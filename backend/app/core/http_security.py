from __future__ import annotations

from starlette.responses import Response

from app.core.config import settings


def apply_security_headers(response: Response) -> Response:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
    response.headers.setdefault("X-DNS-Prefetch-Control", str(settings.security_x_dns_prefetch_control or "off"))
    response.headers.setdefault("Cross-Origin-Opener-Policy", str(settings.security_cross_origin_opener_policy or "same-origin"))
    response.headers.setdefault("Cross-Origin-Resource-Policy", str(settings.security_cross_origin_resource_policy or "same-origin"))
    response.headers.setdefault("Cross-Origin-Embedder-Policy", str(settings.security_cross_origin_embedder_policy or "unsafe-none"))

    csp_value = str(settings.security_content_security_policy or "").strip()
    report_uri = str(settings.security_content_security_policy_report_uri or "").strip()
    if not report_uri and settings.security_csp_report_endpoint_enabled:
        report_uri = "/csp-report"
    if csp_value and report_uri and "report-uri" not in csp_value:
        csp_value = f"{csp_value}; report-uri {report_uri}"
    if csp_value:
        if settings.security_content_security_policy_report_only:
            response.headers.setdefault("Content-Security-Policy-Report-Only", csp_value)
        else:
            response.headers.setdefault("Content-Security-Policy", csp_value)

    if settings.security_hsts_enabled:
        hsts = f"max-age={max(300, int(settings.security_hsts_max_age_seconds))}"
        if settings.security_hsts_include_subdomains:
            hsts += "; includeSubDomains"
        if settings.security_hsts_preload:
            hsts += "; preload"
        response.headers.setdefault("Strict-Transport-Security", hsts)

    return response
