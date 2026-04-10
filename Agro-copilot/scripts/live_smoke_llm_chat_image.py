import argparse
import base64
import json
import os
import sys
from pathlib import Path
from urllib import error, request

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None


def _load_env() -> None:
    root = Path(__file__).resolve().parents[1]
    if load_dotenv is not None:
        load_dotenv(root / ".env")
        load_dotenv(root / "backend" / ".env")


def _guess_mime(image_path: Path) -> str:
    ext = image_path.suffix.lower()
    if ext in {".png"}:
        return "image/png"
    if ext in {".webp"}:
        return "image/webp"
    return "image/jpeg"


def _image_to_data_url(image_path: Path) -> str:
    raw = image_path.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    mime = _guess_mime(image_path)
    return f"data:{mime};base64,{b64}"


def _looks_conversational(text: str) -> bool:
    lowered = text.lower()
    if len(text.strip()) < 25:
        return False
    hints = (
        "we can",
        "let's",
        "i recommend",
        "it looks",
        "likely",
        "you can",
        "step by step",
    )
    return any(h in lowered for h in hints)


def _post_json(url: str, payload: dict, headers: dict[str, str], timeout: float = 120.0) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, method="POST", headers=headers)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            parsed = json.loads(body) if body else {}
            return int(resp.status), parsed
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw) if raw else {}
        except Exception:
            parsed = {"raw": raw}
        return int(exc.code), parsed


def main() -> int:
    _load_env()

    parser = argparse.ArgumentParser(description="Live smoke test for Agro-copilot image chat response.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001", help="Agro-copilot base URL.")
    parser.add_argument("--endpoint", default="/api/v1/chat", help="Chat endpoint path.")
    parser.add_argument("--session-id", default="smoke-session-1", help="Conversation session id.")
    parser.add_argument("--language", default="en", choices=["en", "fr", "ar"], help="Requested response language.")
    parser.add_argument("--image-path", required=True, help="Path to a local image file.")
    parser.add_argument(
        "--message",
        default="Please analyze this olive leaf image and guide me safely.",
        help="Smoke-test user message.",
    )
    args = parser.parse_args()

    openai_key = str(os.getenv("OPENAI_API_KEY", "")).strip()
    if not openai_key:
        print("FAIL: OPENAI_API_KEY is missing. Put it in Agro-copilot/.env")
        return 1

    image_path = Path(args.image_path)
    if not image_path.exists() or not image_path.is_file():
        print(f"FAIL: image file not found: {image_path}")
        return 1

    image_data_url = _image_to_data_url(image_path)
    url = f"{args.base_url.rstrip('/')}{args.endpoint}"

    headers = {"Content-Type": "application/json"}
    internal_key = str(os.getenv("INTERNAL_API_KEY", "")).strip()
    if internal_key:
        headers["x-internal-api-key"] = internal_key

    payload = {
        "message": args.message,
        "observed_symptoms": [],
        "language": args.language,
        "session_id": args.session_id,
        "image_urls": [],
        "image_base64": image_data_url,
        "image_path": None,
    }

    status, body = _post_json(url, payload, headers=headers)
    if status != 200:
        print(f"FAIL: HTTP {status}")
        print(json.dumps(body, indent=2, ensure_ascii=False))
        return 1

    probable_issue = str(body.get("probable_issue", ""))
    confidence = str(body.get("confidence_band", ""))
    language = str(body.get("language", ""))
    followups = body.get("recommended_followup_questions", []) or []

    print("PASS: API responded with 200")
    print(f"- language={language}")
    print(f"- confidence_band={confidence}")
    print(f"- probable_issue={probable_issue}")
    print(f"- followup_count={len(followups)}")

    conversational = _looks_conversational(probable_issue) or any(
        _looks_conversational(str(item)) for item in followups
    )
    if conversational:
        print("PASS: response appears conversational/LLM-like")
        return 0

    print("WARN: response is valid but may not sound conversational enough.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
