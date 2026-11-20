from typing import Any

from fastapi import APIRouter, Depends, Request, status

from app.models.errors import COMMON_ERROR_RESPONSES
from app.models.mensaje import (
    ConversacionSuccessResponse,
    ConversacionesSuccessResponse,
    LeidosSuccessResponse,
    MensajeCreate,
    MensajeSuccessResponse,
    UsuarioId,
)
from app.routes.auth import require_role
from app.services.mensajes import MensajeService
from app.services.policies import UserRole

router = APIRouter(
    prefix="/api/mensajes",
    tags=["mensajes"],
    responses=COMMON_ERROR_RESPONSES,
)
_authenticated = require_role(UserRole.ADMIN, UserRole.ADOPTANTE)


def get_mensaje_service(request: Request) -> MensajeService:
    return request.app.state.mensaje_service


def _success(data: Any, **extra: Any) -> dict[str, Any]:
    return {"success": True, "status": "success", "data": data, **extra}


@router.get("/conversaciones", response_model=ConversacionesSuccessResponse)
def list_conversaciones(
    request: Request, user: dict[str, Any] = Depends(_authenticated)
) -> dict[str, Any]:
    conversaciones = get_mensaje_service(request).list_conversaciones(user)
    return _success(conversaciones, count=len(conversaciones))


@router.get("/conversaciones/{usuario_id}", response_model=ConversacionSuccessResponse)
def get_conversacion(
    request: Request,
    usuario_id: UsuarioId,
    user: dict[str, Any] = Depends(_authenticated),
) -> dict[str, Any]:
    return _success(get_mensaje_service(request).get_conversacion(user, usuario_id))


@router.put("/conversaciones/{usuario_id}/leidos", response_model=LeidosSuccessResponse)
def mark_read(
    request: Request,
    usuario_id: UsuarioId,
    user: dict[str, Any] = Depends(_authenticated),
) -> dict[str, Any]:
    actualizados = get_mensaje_service(request).mark_read(user, usuario_id)
    return _success({"actualizados": actualizados})


@router.post(
    "",
    response_model=MensajeSuccessResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_mensaje(
    values: MensajeCreate,
    request: Request,
    user: dict[str, Any] = Depends(_authenticated),
) -> dict[str, Any]:
    return _success(get_mensaje_service(request).create(values, user))
