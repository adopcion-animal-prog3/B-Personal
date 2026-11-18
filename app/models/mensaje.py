from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.mascota import SuccessResponse

MAX_CONTENIDO = 2000

UsuarioId = Annotated[int, Field(gt=0, le=9_223_372_036_854_775_807)]
StrictId = Annotated[int, Field(strict=True, gt=0, le=9_223_372_036_854_775_807)]
Contenido = Annotated[str, Field(strict=True, min_length=1, max_length=MAX_CONTENIDO)]


class MensajeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    destinatario_id: StrictId
    mascota_id: StrictId | None = None
    contenido: Contenido


class MensajeResponse(BaseModel):
    id: int
    remitente_id: int
    destinatario_id: int
    mascota_id: int | None
    contenido: str
    leido: bool
    created_at: datetime


class UsuarioPublico(BaseModel):
    id: int
    nombre: str
    rol: Literal["ADMIN", "ADOPTANTE"]


class ConversacionResumen(BaseModel):
    usuario: UsuarioPublico
    ultimo_mensaje: MensajeResponse
    no_leidos: int


class ConversacionDetalle(BaseModel):
    usuario: UsuarioPublico
    mensajes: list[MensajeResponse]


class LeidosResponse(BaseModel):
    actualizados: int


class MensajeSuccessResponse(SuccessResponse[MensajeResponse]):
    pass


class ConversacionesSuccessResponse(SuccessResponse[list[ConversacionResumen]]):
    pass


class ConversacionSuccessResponse(SuccessResponse[ConversacionDetalle]):
    pass


class LeidosSuccessResponse(SuccessResponse[LeidosResponse]):
    pass
