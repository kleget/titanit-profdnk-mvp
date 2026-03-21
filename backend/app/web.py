from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape

from app.services.csrf import ensure_csrf_token


TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def csrf_input(request) -> Markup:  # type: ignore[no-untyped-def]
    token = ensure_csrf_token(request)
    escaped_token = escape(token)
    return Markup(f'<input type="hidden" name="csrf_token" value="{escaped_token}">')


templates.env.globals["csrf_input"] = csrf_input
