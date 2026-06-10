"""Open and decrypt PDFs, returning unencrypted PDF bytes."""

import io
from pathlib import Path

import pikepdf


class PasswordRequired(Exception):
    """Raised when a PDF needs an open password that was not supplied (or was wrong)."""


def decrypt_to_bytes(path, password: str = "") -> bytes:
    """Return the bytes of ``path`` with all encryption removed.

    Owner-only restrictions are stripped automatically. A PDF that needs a user
    password to open raises :class:`PasswordRequired` unless the correct
    password is given.
    """
    try:
        pdf = pikepdf.open(str(path), password=password)
    except pikepdf.PasswordError as exc:
        raise PasswordRequired(str(path)) from exc

    out = io.BytesIO()
    with pdf:
        pdf.save(out)  # default save writes an unencrypted PDF
    return out.getvalue()
