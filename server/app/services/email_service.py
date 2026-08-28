import logging

import aiosmtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


async def _send(to: str, subject: str, text_body: str) -> None:
    if settings.EMAIL_PROVIDER != "smtp":
        # No real mail provider configured -- log instead of sending, the
        # same "zero external calls until configured" default PAYMENT_PROVIDER
        # uses for payments.
        logger.info("email (EMAIL_PROVIDER=%s, not sent) to=%s subject=%r", settings.EMAIL_PROVIDER, to, subject)
        return

    message = EmailMessage()
    message["From"] = settings.EMAILS_FROM_EMAIL or settings.SMTP_USER
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text_body)

    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        start_tls=True,
    )


async def send_password_reset_email(to: str, reset_link: str) -> None:
    subject = "Reset your password"
    body = (
        "We received a request to reset your password.\n\n"
        f"Reset it here (expires in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes):\n{reset_link}\n\n"
        "If you didn't request this, you can safely ignore this email."
    )
    await _send(to, subject, body)
