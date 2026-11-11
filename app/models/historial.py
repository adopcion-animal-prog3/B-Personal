from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.mascota import SuccessResponse

HistorialId = Annotated[int, Field(gt=0, le=9_223_372_036_854_775_807)]
HistorialDescripcion = Annotated[str, Field(strict=True, min_length=1)]
HistorialVeterinario = Annotated[str, Field(strict=True, max_length=200)]


class HistorialCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    fecha_registro: datetime | None = None
    descripcion: HistorialDescripcion
    veterinario: HistorialVeterinario | None = None


class HistorialUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    fecha_registro: datetime | None = None
    descripcion: HistorialDescripcion | None = None
    veterinario: HistorialVeterinario | None = None

    @field_validator("descripcion")
    @classmethod
    def descripcion_cannot_be_null(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("descripcion cannot be null")
        return value

    @field_validator("fecha_registro")
    @classmethod
    def fecha_registro_cannot_be_null(cls, value: datetime | None) -> datetime | None:
        if value is None:
            raise ValueError("fecha_registro cannot be null")
        return value

    @model_validator(mode="after")
    def require_changes(self) -> "HistorialUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class HistorialResponse(BaseModel):
    id: int
    mascota_id: int
    fecha_registro: datetime
    descripcion: str
    veterinario: str | None
    created_at: datetime
    updated_at: datetime | None


class HistorialSuccessResponse(SuccessResponse[HistorialResponse]):
    pass


class HistorialesSuccessResponse(SuccessResponse[list[HistorialResponse]]):
    pass


class HistorialDeleteData(BaseModel):
    message: str
    data: HistorialResponse


class HistorialDeleteSuccessResponse(SuccessResponse[HistorialDeleteData]):
    pass
