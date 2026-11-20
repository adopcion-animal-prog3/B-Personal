import hashlib
import hmac
import secrets
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Engine

from app.repositories.verification import VerificationRepository
from app.services.email_templates import build_code_email
from app.services.mailer import Mailer

CODE_TTL_MINUTES = 10
MAX_ATTEMPTS = 5
RESEND_COOLDOWN_SECONDS = 60


class VerificationError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


def _as_utc(value: Any) -> datetime:
    moment = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


class VerificationService:
    """Genera, envía y valida códigos de 6 dígitos para registro e inicio de sesión."""

    def __init__(self, engine: Engine | None, mailer: Mailer, secret: Callable[[], str]) -> None:
        self._repository = VerificationRepository(engine)
        self._mailer = mailer
        self._secret = secret

    def issue(self, user: dict[str, Any], proposito: str) -> dict[str, Any]:
        code = f"{secrets.randbelow(1_000_000):06d}"
        expira_en = datetime.now(timezone.utc) + timedelta(minutes=CODE_TTL_MINUTES)
        self._repository.replace_code(user["id"], proposito, self._hash(user["id"], code), expira_en)
        email = build_code_email(user["nombre"], code, proposito, CODE_TTL_MINUTES)
        self._mailer.send(user["email"], email["subject"], email["text"], email["html"])
        return {"email": user["email"], "proposito": proposito, "expira_en_minutos": CODE_TTL_MINUTES}

    def resend(self, user: dict[str, Any]) -> None:
        active = self._repository.active_code(user["id"])
        if active is None:
            return
        elapsed = datetime.now(timezone.utc) - _as_utc(active["created_at"])
        if elapsed.total_seconds() < RESEND_COOLDOWN_SECONDS:
            raise VerificationError(429, "Wait a minute before requesting a new code")
        self.issue(user, active["proposito"])

    def consume(self, user_id: int, code: str) -> None:
        active = self._repository.active_code(user_id)
        if active is None or _as_utc(active["expira_en"]) < datetime.now(timezone.utc):
            raise VerificationError(400, "The code expired; request a new one")
        if active["intentos"] >= MAX_ATTEMPTS:
            raise VerificationError(429, "Too many attempts; request a new code")
        if not hmac.compare_digest(active["codigo_hash"], self._hash(user_id, code)):
            self._repository.register_failed_attempt(active["id"], active["intentos"] + 1)
            raise VerificationError(400, "Invalid verification code")
        self._repository.mark_used_and_verify(active["id"], user_id)

    def _hash(self, user_id: int, code: str) -> str:
        key = self._secret().encode("utf-8")
        return hmac.new(key, f"{user_id}:{code}".encode(), hashlib.sha256).hexdigest()
