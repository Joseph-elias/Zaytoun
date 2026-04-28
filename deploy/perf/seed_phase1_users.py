import argparse
import json
import sys
import urllib.error
import urllib.request


def post(base: str, path: str, payload: dict, token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        f"{base.rstrip('/')}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        if exc.code == 409:
            return {"conflict": body}
        raise RuntimeError(f"POST {path} failed ({exc.code}): {body}") from exc


def get(base: str, path: str, token: str) -> list[dict]:
    req = urllib.request.Request(
        f"{base.rstrip('/')}{path}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--farmer-phone", required=True)
    parser.add_argument("--farmer-password", required=True)
    parser.add_argument("--worker-phone", required=True)
    parser.add_argument("--worker-password", required=True)
    args = parser.parse_args()

    post(
        args.base_url,
        "/auth/register",
        {
            "full_name": "Phase1 Farmer",
            "phone": args.farmer_phone,
            "password": args.farmer_password,
            "role": "farmer",
            "terms_accepted": True,
            "data_consent_accepted": True,
        },
    )
    post(
        args.base_url,
        "/auth/register",
        {
            "full_name": "Phase1 Worker",
            "phone": args.worker_phone,
            "password": args.worker_password,
            "role": "worker",
            "terms_accepted": True,
            "data_consent_accepted": True,
        },
    )
    login = post(
        args.base_url,
        "/auth/login",
        {
            "phone": args.worker_phone,
            "password": args.worker_password,
            "legal_acknowledged": True,
        },
    )
    worker_token = login.get("access_token")
    if not worker_token:
        raise RuntimeError("Worker login failed: no access_token returned.")

    workers = get(args.base_url, "/workers", worker_token)
    if not workers:
        post(
            args.base_url,
            "/workers",
            {
                "name": "Phase1 Worker",
                "phone": args.worker_phone,
                "village": "Sfax",
                "men_count": 1,
                "women_count": 1,
                "rate_type": "day",
                "men_rate_value": 120,
                "women_rate_value": 120,
                "overtime_open": False,
                "available_dates": ["2026-05-01"],
                "available": True,
            },
            worker_token,
        )
        workers = get(args.base_url, "/workers", worker_token)

    if not workers:
        raise RuntimeError("Worker profile could not be created/fetched.")

    print(workers[0]["id"])


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[seed-phase1] FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
