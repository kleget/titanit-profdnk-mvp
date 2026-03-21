from __future__ import annotations

import re
from typing import Any

from fastapi.testclient import TestClient


CSRF_TOKEN_RE = re.compile(r'name="csrf_token"\s+value="([^"]+)"')


def extract_csrf_token(html: str) -> str:
    match = CSRF_TOKEN_RE.search(html)
    if not match:
        raise AssertionError("CSRF token not found in HTML response")
    return match.group(1)


def fetch_csrf_token(client: TestClient, page_path: str) -> str:
    response = client.get(page_path, follow_redirects=True)
    assert response.status_code == 200
    return extract_csrf_token(response.text)


def post_form_with_csrf(
    client: TestClient,
    post_path: str,
    *,
    data: dict[str, Any],
    csrf_page_path: str,
    follow_redirects: bool = False,
):
    payload = dict(data)
    payload["csrf_token"] = fetch_csrf_token(client, csrf_page_path)
    return client.post(post_path, data=payload, follow_redirects=follow_redirects)
