from typing import Any

from fastapi import APIRouter, Depends, Request, status

from app.models.errors import COMMON_ERROR_RESPONSES
from app.models.historial import (
    HistorialCreate,
    HistorialDeleteSuccessResponse,
    HistorialId,
    HistorialSuccessResponse,
    HistorialUpdate,
    HistorialesSuccessResponse,
)
from app.models.mascota import MascotaId
from app.routes.auth import get_current_user, require_role
from app.services.historial import HistorialService
from app.services.policies import UserRole

router = APIRouter(tags=["historial"], responses=COMMON_ERROR_RESPONSES)


def get_historial_service(request: Request) -> HistorialService:
    return request.app.state.historial_service


@router.get(
    "/api/mascotas/{mascota_id}/historial",
    response_model=HistorialesSuccessResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def list_historial(
    request: Request,
    mascota_id: MascotaId,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    records = get_historial_service(request).list_for_mascota(mascota_id, user)
    return {
        "success": True,
        "status": "success",
        "data": records,
        "count": len(records),
    }


@router.post(
    "/api/mascotas/{mascota_id}/historial",
    response_model=HistorialSuccessResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def create_historial(
    values: HistorialCreate,
    request: Request,
    mascota_id: MascotaId,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    created = get_historial_service(request).create(mascota_id, values, user)
    return {"success": True, "status": "success", "data": created}


@router.put(
    "/api/historial/{historial_id}",
    response_model=HistorialSuccessResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def update_historial(
    values: HistorialUpdate,
    request: Request,
    historial_id: HistorialId,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    updated = get_historial_service(request).update(historial_id, values, user)
    return {"success": True, "status": "success", "data": updated}


@router.delete(
    "/api/historial/{historial_id}",
    response_model=HistorialDeleteSuccessResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def delete_historial(
    request: Request,
    historial_id: HistorialId,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    deleted = get_historial_service(request).delete(historial_id, user)
    return {
        "success": True,
        "status": "success",
        "data": {
            "message": "Historial clinico deleted successfully",
            "data": deleted,
        },
    }
