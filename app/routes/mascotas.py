from typing import Any

from fastapi import APIRouter, Request, Response, status

from app.models.mascota import (
    MascotaCreate,
    MascotaId,
    MascotaResponse,
    MascotaUpdate,
    SuccessResponse,
)
from app.services.mascotas import MascotaService

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
)
def create_mascota(
    mascota: MascotaCreate, request: Request
) -> dict[str, Any]:
    created = get_mascota_service(request).create_mascota(mascota)
    return {"success": True, "status": "success", "data": created}


@router.put("/{mascota_id}", response_model=SuccessResponse[MascotaResponse])
def update_mascota(
    mascota: MascotaUpdate,
    request: Request,
    mascota_id: MascotaId,
) -> dict[str, Any]:
    updated = get_mascota_service(request).update_mascota(mascota_id, mascota)
    return {"success": True, "status": "success", "data": updated}


@router.delete("/{mascota_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mascota(
    request: Request, mascota_id: MascotaId
) -> Response:
    get_mascota_service(request).delete_mascota(mascota_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
