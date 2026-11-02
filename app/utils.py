"""Small shared utilities used by route handlers and templates."""

from base64 import b64encode
from datetime import datetime
from io import BytesIO

import qrcode


def parse_datetime_local(value: str):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M")
    except ValueError:
        return None


def qr_data_uri(value: str) -> str:
    """Return a data URI for a QR code containing the registration token."""
    image = qrcode.make(value)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
