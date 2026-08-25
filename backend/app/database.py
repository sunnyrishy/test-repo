from collections.abc import Iterator
from functools import lru_cache

import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine() -> Engine:
    """Created on first use so importing models never requires a database.

    Serverless invocations are short-lived and each one would otherwise leave a
    pooled connection behind, so on Vercel the pool is disabled and the
    connection string should point at a pooler (Neon/pgbouncer).
    """
    if os.getenv("VERCEL"):
        return create_engine(get_settings().database_url, poolclass=NullPool, future=True)
    return create_engine(get_settings().database_url, pool_pre_ping=True, future=True)


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def SessionLocal() -> Session:  # noqa: N802 - reads as a factory at call sites
    return _session_factory()()


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
