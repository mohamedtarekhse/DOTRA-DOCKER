from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from pgvector.asyncpg import register_vector

from .config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=20,
    pool_pre_ping=True,
)


@event.listens_for(engine.sync_engine, "connect")
def _register_pgvector_codec(dbapi_connection, connection_record):
    """Enable pgvector <-> Python list serialization on asyncpg."""
    register_vector(dbapi_connection)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with SessionLocal() as session:
        yield session
