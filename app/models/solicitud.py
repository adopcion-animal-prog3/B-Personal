from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.models.mascota import SuccessResponse
from app.services.policies import RequestStatus

SolicitudId = Annotated[int, Field(gt=0, le=9_223_372_036_854_775_807)]
SolicitudMascotaId = Annotated[
    int, Field(strict=True, gt=0, le=9_223_372_036_854_775_807)
]
SolicitudMensaje = Annotated[str, Field(strict=True)]


class SolicitudCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    mascota_id: SolicitudMascotaId
    mensaje: SolicitudMensaje | None = None


class SolicitudUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estado: RequestStatus


class SolicitudResponse(BaseModel):
    id: int
    usuario_id: int
    mascota_id: int
    estado: RequestStatus
    mensaje: str | None
    created_at: datetime
    updated_at: datetime | None


class SolicitudSuccessResponse(SuccessResponse[SolicitudResponse]):
    pass


class SolicitudesSuccessResponse(SuccessResponse[list[SolicitudResponse]]):
    pass
