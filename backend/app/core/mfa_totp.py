from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote


def generate_base32_secret(num_bytes: int = 20) -> str:
    raw = secrets.token_bytes(max(10, int(num_bytes)))
    return base64.b32encode(raw).decode("ascii").rstrip("=")


def _normalize_secret(secret: str) -> bytes:
    cleaned = "".join(ch for ch in str(secret or "").upper() if ch.isalnum())
    if not cleaned:
        raise ValueError("MFA secret is empty")
    pad_len = (-len(cleaned)) % 8
    return base64.b32decode(cleaned + ("=" * pad_len), casefold=True)


def _hotp(secret: str, counter: int, digits: int = 6) -> str:
    key = _normalize_secret(secret)
    msg = struct.pack(">Q", int(counter))
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    code = code_int % (10 ** int(digits))
    return str(code).zfill(int(digits))


def totp_now(
    secret: str,
    *,
    now_ts: int | None = None,
    period_seconds: int = 30,
    digits: int = 6,
) -> str:
    ts = int(time.time() if now_ts is None else now_ts)
    period = max(15, int(period_seconds))
    counter = ts // period
    return _hotp(secret, counter=counter, digits=max(6, int(digits)))


def verify_totp(
    secret: str,
    code: str,
    *,
    now_ts: int | None = None,
    period_seconds: int = 30,
    digits: int = 6,
    valid_window: int = 1,
) -> bool:
    entered = "".join(ch for ch in str(code or "") if ch.isdigit())
    d = max(6, int(digits))
    if len(entered) != d:
        return False
    ts = int(time.time() if now_ts is None else now_ts)
    period = max(15, int(period_seconds))
    base_counter = ts // period
    window = max(0, int(valid_window))
    for delta in range(-window, window + 1):
        expected = _hotp(secret, counter=base_counter + delta, digits=d)
        if hmac.compare_digest(entered, expected):
            return True
    return False


def provisioning_uri(*, secret: str, account_name: str, issuer: str, period_seconds: int = 30, digits: int = 6) -> str:
    issuer_clean = str(issuer or "Zaytoun").strip() or "Zaytoun"
    account_clean = str(account_name or "user").strip() or "user"
    label = quote(f"{issuer_clean}:{account_clean}", safe="")
    issuer_q = quote(issuer_clean, safe="")
    secret_q = quote(secret, safe="")
    return (
        f"otpauth://totp/{label}"
        f"?secret={secret_q}&issuer={issuer_q}&algorithm=SHA1"
        f"&digits={max(6, int(digits))}&period={max(15, int(period_seconds))}"
    )
