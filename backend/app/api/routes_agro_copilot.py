import asyncio
import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import require_roles
from app.core.config import settings
from app.models.user import User
from app.schemas.agro_copilot import (
    AgroCopilotChatRequest,
    AgroCopilotDiagnosisRequest,
    AgroCopilotDiagnosisResponse,
    AgroCopilotKnowledgeSource,
)


router = APIRouter(prefix="/agro-copilot", tags=["Agro Copilot"])
logger = logging.getLogger(__name__)


def _agro_base_url() -> str:
    value = str(settings.agro_copilot_api_base_url or "").strip().rstrip("/")
    if not value:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agro Copilot service is not configured. Set AGRO_COPILOT_API_BASE_URL.",
        )
    return value


async def _proxy_json(path: str, method: str = "GET", payload: dict[str, Any] | None = None) -> Any:
    base_url = _agro_base_url()
    url = f"{base_url}/{path.lstrip('/')}"
    timeout = max(5, int(settings.agro_copilot_timeout_seconds))
    max_retries = max(0, int(settings.agro_copilot_max_retries))
    backoff_ms = max(0, int(settings.agro_copilot_retry_backoff_ms))

    headers: dict[str, str] = {}
    internal_key = str(settings.agro_copilot_api_key or "").strip()
    if internal_key:
        headers["X-Internal-Api-Key"] = internal_key

    attempts = 1 + (max_retries if method.upper() == "GET" else 0)
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(method=method, url=url, json=payload, headers=headers)
        except httpx.RequestError as exc:
            last_error = exc
            logger.warning(
                "Agro Copilot upstream request error on %s %s (attempt %s/%s): %s",
                method,
                url,
                attempt,
                attempts,
                exc,
            )
            if attempt < attempts:
                await asyncio.sleep((backoff_ms * attempt) / 1000)
                continue
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Agro Copilot service is unreachable: {exc}",
            ) from exc

        if response.status_code in {502, 503, 504} and attempt < attempts:
            logger.warning(
                "Agro Copilot transient upstream status %s on %s %s (attempt %s/%s)",
                response.status_code,
                method,
                url,
                attempt,
                attempts,
            )
            await asyncio.sleep((backoff_ms * attempt) / 1000)
            continue
        break
    else:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Agro Copilot request failed after retries: {last_error}",
        )

    try:
        data = response.json()
    except ValueError:
        data = {"detail": response.text or "Invalid response from Agro Copilot service"}

    if response.status_code >= 400:
        detail = data.get("detail", data) if isinstance(data, dict) else data
        raise HTTPException(status_code=response.status_code, detail=detail)

    return data


@router.get("/health", response_model=dict[str, str])
async def agro_copilot_health(current_user: User = Depends(require_roles("farmer"))) -> Any:
    _ = current_user
    return await _proxy_json("/health")


@router.get("/knowledge/sources", response_model=list[AgroCopilotKnowledgeSource])
async def agro_copilot_sources(current_user: User = Depends(require_roles("farmer"))) -> list[AgroCopilotKnowledgeSource]:
    _ = current_user
    return await _proxy_json("/api/v1/knowledge/sources")


@router.post("/chat", response_model=AgroCopilotDiagnosisResponse)
async def agro_copilot_chat(
    payload: AgroCopilotChatRequest,
    current_user: User = Depends(require_roles("farmer")),
) -> AgroCopilotDiagnosisResponse:
    _ = current_user
    return await _proxy_json("/api/v1/chat", method="POST", payload=payload.model_dump())


@router.post("/diagnose", response_model=AgroCopilotDiagnosisResponse)
async def agro_copilot_diagnose(
    payload: AgroCopilotDiagnosisRequest,
    current_user: User = Depends(require_roles("farmer")),
) -> AgroCopilotDiagnosisResponse:
    _ = current_user
    return await _proxy_json("/api/v1/diagnose", method="POST", payload=payload.model_dump())
