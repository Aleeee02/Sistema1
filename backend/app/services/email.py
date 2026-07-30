import asyncio
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

import httpx

from app.core.config import settings


def _send_message(message: EmailMessage) -> None:
    context = ssl.create_default_context()
    if settings.smtp_use_ssl:
        client = smtplib.SMTP_SSL(
            settings.smtp_host,
            settings.smtp_port,
            timeout=15,
            context=context,
        )
    else:
        client = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)

    with client:
        if settings.smtp_use_tls and not settings.smtp_use_ssl:
            client.starttls(context=context)
        if settings.smtp_username and settings.smtp_password:
            client.login(settings.smtp_username, settings.smtp_password)
        client.send_message(message)


async def send_password_reset_email(recipient: str, token: str) -> bool:
    if not settings.brevo_configured and not settings.smtp_configured:
        return False

    reset_url = (
        f"{settings.frontend_url.rstrip('/')}/restablecer-password?token={token}"
    )
    text_content = (
        "Recibimos una solicitud para restablecer tu contraseña.\n\n"
        f"Abre este enlace durante los próximos 30 minutos:\n{reset_url}\n\n"
        "Si no realizaste esta solicitud, ignora este mensaje."
    )
    html_content = f"""
        <html>
          <body style="font-family:Arial,sans-serif;color:#0f172a">
            <h2>Restablece tu contraseña</h2>
            <p>Recibimos una solicitud para restablecer tu contraseña.</p>
            <p>
              <a href="{reset_url}" style="display:inline-block;padding:12px 18px;
              background:#2563eb;color:white;text-decoration:none;border-radius:8px">
                Crear nueva contraseña
              </a>
            </p>
            <p>El enlace vence en 30 minutos.</p>
            <p>Si no realizaste esta solicitud, ignora este mensaje.</p>
          </body>
        </html>
        """

    if settings.brevo_configured:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "api-key": settings.brevo_api_key or "",
                    "accept": "application/json",
                    "content-type": "application/json",
                },
                json={
                    "sender": {
                        "email": settings.brevo_from_email,
                        "name": settings.brevo_from_name,
                    },
                    "to": [{"email": recipient}],
                    "subject": "Restablece tu contraseña",
                    "textContent": text_content,
                    "htmlContent": html_content,
                    "tags": ["password-reset"],
                },
            )
            response.raise_for_status()
        return True

    message = EmailMessage()
    message["Subject"] = "Restablece tu contraseña"
    message["From"] = formataddr(
        (settings.smtp_from_name, settings.smtp_from_email or "")
    )
    message["To"] = recipient
    message.set_content(text_content)
    message.add_alternative(html_content, subtype="html")
    await asyncio.to_thread(_send_message, message)
    return True


async def send_subscription_alert_email(
    recipient: str,
    company_name: str,
    subject: str,
    message_text: str,
) -> bool:
    if not settings.brevo_configured and not settings.smtp_configured:
        return False
    html_content = f"""
    <html><body style="font-family:Arial,sans-serif;color:#0f172a">
      <h2>{subject}</h2>
      <p>Empresa: <strong>{company_name}</strong></p>
      <p>{message_text}</p>
      <p>Si ya realizaste el pago, comunícate con el administrador de la plataforma.</p>
    </body></html>
    """
    if settings.brevo_configured:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={"api-key": settings.brevo_api_key or "", "accept": "application/json", "content-type": "application/json"},
                json={
                    "sender": {"email": settings.brevo_from_email, "name": settings.brevo_from_name},
                    "to": [{"email": recipient}],
                    "subject": subject,
                    "textContent": f"{company_name}\n\n{message_text}",
                    "htmlContent": html_content,
                    "tags": ["subscription-alert"],
                },
            )
            response.raise_for_status()
        return True
    email = EmailMessage()
    email["Subject"] = subject
    email["From"] = formataddr((settings.smtp_from_name, settings.smtp_from_email or ""))
    email["To"] = recipient
    email.set_content(f"{company_name}\n\n{message_text}")
    email.add_alternative(html_content, subtype="html")
    await asyncio.to_thread(_send_message, email)
    return True
