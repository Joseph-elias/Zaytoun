from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.observability import observe_db_pool_state


database_url = settings.resolved_database_url
connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}

engine_kwargs = {"connect_args": connect_args}
if not database_url.startswith("sqlite"):
    engine_kwargs.update(
        {
            "pool_size": int(settings.db_pool_size),
            "max_overflow": int(settings.db_max_overflow),
            "pool_timeout": int(settings.db_pool_timeout_seconds),
            "pool_recycle": int(settings.db_pool_recycle_seconds),
            "pool_pre_ping": True,
        }
    )

engine = create_engine(database_url, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _observe_pool() -> None:
    pool = engine.pool
    size = pool.size() if hasattr(pool, "size") else 0
    checked_out = pool.checkedout() if hasattr(pool, "checkedout") else 0
    overflow = pool.overflow() if hasattr(pool, "overflow") else 0
    observe_db_pool_state(pool_size=size, checked_out=checked_out, overflow=overflow)


if not database_url.startswith("sqlite"):
    @event.listens_for(engine, "checkout")
    def _on_checkout(*_args):  # pragma: no cover - event callback
        _observe_pool()

    @event.listens_for(engine, "checkin")
    def _on_checkin(*_args):  # pragma: no cover - event callback
        _observe_pool()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
