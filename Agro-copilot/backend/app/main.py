import os
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from backend.app.api.routes_diagnosis import router as diagnosis_router
from backend.app.core.security import require_internal_api_key

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

if load_dotenv is not None:
    project_root = Path(__file__).resolve().parents[3]
    load_dotenv(project_root / ".env")
    load_dotenv(project_root / "backend" / ".env")


app = FastAPI(
    title="Olive Agriculture Copilot API",
    version="0.1.0",
    description="Worker Radar backend for olive diagnosis and agronomy guidance.",
)

cors_origins_raw = os.getenv("CORS_ORIGINS", "").strip()
if cors_origins_raw:
    cors_origins = [origin.strip() for origin in cors_origins_raw.split(",") if origin.strip()]
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )

app.include_router(
    diagnosis_router,
    prefix="/api/v1",
    tags=["diagnosis"],
    dependencies=[Depends(require_internal_api_key)],
)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/ui", StaticFiles(directory=FRONTEND_DIR, html=True), name="ui")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


@app.get("/", include_in_schema=False)
def root_redirect() -> RedirectResponse:
    if FRONTEND_DIR.exists():
        return RedirectResponse(url="/ui")
    return RedirectResponse(url="/docs")
