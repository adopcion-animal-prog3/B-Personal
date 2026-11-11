from typing import Any

from fastapi import APIRouter, Depends, Request, status

from app.models.errors import COMMON_ERROR_RESPONSES
from app.models.solicitud import (
    SolicitudCreate,
    SolicitudId,
    SolicitudSuccessResponse,
    SolicitudUpdate,
    SolicitudesSuccessResponse,
)
from app.routes.auth import get_current_user, require_role
from app.services.policies import UserRole
from app.services.solicitudes import SolicitudService

router = APIRouter(
    prefix="/api/solicitudes",
    tags=["solicitudes"],
    responses=COMMON_ERROR_RESPONSES,
)


def get_solicitud_service(request: Request) -> SolicitudService:
    return request.app.state.solicitud_service


@router.get(
    "",
    response_model=SolicitudesSuccessResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.ADOPTANTE))],
)
def list_solicitudes(
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    solicitudes = get_solicitud_service(request).list_solicitudes(user)
    return {
        "success": True,
        "status": "success",
        "data": solicitudes,
        "count": len(solicitudes),
    }


@router.get(
    "/{solicitud_id}",
    response_model=SolicitudSuccessResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.ADOPTANTE))],
)
def get_solicitud(
    request: Request,
    solicitud_id: SolicitudId,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    solicitud = get_solicitud_service(request).get_solicitud(solicitud_id, user)
    return {"success": True, "status": "success", "data": solicitud}


@router.post(
    "",
    response_model=SolicitudSuccessResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_solicitud(
    values: SolicitudCreate,
    request: Request,
    user: dict[str, Any] = Depends(
        require_role(UserRole.ADMIN, UserRole.ADOPTANTE)
    ),
) -> dict[str, Any]:
    created = get_solicitud_service(request).create_solicitud(values, user)
    return {"success": True, "status": "success", "data": created}


@router.put(
    "/{solicitud_id}",
    response_model=SolicitudSuccessResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def update_solicitud(
    values: SolicitudUpdate,
    request: Request,
    solicitud_id: SolicitudId,
) -> dict[str, Any]:
    updated = get_solicitud_service(request).update_solicitud(
        solicitud_id, values
    )
    return {"success": True, "status": "success", "data": updated}
