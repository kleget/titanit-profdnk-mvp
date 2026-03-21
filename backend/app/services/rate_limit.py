from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from threading import Lock
from time import monotonic

from fastapi import Request


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Retry-After": str(self.retry_after_seconds),
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining),
        }


class InMemoryRateLimiter:
    """Simple per-key sliding-window limiter for hackathon MVP protection."""

    def __init__(self, *, max_keys: int = 10_000) -> None:
        self._events: dict[str, deque[float]] = {}
        self._max_keys = max_keys
        self._lock = Lock()

    def check(self, key: str, *, limit: int, window_seconds: int) -> RateLimitDecision:
        current_ts = monotonic()
        window_start_ts = current_ts - window_seconds

        with self._lock:
            bucket = self._events.get(key)
            if bucket is None:
                bucket = deque()
                self._events[key] = bucket

            while bucket and bucket[0] <= window_start_ts:
                bucket.popleft()

            if len(bucket) >= limit:
                retry_after_seconds = max(
                    1,
                    int(math.ceil(window_seconds - (current_ts - bucket[0]))),
                )
                return RateLimitDecision(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    retry_after_seconds=retry_after_seconds,
                )

            bucket.append(current_ts)
            self._trim_if_needed()

            remaining = max(0, limit - len(bucket))
            return RateLimitDecision(
                allowed=True,
                limit=limit,
                remaining=remaining,
                retry_after_seconds=0,
            )

    def _trim_if_needed(self) -> None:
        if len(self._events) <= self._max_keys:
            return
        # Удаляем старые/пустые ключи, чтобы ограничить память в долгоживущем процессе.
        for key in list(self._events.keys()):
            bucket = self._events.get(key)
            if bucket is None or not bucket:
                self._events.pop(key, None)
                if len(self._events) <= self._max_keys:
                    return


_rate_limiter = InMemoryRateLimiter()


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        first_ip = forwarded_for.split(",")[0].strip()
        if first_ip:
            return first_ip
    real_ip = request.headers.get("x-real-ip", "").strip()
    if real_ip:
        return real_ip
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def check_request_rate_limit(
    request: Request,
    *,
    scope: str,
    limit: int,
    window_seconds: int,
    key_suffix: str = "",
) -> RateLimitDecision:
    client_ip = _client_ip(request)
    suffix = key_suffix.strip() or "-"
    key = f"{scope}:{client_ip}:{suffix}"
    return _rate_limiter.check(
        key,
        limit=limit,
        window_seconds=window_seconds,
    )
