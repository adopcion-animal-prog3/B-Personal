from datetime import datetime
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

MascotaNombre = Annotated[str, Field(strict=True, min_length=1, max_length=150)]
MascotaEspecie = Annotated[str, Field(strict=True, min_length=1, max_length=100)]
MascotaRaza = Annotated[str, Field(strict=True, max_length=120)]
MascotaEdad = Annotated[int, Field(strict=True, ge=0, le=2_147_483_647)]
MascotaCreador = Annotated[int, Field(strict=True, gt=0, le=9_223_372_036_854_775_807)]
MascotaId = Annotated[int, Field(gt=0, le=9_223_372_036_854_775_807)]


class MascotaInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    nombre: MascotaNombre
    especie: MascotaEspecie
    raza: MascotaRaza | None = None
    edad: MascotaEdad | None = None
    sexo: Literal["M", "F", "OTRO"] | None = None
    descripcion: str | None = None
    adoptada: bool = Field(default=False, strict=True)
    creado_por: MascotaCreador | None = None


class MascotaCreate(MascotaInput):
    pass


class MascotaUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    nombre: MascotaNombre | None = None
    especie: MascotaEspecie | None = None
    raza: MascotaRaza | None = None
    edad: MascotaEdad | None = None
    sexo: Literal["M", "F", "OTRO"] | None = None
    descripcion: str | None = None
    adoptada: bool | None = Field(default=None, strict=True)

    def model_post_init(self, __context: object) -> None:
        for field in ("nombre", "especie"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")


class MascotaResponse(BaseModel):
    id: int
    nombre: str
    especie: str
    raza: str | None
    edad: int | None
    sexo: Literal["M", "F", "OTRO"] | None
    descripcion: str | None
    adoptada: bool
    creado_por: int | None
    created_at: datetime


T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    success: Literal[True] = True
    status: Literal["success"] = "success"
    data: T
    count: int | None = None
