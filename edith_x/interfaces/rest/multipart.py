"""Pure Python Standard Library Multipart/Form-Data Parser (Zero External Dependencies)."""
from __future__ import annotations

import email
from email.message import Message
from typing import Tuple


def parse_multipart_form(body: bytes, content_type: str) -> tuple[bytes, str, str]:
    """Extract (file_bytes, filename, purpose) from raw HTTP body using stdlib email parser.
    
    Avoids requiring python-multipart.
    """
    if not content_type:
        return body, "file.bin", "assistants"

    # Email parser expects header followed by empty line and payload
    header = f"Content-Type: {content_type}\r\n\r\n".encode("latin-1")
    msg = email.message_from_bytes(header + body)

    file_bytes = b""
    filename = "uploaded_file.bin"
    purpose = "assistants"

    for part in msg.walk():
        fn = part.get_filename()
        cd = part.get("Content-Disposition", "")
        if fn:
            filename = fn
            file_bytes = part.get_payload(decode=True) or b""
        elif 'name="purpose"' in cd:
            payload = part.get_payload(decode=True)
            if payload:
                purpose = payload.decode("utf-8", errors="ignore").strip()

    # If no filename in parts, fallback to raw body if present
    if not file_bytes and body:
        file_bytes = body

    return file_bytes, filename, purpose
