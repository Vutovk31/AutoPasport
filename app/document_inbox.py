"""Document Inbox lifecycle for uploaded automotive documents.

The inbox is a staging area between safe file intake and vehicle-history mutation.
A document may be uploaded, processed and reviewed without creating a service
visit. Only an explicit owner confirmation may move it to ``confirmed``.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone


UPLOADED = "uploaded"
PROCESSING = "processing"
NEEDS_REVIEW = "needs_review"
CONFIRMED = "confirmed"
FAILED = "failed"
ARCHIVED = "archived"

DOCUMENT_STATUSES = frozenset(
    {UPLOADED, PROCESSING, NEEDS_REVIEW, CONFIRMED, FAILED, ARCHIVED}
)

_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    UPLOADED: frozenset({PROCESSING, ARCHIVED}),
    PROCESSING: frozenset({NEEDS_REVIEW, FAILED}),
    NEEDS_REVIEW: frozenset({CONFIRMED, PROCESSING, ARCHIVED}),
    FAILED: frozenset({PROCESSING, ARCHIVED}),
    CONFIRMED: frozenset({ARCHIVED}),
    ARCHIVED: frozenset(),
}


class DocumentInboxError(ValueError):
    """Raised when a document-inbox state change violates the lifecycle."""


@dataclass(frozen=True)
class DocumentInboxItem:
    id: str
    owner_id: str
    vehicle_id: str
    document_type: str
    original_name: str
    stored_name: str
    media_type: str
    size_bytes: int
    sha256: str
    status: str = UPLOADED
    linked_visit_id: str | None = None
    failure_reason: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        required = {
            "id": self.id,
            "owner_id": self.owner_id,
            "vehicle_id": self.vehicle_id,
            "document_type": self.document_type,
            "original_name": self.original_name,
            "stored_name": self.stored_name,
            "media_type": self.media_type,
            "sha256": self.sha256,
        }
        missing = [name for name, value in required.items() if not str(value).strip()]
        if missing:
            raise DocumentInboxError(f"Missing required fields: {', '.join(missing)}")
        if self.status not in DOCUMENT_STATUSES:
            raise DocumentInboxError("Unsupported document status")
        if self.size_bytes <= 0:
            raise DocumentInboxError("Document size must be greater than zero")
        if len(self.sha256) != 64:
            raise DocumentInboxError("SHA-256 must contain 64 hexadecimal characters")
        try:
            int(self.sha256, 16)
        except ValueError as exc:
            raise DocumentInboxError("SHA-256 must be hexadecimal") from exc
        if self.status == FAILED and not (self.failure_reason or "").strip():
            raise DocumentInboxError("Failed document requires a failure reason")
        if self.status != FAILED and self.failure_reason is not None:
            raise DocumentInboxError("Failure reason is allowed only for failed documents")
        if self.linked_visit_id is not None and self.status != CONFIRMED:
            raise DocumentInboxError("A visit may be linked only after owner confirmation")


def transition_document(
    item: DocumentInboxItem,
    target_status: str,
    *,
    linked_visit_id: str | None = None,
    failure_reason: str | None = None,
    changed_at: datetime | None = None,
) -> DocumentInboxItem:
    """Return a new inbox item after a valid explicit lifecycle transition."""

    if target_status not in DOCUMENT_STATUSES:
        raise DocumentInboxError("Unsupported document status")
    if target_status not in _ALLOWED_TRANSITIONS[item.status]:
        raise DocumentInboxError(
            f"Transition from {item.status} to {target_status} is not allowed"
        )

    if target_status == CONFIRMED and not (linked_visit_id or "").strip():
        raise DocumentInboxError("Confirmed document requires a linked visit")
    if target_status != CONFIRMED and linked_visit_id is not None:
        raise DocumentInboxError("Visit link is allowed only when confirming a document")
    if target_status == FAILED and not (failure_reason or "").strip():
        raise DocumentInboxError("Failed document requires a failure reason")
    if target_status != FAILED and failure_reason is not None:
        raise DocumentInboxError("Failure reason is allowed only for failed documents")

    timestamp = changed_at or datetime.now(timezone.utc)
    return replace(
        item,
        status=target_status,
        linked_visit_id=linked_visit_id if target_status == CONFIRMED else None,
        failure_reason=failure_reason.strip() if target_status == FAILED else None,
        updated_at=timestamp,
    )
