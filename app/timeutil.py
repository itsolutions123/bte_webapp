"""Timestamp display helper.

Storage stays UTC (timestamptz). Responses show times in the app timezone
(default Philippine Time) as ISO 8601 with offset, per docs/API_CONTRACT.md
Global Rules (Timestamps). The zone comes from APP_TIMEZONE; the default is
defined only here.
"""
import os
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

DEFAULT_TIMEZONE = "Asia/Manila"

# An invalid APP_TIMEZONE raises at import, so a typo fails loudly at startup.
APP_TIMEZONE = ZoneInfo(os.environ.get("APP_TIMEZONE", DEFAULT_TIMEZONE))


def to_app_tz(value: Optional[datetime]) -> Optional[datetime]:
    """Convert a datetime to the app timezone. None stays None.
    A naive datetime is assumed to be UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(APP_TIMEZONE)
