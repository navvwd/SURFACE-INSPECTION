from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


engine = None
SessionLocal = sessionmaker(autoflush=False, expire_on_commit=False)


def init_engine(db_url: str):
    global engine
    if db_url.startswith("sqlite:///"):
        Path(db_url.replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(db_url, connect_args={"check_same_thread": False} if db_url.startswith("sqlite") else {})

    if db_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _pragmas(conn, _):
            cur = conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA journal_mode=WAL")
            cur.close()

    SessionLocal.configure(bind=engine)
    from backend.database import models  # noqa: F401  (register tables)
    Base.metadata.create_all(engine)
    return engine


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
