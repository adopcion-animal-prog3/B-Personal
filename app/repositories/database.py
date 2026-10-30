import logging

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import Settings

logger = logging.getLogger(__name__)


def create_database_engine(settings: Settings) -> Engine | None:
    if settings.database_url is None:
        return None

    return create_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
    )


class DatabaseRepository:
    def __init__(self, engine: Engine | None) -> None:
        self._engine = engine

    def check_connection(self) -> bool:
        if self._engine is None:
            logger.warning("Database connectivity check unavailable: DATABASE_URL is not configured")
            return False

        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError as error:
            logger.warning("Database connectivity check failed (%s)", type(error).__name__)
            return False

        return True
