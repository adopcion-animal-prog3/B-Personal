import logging
import smtplib
from email.message import EmailMessage
from typing import Any

from app.config import Settings

logger = logging.getLogger(__name__)


class Mailer:
    """Envía correos por SMTP, los escribe en el log (desarrollo) o los guarda en memoria (pruebas)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.outbox: list[dict[str, Any]] = []

    def send(self, to: str, subject: str, text: str, html: str) -> None:
        mode = self._settings.resolved_mail_mode()
        if mode == "memory":
            self.outbox.append({"to": to, "subject": subject, "text": text, "html": html})
            return
        if mode == "log":
            logger.info("[mail] Para: %s | %s\n%s", to, subject, text)
            return
        self._send_smtp(self._build_message(to, subject, text, html))

    def _build_message(self, to: str, subject: str, text: str, html: str) -> EmailMessage:
        message = EmailMessage()
        message["From"] = self._settings.mail_from
        message["To"] = to
        message["Subject"] = subject
        message.set_content(text)
        message.add_alternative(html, subtype="html")
        return message

    def _send_smtp(self, message: EmailMessage) -> None:
        settings = self._settings
        smtp_class = smtplib.SMTP_SSL if settings.smtp_secure else smtplib.SMTP
        with smtp_class(settings.smtp_host or "localhost", settings.smtp_port, timeout=15) as server:
            if settings.smtp_starttls and not settings.smtp_secure:
                server.starttls()
            if settings.smtp_user and settings.smtp_password is not None:
                server.login(settings.smtp_user, settings.smtp_password.get_secret_value())
            server.send_message(message)
