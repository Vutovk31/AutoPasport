"""Recovery sweep for inbox documents that were not accepted by a parser queue.

The sweep is intentionally transport-neutral. It only redelivers persisted document IDs
through the existing dispatch boundary; it never reads document bytes, invokes OCR,
creates drafts, service visits, or vehicle-history records.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from .document_parser_dispatch import ParserDispatchResult, dispatch_document_for_parsing
from .models import DocumentInboxDocument


@dataclass(frozen=True)
class ParserRecoveryReport:
    scanned: int
    accepted: int
    declined: int


def recover_unqueued_documents(
    session: Session,
    *,
    limit: int = 100,
    minimum_age_seconds: int = 30,
    dispatch: Callable[[str], ParserDispatchResult] = dispatch_document_for_parsing,
) -> ParserRecoveryReport:
    """Best-effort redelivery for durable documents still awaiting parser processing.

    Only ``uploaded`` documents older than the safety window are considered. A bounded
    batch prevents an application startup or scheduled sweep from flooding the queue.
    Dispatch failures remain non-destructive: document status and stored content are not
    changed here, allowing a later sweep to retry them again.
    """

    if limit < 1 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")
    if minimum_age_seconds < 0:
        raise ValueError("minimum_age_seconds must be non-negative")

    cutoff = datetime.now(timezone.utc) - timedelta(seconds=minimum_age_seconds)
    documents = session.scalars(
        select(DocumentInboxDocument)
        .where(
            DocumentInboxDocument.status == "uploaded",
            DocumentInboxDocument.created_at <= cutoff,
        )
        .order_by(DocumentInboxDocument.created_at.asc(), DocumentInboxDocument.id.asc())
        .limit(limit)
    ).all()

    accepted = 0
    for document in documents:
        result = dispatch(document.id)
        if result.accepted:
            accepted += 1

    scanned = len(documents)
    return ParserRecoveryReport(
        scanned=scanned,
        accepted=accepted,
        declined=scanned - accepted,
    )
