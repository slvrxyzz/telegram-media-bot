from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from bot.config import get_settings


_session_factory: sessionmaker | None = None


def get_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(settings.database_url, echo=False)


def get_session_factory(engine: AsyncEngine) -> sessionmaker:
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def set_session_factory(factory: sessionmaker) -> None:
    global _session_factory
    _session_factory = factory


def get_session() -> sessionmaker:
    if _session_factory is None:
        raise RuntimeError("Session factory is not initialized")
    return _session_factory

