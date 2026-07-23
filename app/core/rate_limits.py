"""Small bounded in-process rate limiting for local credential endpoints."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock
from time import monotonic


@dataclass(frozen=True)
class RateLimitResult:
    """Outcome of a rate-limit check with an optional retry delay."""

    allowed: bool
    retry_after_seconds: int = 0


class LoginRateLimiter:
    """Bound failed credential attempts by client address without retaining passwords.

    The bounded local structure deliberately resets on restart. It protects the
    single-process, SQLite-first deployment without adding a cache service.
    """

    def __init__(self, maximum_attempts: int, window_seconds: int, capacity: int = 1_000) -> None:
        self._maximum_attempts = maximum_attempts
        self._window_seconds = window_seconds
        self._capacity = capacity
        self._attempts: OrderedDict[str, tuple[int, float]] = OrderedDict()
        self._lock = Lock()

    def check(self, client_key: str) -> RateLimitResult:
        """Return whether another authentication attempt is currently permitted."""

        with self._lock:
            entry = self._attempts.get(client_key)
            if entry is None:
                return RateLimitResult(allowed=True)
            attempts, started_at = entry
            elapsed = monotonic() - started_at
            if elapsed >= self._window_seconds:
                self._attempts.pop(client_key, None)
                return RateLimitResult(allowed=True)
            self._attempts.move_to_end(client_key)
            if attempts < self._maximum_attempts:
                return RateLimitResult(allowed=True)
            return RateLimitResult(
                allowed=False, retry_after_seconds=max(1, int(self._window_seconds - elapsed))
            )

    def record_failure(self, client_key: str) -> None:
        """Record one failed attempt while keeping memory use bounded."""

        with self._lock:
            entry = self._attempts.get(client_key)
            now = monotonic()
            if entry is None or now - entry[1] >= self._window_seconds:
                self._attempts[client_key] = (1, now)
            else:
                self._attempts[client_key] = (entry[0] + 1, entry[1])
            self._attempts.move_to_end(client_key)
            while len(self._attempts) > self._capacity:
                self._attempts.popitem(last=False)

    def clear(self, client_key: str) -> None:
        """Forget failed attempts after successful authentication."""

        with self._lock:
            self._attempts.pop(client_key, None)
