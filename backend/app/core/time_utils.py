from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def utcnow_naive() -> datetime:
    # Keep UTC semantics while matching existing naive DB DateTime columns.
    return utcnow().replace(tzinfo=None)
