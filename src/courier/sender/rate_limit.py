"""Conservative send rate limiting and time estimates."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class RateLimiter:
    interval_seconds: float = 2.0
    daily_cap: int = 400
    sent_today: int = 0
    day_key: str = ""
    _last_sent_at: float = field(default=0.0, repr=False)

    def reset_day_if_needed(self, day_key: str) -> None:
        if day_key != self.day_key:
            self.day_key = day_key
            self.sent_today = 0

    def can_send(self) -> tuple[bool, str]:
        if self.sent_today >= self.daily_cap:
            return False, (
                f"Daily cap of {self.daily_cap} emails reached. "
                "Gmail consumer accounts are limited to roughly 500/day; "
                "Workspace accounts roughly 2000/day. Raise the cap carefully in Settings."
            )
        return True, ""

    def wait_seconds(self) -> float:
        if self._last_sent_at <= 0:
            return 0.0
        elapsed = time.monotonic() - self._last_sent_at
        remaining = self.interval_seconds - elapsed
        return max(0.0, remaining)

    def mark_sent(self) -> None:
        self._last_sent_at = time.monotonic()
        self.sent_today += 1


def estimate_send_seconds(count: int, interval_seconds: float) -> float:
    if count <= 0:
        return 0.0
    # First send is immediate; remaining wait interval each
    return max(0.0, (count - 1) * max(0.0, interval_seconds))


def format_duration(seconds: float) -> str:
    total = int(round(seconds))
    if total < 60:
        return f"{total}s"
    minutes, secs = divmod(total, 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m"
