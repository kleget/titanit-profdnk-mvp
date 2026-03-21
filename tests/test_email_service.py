from __future__ import annotations

from types import SimpleNamespace

from app.services import email as email_service


class DummySMTP:
    def __init__(self) -> None:
        self.ehlo_calls = 0
        self.tls_started = False
        self.login_payload: tuple[str, str] | None = None
        self.last_message = None

    def __enter__(self) -> "DummySMTP":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        return None

    def ehlo(self) -> None:
        self.ehlo_calls += 1

    def starttls(self, context) -> None:  # type: ignore[no-untyped-def]
        self.tls_started = True

    def login(self, user: str, password: str) -> None:
        self.login_payload = (user, password)

    def send_message(self, message) -> None:  # type: ignore[no-untyped-def]
        self.last_message = message


def test_send_email_message_skips_when_smtp_disabled(monkeypatch):  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        email_service,
        "settings",
        SimpleNamespace(
            smtp_enabled=False,
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_password="secret",
            smtp_from="user@example.com",
            smtp_tls=True,
            smtp_timeout_seconds=15,
        ),
    )

    sent = email_service.send_email_message(
        to_email="client@example.com",
        subject="Test",
        text_body="Body",
    )

    assert sent is False


def test_send_email_message_uses_tls_and_login(monkeypatch):  # type: ignore[no-untyped-def]
    smtp_stub = DummySMTP()
    monkeypatch.setattr(
        email_service,
        "settings",
        SimpleNamespace(
            smtp_enabled=True,
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="mailer@example.com",
            smtp_password="secret",
            smtp_from="mailer@example.com",
            smtp_tls=True,
            smtp_timeout_seconds=15,
        ),
    )
    monkeypatch.setattr(
        email_service.smtplib,
        "SMTP",
        lambda host, port, timeout: smtp_stub,
    )

    sent = email_service.send_email_message(
        to_email="client@example.com",
        subject="Тема письма",
        text_body="Текст",
    )

    assert sent is True
    assert smtp_stub.tls_started is True
    assert smtp_stub.login_payload == ("mailer@example.com", "secret")
    assert smtp_stub.last_message is not None
    assert smtp_stub.last_message["To"] == "client@example.com"
    assert smtp_stub.last_message["Subject"] == "Тема письма"
