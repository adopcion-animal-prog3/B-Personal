from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: SecretStr | None = None
    log_level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"] = "INFO"
    jwt_secret: SecretStr | None = None
    jwt_expiration_minutes: int = Field(default=60, gt=0)
    # Correo: smtp (envío real), log (escribe el correo en el log, solo desarrollo)
    # o memory (pruebas). Sin MAIL_MODE se usa smtp si hay SMTP_HOST, si no log.
    mail_mode: Literal["smtp", "log", "memory"] | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: SecretStr | None = None
    smtp_secure: bool = False
    smtp_starttls: bool = False
    mail_from: str = "Huellitas <no-reply@huellitas.local>"

    def resolved_mail_mode(self) -> str:
        if self.mail_mode is not None:
            return self.mail_mode
        return "smtp" if self.smtp_host else "log"
