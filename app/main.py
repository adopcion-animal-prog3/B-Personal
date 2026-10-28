import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.config import Settings
from app.repositories.database import DatabaseRepository, create_database_engine
from app.routes.health import router as health_router
from app.services.health import HealthService


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings()
    logging.basicConfig(
        level=app_settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    engine = create_database_engine(app_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        if engine is not None:
            engine.dispose()

    app = FastAPI(
        title="B-Personal API",
        description="Backend API for animal adoption and health management.",
        lifespan=lifespan,
    )
    app.state.health_service = HealthService(DatabaseRepository(engine))
    app.include_router(health_router)
    return app


app = create_app()
