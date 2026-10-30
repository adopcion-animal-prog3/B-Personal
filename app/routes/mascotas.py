from typing import Any

from fastapi import APIRouter, Depends, Request, Response, status

from app.routes.auth import require_role
from app.models.mascota import (
    MascotaCreate,
    MascotaId,
    MascotaResponse,
    MascotaUpdate,
    SuccessResponse,
)
from app.services.mascotas import MascotaService
from app.services.policies import UserRole

router = APIRouter(prefix="/api/mascotas", tags=["mascotas"])


def get_mascota_service(request: Request) -> MascotaService:
    return request.app.state.mascota_service


@router.get("", response_model=SuccessResponse[list[MascotaResponse]])
def list_mascotas(request: Request) -> dict[str, Any]:
    mascotas = get_mascota_service(request).list_mascotas()
    return {
        "success": True,
        "status": "success",
        "data": mascotas,
        "count": len(mascotas),
    }


@router.get("/{mascota_id}", response_model=SuccessResponse[MascotaResponse])
def get_mascota(
    request: Request, mascota_id: MascotaId
) -> dict[str, Any]:
    mascota = get_mascota_service(request).get_mascota(mascota_id)
    return {"success": True, "status": "success", "data": mascota}


@router.post(
    "",
    response_model=SuccessResponse[MascotaResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def create_mascota(
    mascota: MascotaCreate, request: Request
) -> dict[str, Any]:
    created = get_mascota_service(request).create_mascota(mascota)
    return {"success": True, "status": "success", "data": created}


@router.put(
    "/{mascota_id}",
    response_model=SuccessResponse[MascotaResponse],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def update_mascota(
    mascota: MascotaUpdate,
    request: Request,
    mascota_id: MascotaId,
) -> dict[str, Any]:
    updated = get_mascota_service(request).update_mascota(mascota_id, mascota)
    return {"success": True, "status": "success", "data": updated}


@router.delete(
    "/{mascota_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def delete_mascota(
    request: Request, mascota_id: MascotaId
) -> Response:
    get_mascota_service(request).delete_mascota(mascota_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
