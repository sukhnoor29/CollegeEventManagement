"""Consistent naive local timestamps for HTML datetime-local form fields.

The timezone is configurable with APP_TIMEZONE; the project defaults to
Asia/Kolkata for the intended college deployment context.
"""

import os
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()


TIMEZONE = ZoneInfo(os.getenv("APP_TIMEZONE", "Asia/Kolkata"))


def now_local() -> datetime:
    """Return the configured local time without tzinfo for database fields."""
    return datetime.now(TIMEZONE).replace(tzinfo=None)
