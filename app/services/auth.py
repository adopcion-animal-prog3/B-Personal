from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from pydantic import SecretStr
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError

from app.config import Settings
from app.models.auth import LoginRequest, RegisterRequest
from app.repositories.users import UserRepository
from app.services.mailer import Mailer
from app.services.verification import VerificationError, VerificationService

_MINIMUM_JWT_SECRET_BYTES = 32


class EmailAlreadyExistsError(Exception):
    pass


class AuthenticationConfigurationError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class WrongPortalError(Exception):
    pass


# Este backend atiende el portal personal: solo las cuentas ADOPTANTE inician sesión aquí.
_PORTAL_ROLE = "ADOPTANTE"


class InvalidAuthTokenError(Exception):
    pass


class ExpiredAuthTokenError(Exception):
    pass


class AuthService:
    def __init__(
        self, engine: Engine | None, settings: Settings, mailer: Mailer | None = None
    ) -> None:
        self._repository = UserRepository(engine)
        self._settings = settings
        self.mailer = mailer or Mailer(settings)
        self._verification = VerificationService(engine, self.mailer, self._get_jwt_secret)

    def register(self, values: RegisterRequest) -> dict[str, Any]:
        if self._repository.get_by_email(values.email) is not None:
            raise EmailAlreadyExistsError("Email already registered")

        password_hash = bcrypt.hashpw(
            values.password.encode("utf-8"), bcrypt.gensalt()
        ).decode("ascii")
        try:
            return self._repository.create(
                values.nombre, values.email, password_hash
            )
        except IntegrityError as error:
            if self._repository.get_by_email(values.email) is not None:
                raise EmailAlreadyExistsError("Email already registered") from error
            raise

    def start_registration(self, values: RegisterRequest) -> dict[str, Any]:
        """Crea la cuenta (sin verificar) y envía el código de verificación por email."""
        user = self.register(values)
        return {**user, "verificacion": self._verification.issue(user, "REGISTRO")}

    def start_login(self, values: LoginRequest) -> dict[str, Any]:
        """Paso 1 del login: valida la contraseña y envía un código por email."""
        self._get_jwt_secret()
        user = self._authenticate_password(values)
        return self._verification.issue(user, "LOGIN")

    def verify_code(self, email: str, code: str) -> tuple[str, dict[str, Any]]:
        """Paso 2 (login o registro): valida el código y entrega el token."""
        user = self._repository.get_by_email(email)
        if user is None or user["rol"] != _PORTAL_ROLE:
            raise VerificationError(400, "Invalid verification code")
        self._verification.consume(user["id"], code)
        return self._issue_token(user), user

    def resend_code(self, email: str) -> None:
        user = self._repository.get_by_email(email)
        if user is not None and user["rol"] == _PORTAL_ROLE:
            self._verification.resend(user)

    def _authenticate_password(self, values: LoginRequest) -> dict[str, Any]:
        user = self._repository.get_by_email(values.email)
        password_matches = False
        if user is not None:
            try:
                password_matches = bcrypt.checkpw(
                    values.password.encode("utf-8"),
                    user["password_hash"].encode("ascii"),
                )
            except (UnicodeEncodeError, ValueError):
                password_matches = False
        if user is None or not password_matches:
            raise InvalidCredentialsError("Invalid email or password")
        if user["rol"] != _PORTAL_ROLE:
            raise WrongPortalError(
                "This account belongs to the professional portal; sign in there instead"
            )

        return user

    def _issue_token(self, user: dict[str, Any]) -> str:
        now = datetime.now(timezone.utc)
        return jwt.encode(
            {
                "id": user["id"],
                "email": user["email"],
                "rol": user["rol"],
                "sub": str(user["id"]),
                "iat": now,
                "exp": now + timedelta(minutes=self._settings.jwt_expiration_minutes),
            },
            self._get_jwt_secret(),
            algorithm="HS256",
        )

    def authenticate(self, token: str) -> dict[str, Any]:
        try:
            claims = jwt.decode(
                token,
                self._get_jwt_secret(),
                algorithms=["HS256"],
                options={"require": ["exp", "sub"]},
            )
        except ExpiredSignatureError as error:
            raise ExpiredAuthTokenError("Token expired") from error
        except InvalidTokenError as error:
            raise InvalidAuthTokenError("Invalid token") from error

        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject.isdigit():
            raise InvalidAuthTokenError("Invalid token")
        user = self._repository.get_by_id(int(subject))
        if user is None:
            raise InvalidAuthTokenError("Invalid token")
        return user

    def _get_jwt_secret(self) -> str:
        secret: SecretStr | None = self._settings.jwt_secret
        if secret is None:
            raise AuthenticationConfigurationError("JWT_SECRET is not configured")
        value = secret.get_secret_value()
        if (
            not value.strip()
            or len(value.encode("utf-8")) < _MINIMUM_JWT_SECRET_BYTES
        ):
            raise AuthenticationConfigurationError(
                "JWT_SECRET must contain at least 32 bytes"
            )
        return value
