from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_auth import router as auth_router
from app.api.routes_workers import router as workers_router
from app.db.base import Base
from app.db.session import engine
from app.models.user import User
from app.models.worker import Worker


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

    # MVP setup for immediate shipping. Replace with Alembic migrations once schema stabilizes.
    Base.metadata.create_all(bind=engine)

    app.include_router(auth_router)
    app.include_router(workers_router)
    return app


app = create_app()
