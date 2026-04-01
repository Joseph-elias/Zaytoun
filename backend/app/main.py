from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_auth import router as auth_router
from app.api.routes_workers import router as workers_router
from app.api.routes_olive_seasons import router as olive_seasons_router
from app.api.routes_olive_piece_metrics import router as olive_piece_metrics_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Worker Radar API",
        description="MVP API for worker registration, search, and availability updates.",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:5500",
            "http://localhost:5500",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(workers_router)
    app.include_router(olive_seasons_router)
    app.include_router(olive_piece_metrics_router)
    return app


app = create_app()




