import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.mascota import SuccessResponse

Email = Annotated[str, Field(strict=True, min_length=3, max_length=255)]
Password = Annotated[str, Field(strict=True, min_length=1)]
_EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_MAX_BCRYPT_PASSWORD_BYTES = 72


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: Annotated[str, Field(strict=True, min_length=1, max_length=150)]
    email: Email
    password: Annotated[str, Field(strict=True, min_length=8)]

    @field_validator("nombre")
    @classmethod
    def validate_nombre(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("nombre cannot be blank")
        return normalized

    @field_validator("email")
    @classmethod
    def normalize_and_validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not _EMAIL_PATTERN.fullmatch(normalized):
            raise ValueError("email is invalid")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        _validate_bcrypt_password(value)
        return value


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: Email
    password: Password

    @field_validator("email")
    @classmethod
    def normalize_and_validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not _EMAIL_PATTERN.fullmatch(normalized):
            raise ValueError("email is invalid")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        _validate_bcrypt_password(value)
        return value


def _validate_bcrypt_password(value: str) -> None:
    if "\x00" in value or len(value.encode("utf-8")) > _MAX_BCRYPT_PASSWORD_BYTES:
        raise ValueError("password exceeds the supported length")


class PublicUser(BaseModel):
    id: int
    nombre: str
    email: str
    rol: Literal["ADMIN", "ADOPTANTE"]


class AuthenticatedUserResponse(BaseModel):
    user: PublicUser


class AuthTokenResponse(BaseModel):
    token: str
    user: PublicUser


class AuthSuccessResponse(SuccessResponse[AuthTokenResponse]):
    pass


class UserSuccessResponse(SuccessResponse[PublicUser]):
    pass


class AuthenticatedUserSuccessResponse(SuccessResponse[AuthenticatedUserResponse]):
    pass
