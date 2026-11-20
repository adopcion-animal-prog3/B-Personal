from typing import Any

from sqlalchemy.engine import Engine

from app.models.mensaje import MensajeCreate
from app.repositories.mascotas import MascotaRepository
from app.repositories.mensajes import MensajeRepository
from app.services.mascotas import MascotaNotFoundError
from app.services.policies import BusinessRuleViolationError


class UsuarioNotFoundError(Exception):
    def __init__(self, user_id: int) -> None:
        super().__init__(f"Usuario {user_id} not found")


class SelfMessageError(BusinessRuleViolationError):
    pass


def build_conversaciones(
    mensajes: list[dict[str, Any]],
    user_id: int,
    usuarios: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Agrupa los mensajes por la otra cuenta y resume cada conversación."""
    conversaciones: dict[int, dict[str, Any]] = {}
    for mensaje in mensajes:
        propio = mensaje["remitente_id"] == user_id
        otro_id = mensaje["destinatario_id"] if propio else mensaje["remitente_id"]
        actual = conversaciones.setdefault(otro_id, {"no_leidos": 0})
        actual["ultimo_mensaje"] = mensaje
        if not propio and not mensaje["leido"]:
            actual["no_leidos"] += 1
    resultado = [
        {"usuario": usuarios[otro_id], **datos}
        for otro_id, datos in conversaciones.items()
        if otro_id in usuarios
    ]
    return sorted(resultado, key=lambda item: item["ultimo_mensaje"]["id"], reverse=True)


class MensajeService:
    """Mensajes directos entre cuentas; la tabla es compartida con B-Profesional."""

    def __init__(self, engine: Engine | None) -> None:
        self._repository = MensajeRepository(engine)
        self._mascotas = MascotaRepository(engine)

    def list_conversaciones(self, user: dict[str, Any]) -> list[dict[str, Any]]:
        mensajes = self._repository.list_for_user(user["id"])
        otros = {m["remitente_id"] for m in mensajes} | {m["destinatario_id"] for m in mensajes}
        otros.discard(user["id"])
        return build_conversaciones(mensajes, user["id"], self._repository.get_users(otros))

    def get_conversacion(self, user: dict[str, Any], other_id: int) -> dict[str, Any]:
        otro = self._require_user(other_id)
        return {"usuario": otro, "mensajes": self._repository.conversation(user["id"], other_id)}

    def mark_read(self, user: dict[str, Any], other_id: int) -> int:
        self._require_user(other_id)
        return self._repository.mark_read(user["id"], other_id)

    def create(self, values: MensajeCreate, user: dict[str, Any]) -> dict[str, Any]:
        if values.destinatario_id == user["id"]:
            raise SelfMessageError("You cannot send a message to yourself")
        self._require_user(values.destinatario_id)
        if values.mascota_id is not None and self._mascotas.get(values.mascota_id) is None:
            raise MascotaNotFoundError(values.mascota_id)
        return self._repository.create(
            {
                "remitente_id": user["id"],
                "destinatario_id": values.destinatario_id,
                "mascota_id": values.mascota_id,
                "contenido": values.contenido,
                "leido": False,
            }
        )

    def _require_user(self, user_id: int) -> dict[str, Any]:
        usuario = self._repository.get_user(user_id)
        if usuario is None:
            raise UsuarioNotFoundError(user_id)
        return usuario
