from __future__ import annotations

import logging
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger("profdnk.email")


def smtp_configured() -> bool:
    return bool(
        settings.smtp_enabled
        and settings.smtp_host
        and settings.smtp_port
        and settings.smtp_user
        and settings.smtp_password
        and settings.smtp_from
    )


def send_email_message(
    *,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> bool:
    if not smtp_configured():
        logger.info("email skipped: smtp is not configured or disabled")
        return False

    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to_email.strip()
    message["Subject"] = subject
    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(
            settings.smtp_host,
            settings.smtp_port,
            timeout=settings.smtp_timeout_seconds,
        ) as smtp_client:
            smtp_client.ehlo()
            if settings.smtp_tls:
                smtp_client.starttls(context=ssl.create_default_context())
                smtp_client.ehlo()
            smtp_client.login(settings.smtp_user, settings.smtp_password)
            smtp_client.send_message(message)
        return True
    except Exception:
        logger.exception(
            "email send failed recipient=%s subject=%s",
            to_email,
            subject,
        )
        return False


def send_psychologist_welcome_email(
    *,
    to_email: str,
    full_name: str,
    password: str,
    access_until: datetime | None,
    login_url: str,
) -> bool:
    access_text = access_until.strftime("%Y-%m-%d") if access_until else "без ограничения"
    subject = "ПрофДНК: доступ к кабинету психолога"
    text_body = (
        f"Здравствуйте, {full_name}!\n\n"
        "Для вас создан аккаунт в платформе ПрофДНК.\n"
        f"Логин: {to_email}\n"
        f"Пароль: {password}\n"
        f"Доступ до: {access_text}\n\n"
        f"Вход: {login_url}\n\n"
        "Рекомендуем после входа сменить пароль у администратора."
    )
    html_body = (
        f"<p>Здравствуйте, <strong>{full_name}</strong>!</p>"
        "<p>Для вас создан аккаунт в платформе ПрофДНК.</p>"
        f"<p>Логин: <strong>{to_email}</strong><br>"
        f"Пароль: <strong>{password}</strong><br>"
        f"Доступ до: <strong>{access_text}</strong></p>"
        f"<p><a href=\"{login_url}\">Перейти ко входу</a></p>"
        "<p>Рекомендуем после входа сменить пароль у администратора.</p>"
    )
    return send_email_message(
        to_email=to_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )


def send_client_report_email(
    *,
    to_email: str,
    client_name: str,
    test_title: str,
    report_url: str,
) -> bool:
    subject = f"ПрофДНК: результат теста «{test_title}»"
    text_body = (
        f"Здравствуйте, {client_name}!\n\n"
        f"Ваш результат по методике «{test_title}» готов.\n"
        f"Открыть отчёт: {report_url}\n\n"
        "Письмо отправлено автоматически сервисом ПрофДНК."
    )
    html_body = (
        f"<p>Здравствуйте, <strong>{client_name}</strong>!</p>"
        f"<p>Ваш результат по методике <strong>«{test_title}»</strong> готов.</p>"
        f"<p><a href=\"{report_url}\">Открыть отчёт</a></p>"
        "<p>Письмо отправлено автоматически сервисом ПрофДНК.</p>"
    )
    return send_email_message(
        to_email=to_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )
