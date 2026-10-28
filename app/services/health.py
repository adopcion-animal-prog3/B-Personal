from app.models.health import HealthResponse
from app.repositories.database import DatabaseRepository


class HealthService:
    def __init__(self, database_repository: DatabaseRepository) -> None:
        self._database_repository = database_repository

    def check_api(self) -> HealthResponse:
        return HealthResponse(status="ok")

    def check_database(self) -> HealthResponse:
        status = "ok" if self._database_repository.check_connection() else "unavailable"
        return HealthResponse(status=status)
