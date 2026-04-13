from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings


logger = logging.getLogger(__name__)


def can_send_password_reset_email() -> bool:
    if not settings.auth_password_reset_email_enabled:
        return False
    required = [settings.smtp_host, settings.smtp_username, settings.smtp_password, settings.smtp_from_email]
    return all(required)


def send_password_reset_code_email(to_email: str, reset_code: str, ttl_minutes: int) -> bool:
    if not can_send_password_reset_email():
        return False

    message = EmailMessage()
    message["Subject"] = "Zaytoun Password Reset Code"
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = to_email
    message.set_content(
        "You requested a password reset for your Zaytoun account.\n\n"
        f"Reset code: {reset_code}\n"
        f"This code expires in {ttl_minutes} minutes.\n\n"
        "If you did not request this, you can safely ignore this email."
    )

    try:
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as server:
                server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(message)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
                if settings.smtp_use_tls:
                    server.starttls()
                server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(message)
        return True
    except Exception:
        logger.exception("Failed to send password reset email.")
        return False
