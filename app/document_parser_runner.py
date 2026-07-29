"""Provider-neutral runner for producing owner-reviewable document drafts.

The runner owns orchestration only: claim one inbox document, read its private bytes,
invoke an injected parser, validate the structured result and persist exactly one
``DocumentAIDraft``. It never creates service visits or vehicle-history records.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Any, Mapping, Protocol, runtime_checkable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .document_parser_jobs import (
    DocumentParserJobError,
    claim_document_for_processing,
    mark_document_processing_failed,
)
from .document_storage import DocumentStorageError, read_document
from .models import DocumentAIDraft


class DocumentParserRunnerError(RuntimeError):
    """Raised when a parser run cannot safely produce a reviewable draft."""


@dataclass(frozen=True)
class DocumentParserResult:
    """Validated provider-neutral parser output before persistence."""

    extracted_text: str
    proposed_fields: Mapping[str, Any]
    confidence: Mapping[str, float]
    parser_name: str
    parser_version: str


@runtime_checkable
class DocumentParser(Protocol):
    """Minimal adapter contract implemented by OCR/AI providers."""

    def parse(self, *, content: bytes, media_type: str) -> DocumentParserResult:
        """Extract a structured draft from one private document payload."""


def _json_object(value: Mapping[str, Any], field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise DocumentParserRunnerError(f"{field_name} must be an object")
    normalized = dict(value)
    try:
        json.dumps(normalized, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError) as error:
        raise DocumentParserRunnerError(f"{field_name} must be JSON serializable") from error
    return normalized


def _validate_result(result: DocumentParserResult) -> tuple[dict[str, Any], dict[str, float]]:
    if not isinstance(result, DocumentParserResult):
        raise DocumentParserRunnerError("Parser returned an unsupported result")
    if not isinstance(result.extracted_text, str):
        raise DocumentParserRunnerError("extracted_text must be a string")

    parser_name = result.parser_name.strip()
    parser_version = result.parser_version.strip()
    if not parser_name or not parser_version:
        raise DocumentParserRunnerError("parser_name and parser_version are required")

    proposed_fields = _json_object(result.proposed_fields, "proposed_fields")
    raw_confidence = _json_object(result.confidence, "confidence")
    confidence: dict[str, float] = {}
    for field, value in raw_confidence.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise DocumentParserRunnerError(f"Confidence for {field} must be a number")
        normalized = float(value)
        if not 0 <= normalized <= 1:
            raise DocumentParserRunnerError(f"Confidence for {field} must be between 0 and 1")
        confidence[str(field)] = normalized
    return proposed_fields, confidence


def _safe_failure_reason(error: Exception) -> str:
    if isinstance(error, DocumentStorageError):
        return "Document storage read failed"
    if isinstance(error, IntegrityError):
        return "Document draft persistence conflict"
    if isinstance(error, DocumentParserRunnerError):
        return str(error)
    return "Document parser failed"


def run_document_parser(
    session: Session,
    document_id: str,
    parser: DocumentParser,
) -> DocumentAIDraft:
    """Run one claimed document through an injected parser and save a review draft.

    Provider exceptions are deliberately reduced to an operator-safe status reason.
    Raw provider responses, prompts and credentials are never persisted here.
    """

    document = claim_document_for_processing(session, document_id)
    try:
        existing = session.scalar(
            select(DocumentAIDraft).where(DocumentAIDraft.document_id == document.id)
        )
        if existing is not None:
            raise DocumentParserRunnerError("Document draft already exists")

        content = read_document(document.stored_name)
        result = parser.parse(content=content, media_type=document.media_type)
        proposed_fields, confidence = _validate_result(result)

        timestamp = datetime.now(timezone.utc)
        draft = DocumentAIDraft(
            document_id=document.id,
            owner_id=document.owner_id,
            vehicle_id=document.vehicle_id,
            extracted_text=result.extracted_text,
            proposed_fields_json=json.dumps(
                proposed_fields, ensure_ascii=False, sort_keys=True
            ),
            confidence_json=json.dumps(confidence, ensure_ascii=False, sort_keys=True),
            parser_name=result.parser_name.strip()[:80],
            parser_version=result.parser_version.strip()[:40],
            status="needs_review",
            created_at=timestamp,
            updated_at=timestamp,
        )
        document.status = "needs_review"
        document.failure_reason = None
        document.updated_at = timestamp
        session.add(draft)
        session.commit()
        session.refresh(draft)
        return draft
    except DocumentParserJobError:
        session.rollback()
        raise
    except Exception as error:
        session.rollback()
        try:
            mark_document_processing_failed(
                session,
                document.id,
                reason=_safe_failure_reason(error),
            )
        except DocumentParserJobError:
            session.rollback()
        if isinstance(error, DocumentParserRunnerError):
            raise
        raise DocumentParserRunnerError("Document parser run failed") from error
