from __future__ import annotations

import bleach
import markdown

_ALLOWED_TAGS = [
    "p",
    "br",
    "strong",
    "em",
    "u",
    "s",
    "ul",
    "ol",
    "li",
    "blockquote",
    "code",
    "pre",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "a",
]

_ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "rel", "target"],
}

_ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def render_safe_markdown(source: str) -> str:
    rendered = markdown.markdown(source or "", extensions=["extra", "sane_lists"])
    return bleach.clean(
        rendered,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        protocols=_ALLOWED_PROTOCOLS,
        strip=True,
    )

