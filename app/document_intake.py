"""Safe document-intake boundary for the future Document Inbox.

This module validates an incoming automotive document before it is persisted,
parsed, or linked to a service visit. It intentionally performs no OCR and no
automatic history mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib


ALLOWED_DOCUMENT_TYPES = frozenset(
    {
        "receipt",
        "work_order",
        "service_act",
        "diagnostic_report",
        "estimate",
    }
)

MEDIA_SIGNATURES: dict[str, tuple[bytes, str]] = {
    "application/pdf": (b"%PDF-", ".pdf"),
    "image/png": (b"\x89PNG\r\n\x1a\n", ".png"),
    "image/jpeg": (b"\xff\xd8\xff", ".jpg"),
}


class DocumentIntakeError(ValueError):
    """Raised when an incoming document is unsupported or unsafe."""


@dataclass(frozen=True)
class ValidatedDocument:
    document_type: str
    original_name: str
    media_type: str
    suffix: str
    size_bytes: int
    sha256: str


def _safe_original_name(filename: str | None) -> str:
    name = Path(filename or "document").name.strip()
    if not name or name in {".", ".."}:
        return "document"
    return name[:255]


def validate_document_intake(
    *,
    document_type: str,
    filename: str | None,
    media_type: str | None,
    data: bytes,
    max_upload_bytes: int,
) -> ValidatedDocument:
    """Validate one file and return immutable metadata for later persistence.

    The function does not trust the filename extension or browser MIME alone:
    it verifies a known binary signature and computes a SHA-256 digest.
    """

    normalized_type = (document_type or "").strip()
    if normalized_type not in ALLOWED_DOCUMENT_TYPES:
        raise DocumentIntakeError("Unsupported document type")

    if max_upload_bytes <= 0:
        raise DocumentIntakeError("Upload limit must be greater than zero")
    if not data:
        raise DocumentIntakeError("Document is empty")
    if len(data) > max_upload_bytes:
        raise DocumentIntakeError("Document exceeds upload limit")

    normalized_media_type = (media_type or "").split(";", 1)[0].strip().lower()
    signature = MEDIA_SIGNATURES.get(normalized_media_type)
    if signature is None:
        raise DocumentIntakeError("Unsupported media type")

    magic, suffix = signature
    if not data.startswith(magic):
        raise DocumentIntakeError("Document content does not match media type")

    return ValidatedDocument(
        document_type=normalized_type,
        original_name=_safe_original_name(filename),
        media_type=normalized_media_type,
        suffix=suffix,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )
