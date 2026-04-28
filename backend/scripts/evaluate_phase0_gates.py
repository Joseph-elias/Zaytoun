import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path


def load_summary(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def metric_value(summary: dict, metric: str, field: str, default: float = 0.0) -> float:
    try:
        return float(summary["metrics"][metric]["values"][field])
    except Exception:
        return default


def extract_metric(metrics_text: str, metric_name: str) -> float:
    pattern = re.compile(rf"^{re.escape(metric_name)}(?:\{{[^}}]*\}})?\s+([0-9eE+.\-]+)$", re.MULTILINE)
    values = [float(match.group(1)) for match in pattern.finditer(metrics_text)]
    return max(values) if values else 0.0


def fetch_metrics(base_url: str, bearer_token: str | None) -> str:
    req = urllib.request.Request(f"{base_url.rstrip('/')}/metrics")
    if bearer_token:
        req.add_header("Authorization", f"Bearer {bearer_token}")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fail(msg: str) -> None:
    print(f"[gate] FAIL: {msg}")
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--health", required=True)
    parser.add_argument("--workers", required=True)
    parser.add_argument("--auth", required=True)
    parser.add_argument("--booking", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--metrics-bearer-token", default="")
    args = parser.parse_args()

    health = load_summary(Path(args.health))
    workers = load_summary(Path(args.workers))
    auth = load_summary(Path(args.auth))
    booking = load_summary(Path(args.booking))

    # Phase 0 latency and failure gates.
    if metric_value(health, "http_req_duration", "p(95)") > 150:
        fail("health p95 > 150ms")
    if metric_value(workers, "http_req_duration", "p(95)") > 1000:
        fail("workers p95 > 1000ms")
    if metric_value(auth, "http_req_duration", "p(95)") > 700:
        fail("auth p95 > 700ms")
    if metric_value(booking, "http_req_duration", "p(95)") > 1000:
        fail("booking p95 > 1000ms")

    for name, summary in [("health", health), ("workers", workers), ("auth", auth), ("booking", booking)]:
        if metric_value(summary, "http_req_failed", "rate") > 0.01:
            fail(f"{name} error rate > 1%")

    metrics_text = fetch_metrics(args.base_url, args.metrics_bearer_token or None)

    backend_errors = extract_metric(metrics_text, "worker_radar_rate_limit_backend_error_total")
    if backend_errors > 0:
        fail("rate limiter backend errors detected")

    checked_out = extract_metric(metrics_text, "worker_radar_db_pool_checked_out_connections")
    pool_size = extract_metric(metrics_text, "worker_radar_db_pool_size")
    overflow = extract_metric(metrics_text, "worker_radar_db_pool_overflow_connections")

    if pool_size > 0 and checked_out >= pool_size + overflow:
        fail("DB pool reached full saturation (checked_out >= pool_size + overflow)")

    print("[gate] PASS: latency/error/limiter/db-pool gates passed")


if __name__ == "__main__":
    main()
