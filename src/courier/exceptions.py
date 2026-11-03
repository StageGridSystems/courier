"""Application-level exceptions with user-facing messages."""

from __future__ import annotations


class CourierError(Exception):
    """Base error with an optional user-facing message."""

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


class AuthError(CourierError):
    """OAuth / credential problems."""


class AudienceError(CourierError):
    """Audience parsing or import problems."""


class SendError(CourierError):
    """Outbound send / queue problems."""


class ConfigError(CourierError):
    """Persistence / import-export problems."""
