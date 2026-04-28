from contextlib import asynccontextmanager
import logging
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import inspect, text

from app.api.routes_agro_copilot import router as agro_copilot_router
from app.api.routes_auth import router as auth_router
from app.api.routes_market import router as market_router
from app.api.routes_olive_inventory_items import router as olive_inventory_items_router
from app.api.routes_olive_land_pieces import router as olive_land_pieces_router
from app.api.routes_olive_labor_days import router as olive_labor_days_router
from app.api.routes_olive_piece_metrics import router as olive_piece_metrics_router
from app.api.routes_olive_sales import router as olive_sales_router
from app.api.routes_olive_seasons import router as olive_seasons_router
from app.api.routes_olive_usages import router as olive_usages_router
from app.api.routes_uploads import router as uploads_router
from app.api.routes_workers import router as workers_router
from app.core.config import settings
from app.core.http_security import apply_security_headers
from app.core.observability import (
    log_security_event,
    metrics_backend_status,
    metrics_content_type,
    metrics_endpoint_enabled,
    metrics_payload,
    now_monotonic,
    observe_http_request,
)
from app.core.rate_limit import build_rate_limit_rules, enforce_rate_limit, rate_limiter_healthcheck
from app.core.startup_validation import parse_cors_origins, validate_startup_settings_or_raise
from app.db.session import engine

logger = logging.getLogger(__name__)


def _ensure_market_order_review_columns_for_sqlite() -> None:
    # Safety net for local SQLite dev environments where migrations may have
    # been applied against a different relative DB file.
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "market_orders" not in table_names:
        return

    columns = {col["name"] for col in inspector.get_columns("market_orders")}
    add_columns_sql: list[str] = []

    if "market_rating" not in columns:
        add_columns_sql.append("ALTER TABLE market_orders ADD COLUMN market_rating INTEGER")
    if "market_review" not in columns:
        add_columns_sql.append("ALTER TABLE market_orders ADD COLUMN market_review VARCHAR(800)")
    if "market_reviewed_at" not in columns:
        add_columns_sql.append("ALTER TABLE market_orders ADD COLUMN market_reviewed_at DATETIME")

    if not add_columns_sql:
        return

    with engine.begin() as conn:
        for sql in add_columns_sql:
            conn.execute(text(sql))


def _ensure_worker_slot_schema_for_sqlite() -> None:
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "bookings" in table_names:
        columns = {col["name"] for col in inspector.get_columns("bookings")}
        if "work_slot" not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE bookings ADD COLUMN work_slot VARCHAR(20)"))
                conn.execute(
                    text(
                        "UPDATE bookings SET work_slot = 'full_day' "
                        "WHERE work_slot IS NULL OR work_slot = ''"
                    )
                )

    if "worker_availability_slots" not in table_names:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE worker_availability_slots (
                        id CHAR(32) NOT NULL PRIMARY KEY,
                        worker_id CHAR(32) NOT NULL,
                        work_date DATE NOT NULL,
                        slot_type VARCHAR(20) NOT NULL,
                        created_at DATETIME NOT NULL,
                        FOREIGN KEY(worker_id) REFERENCES workers (id) ON DELETE CASCADE
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX ix_worker_availability_slots_worker_date "
                    "ON worker_availability_slots (worker_id, work_date)"
                )
            )
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX ux_worker_availability_slots_worker_date_slot "
                    "ON worker_availability_slots (worker_id, work_date, slot_type)"
                )
            )


def _trusted_hosts() -> list[str]:
    raw = str(settings.security_trusted_hosts or "").strip()
    if not raw:
        return []
    return [host.strip() for host in raw.split(",") if host.strip()]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    validate_startup_settings_or_raise()
    metrics_ok, metrics_reason = metrics_backend_status()
    if settings.metrics_enabled and settings.metrics_require_prometheus_client and not metrics_ok:
        raise RuntimeError(f"Metrics enabled but Prometheus backend is unavailable: {metrics_reason}")
    _ensure_market_order_review_columns_for_sqlite()
    _ensure_worker_slot_schema_for_sqlite()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Worker Radar API",
        description="MVP API for worker registration, search, and availability updates.",
        version="0.1.0",
        lifespan=lifespan,
    )

    trusted_hosts = _trusted_hosts()
    if trusted_hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=parse_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def _rate_limit_middleware(request, call_next):
        request_id_header = str(settings.request_id_header_name or "X-Request-ID")
        request_id = str(request.headers.get(request_id_header, "")).strip() or uuid4().hex
        request.state.request_id = request_id
        start = now_monotonic()

        blocked = await enforce_rate_limit(request, build_rate_limit_rules())
        if blocked is not None:
            blocked.headers[request_id_header] = request_id
            observe_http_request(
                method=request.method,
                path=request.url.path,
                status_code=blocked.status_code,
                duration_seconds=now_monotonic() - start,
            )
            return apply_security_headers(blocked)

        response = await call_next(request)
        observe_http_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_seconds=now_monotonic() - start,
        )
        response.headers[request_id_header] = request_id
        return apply_security_headers(response)

    @app.get(str(settings.metrics_path or "/metrics"), include_in_schema=False)
    async def metrics_endpoint(request: Request) -> Response:
        if not metrics_endpoint_enabled():
            return Response(status_code=status.HTTP_404_NOT_FOUND)

        token = str(settings.metrics_bearer_token or "").strip()
        if token:
            auth_header = str(request.headers.get("authorization", "")).strip()
            expected = f"Bearer {token}"
            if auth_header != expected:
                return Response(status_code=status.HTTP_401_UNAUTHORIZED)

        return Response(content=metrics_payload(), media_type=metrics_content_type())

    @app.post("/csp-report", include_in_schema=False)
    async def csp_report_endpoint(request: Request) -> Response:
        if not settings.security_csp_report_endpoint_enabled:
            return Response(status_code=status.HTTP_404_NOT_FOUND)
        payload = await request.body()
        if payload:
            log_security_event(logger, "csp_violation_report", payload=payload.decode("utf-8", errors="replace")[:4000])
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    app.include_router(auth_router)
    app.include_router(workers_router)
    app.include_router(olive_seasons_router)
    app.include_router(olive_piece_metrics_router)
    app.include_router(olive_labor_days_router)
    app.include_router(olive_sales_router)
    app.include_router(olive_usages_router)
    app.include_router(olive_inventory_items_router)
    app.include_router(olive_land_pieces_router)
    app.include_router(market_router)
    app.include_router(agro_copilot_router)
    app.include_router(uploads_router)
    return app


app = create_app()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", response_model=None)
async def ready() -> Response:
    checks: dict[str, str | bool | dict[str, str]] = {"database": "ok"}
    healthy = True

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        healthy = False
        checks["database"] = f"error:{exc.__class__.__name__}"

    limiter_ok, limiter_info = await rate_limiter_healthcheck()
    checks["rate_limiter"] = limiter_info
    if not limiter_ok:
        healthy = False

    metrics_ok, metrics_reason = metrics_backend_status()
    checks["metrics_backend"] = {"status": metrics_reason}
    if settings.metrics_enabled and settings.metrics_require_prometheus_client and not metrics_ok:
        healthy = False

    if healthy:
        return JSONResponse(content={"status": "ready", "ok": True, "checks": checks})
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "not_ready", "ok": False, "checks": checks},
    )
