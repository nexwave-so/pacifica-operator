"""Database session management"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from nexwave.common.config import settings
from typing import AsyncGenerator


class Base(DeclarativeBase):
    """Base class for all database models"""
    pass


# Create async engine
engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

