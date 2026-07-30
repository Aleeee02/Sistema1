import asyncio

from app.core.config import settings
from app.services.email import send_password_reset_email


def test_password_reset_email_is_skipped_without_smtp(monkeypatch) -> None:
    monkeypatch.setattr(settings, "smtp_host", None)
    monkeypatch.setattr(settings, "smtp_from_email", None)
    monkeypatch.setattr(settings, "brevo_api_key", None)
    monkeypatch.setattr(settings, "brevo_from_email", None)

    sent = asyncio.run(
        send_password_reset_email("usuario@example.com", "token")
    )

    assert sent is False
