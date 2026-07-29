"""Transactional lifecycle for asynchronous document parser jobs.

This module owns only parser job state. It does not fabricate extracted fields and
never writes vehicle history. A worker must claim a document before reading it and
must persist parser output through the existing reviewable draft boundary.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session

from .models import DocumentInboxDocument


class DocumentParserJobError(RuntimeError):
    """Raised when a parser job cannot perform a valid state transition."""


def claim_document_for_processing(session: Session, document_id: str) -> DocumentInboxDocument:
    """Atomically move one uploaded/failed document to ``processing``.

    The conditional UPDATE prevents two workers from claiming the same document.
    ``failed`` documents are intentionally retryable; documents with a saved draft
    or terminal status are not.
    """

    timestamp = datetime.now(timezone.utc)
    result = session.execute(
        update(DocumentInboxDocument)
        .where(
            DocumentInboxDocument.id == document_id,
            DocumentInboxDocument.status.in_(("uploaded", "failed")),
        )
        .values(
            status="processing",
            failure_reason=None,
            updated_at=timestamp,
        )
    )
    if result.rowcount != 1:
        session.rollback()
        raise DocumentParserJobError("Document is not available for processing")

    session.commit()
    document = session.get(DocumentInboxDocument, document_id)
    if document is None:  # defensive: the row existed during the conditional update
        raise DocumentParserJobError("Document disappeared after parser claim")
    return document


def mark_document_processing_failed(
    session: Session,
    document_id: str,
    *,
    reason: str,
) -> DocumentInboxDocument:
    """Move a claimed document to ``failed`` without exposing raw provider errors.

    Callers must pass a stable, operator-safe reason. The value is trimmed and
    bounded before persistence so credentials, prompts, or full provider responses
    are not accidentally stored in the inbox record.
    """

    safe_reason = " ".join(str(reason).split()).strip()
    if not safe_reason:
        raise DocumentParserJobError("Failure reason is required")
    safe_reason = safe_reason[:240]

    timestamp = datetime.now(timezone.utc)
    result = session.execute(
        update(DocumentInboxDocument)
        .where(
            DocumentInboxDocument.id == document_id,
            DocumentInboxDocument.status == "processing",
        )
        .values(
            status="failed",
            failure_reason=safe_reason,
            updated_at=timestamp,
        )
    )
    if result.rowcount != 1:
        session.rollback()
        raise DocumentParserJobError("Document is not currently processing")

    session.commit()
    document = session.get(DocumentInboxDocument, document_id)
    if document is None:
        raise DocumentParserJobError("Document disappeared after parser failure")
    return document
