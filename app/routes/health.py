from fastapi import APIRouter, HTTPException, Request, status

from app.models.health import HealthResponse
from app.services.health import HealthService

router = APIRouter(prefix="/health", tags=["health"])


def get_health_service(request: Request) -> HealthService:
    return request.app.state.health_service


@router.get("", response_model=HealthResponse)
def check_api_health(request: Request) -> HealthResponse:
    return get_health_service(request).check_api()


@router.get(
    "/db",
    response_model=HealthResponse,
    responses={503: {"description": "Database unavailable"}},
)
def check_database_health(request: Request) -> HealthResponse:
    result = get_health_service(request).check_database()
    if result.status != "ok":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )
    return result
