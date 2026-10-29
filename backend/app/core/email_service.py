import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import quote

from app.core.config import settings


class EmailDeliveryError(RuntimeError):
    pass


class EmailService:
    def send_action_link(self, recipient: str, purpose: str, token: str) -> None:
        if not settings.smtp_host or not settings.smtp_sender:
            raise EmailDeliveryError("Email delivery is not configured")
        route = "verify-email" if purpose == "verify_email" else "reset-password"
        link = f"{settings.public_app_url.rstrip('/')}/{route}?token={quote(token, safe='')}"
        message = EmailMessage()
        message["Subject"] = "Verify your college account" if purpose == "verify_email" else "Reset your college account password"
        message["From"] = str(settings.smtp_sender)
        message["To"] = recipient
        message.set_content(
            f"Use this one-time link within 30 minutes:\n\n{link}\n\n"
            "If you did not request this, you can ignore this message."
        )
        try:
            if settings.smtp_ssl:
                with smtplib.SMTP_SSL(
                    settings.smtp_host,
                    settings.smtp_port,
                    timeout=settings.smtp_timeout_seconds,
                    context=ssl.create_default_context(),
                ) as client:
                    self._deliver(client, message)
            else:
                with smtplib.SMTP(
                    settings.smtp_host,
                    settings.smtp_port,
                    timeout=settings.smtp_timeout_seconds,
                ) as client:
                    if settings.smtp_starttls:
                        client.starttls(context=ssl.create_default_context())
                    self._deliver(client, message)
        except (OSError, smtplib.SMTPException) as exc:
            raise EmailDeliveryError("The account email could not be delivered") from exc

    def _deliver(self, client: smtplib.SMTP, message: EmailMessage) -> None:
        if settings.smtp_username and settings.smtp_password:
            client.login(settings.smtp_username, settings.smtp_password.get_secret_value())
        client.send_message(message)
