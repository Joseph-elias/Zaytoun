import os

from fastapi import Header, HTTPException, status


def require_internal_api_key(x_internal_api_key: str | None = Header(default=None)) -> None:
    required_key = str(os.getenv("INTERNAL_API_KEY", "")).strip()
    if not required_key:
        return

    if x_internal_api_key != required_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal API key")
