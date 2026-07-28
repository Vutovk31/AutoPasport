"""Owner review boundary for document AI drafts.

This router lets an authenticated owner correct parser output while the draft
remains in ``needs_review``. It deliberately does not create service visits,
attachments, events, or any other vehicle-history record.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import DocumentAIDraft, DocumentInboxDocument, User
from .security import db, mutation_guard


router = APIRouter(tags=["document-draft-review"])


def _owned_document(session: Session, user: User, document_id: str) -> DocumentInboxDocument:
    document = session.get(DocumentInboxDocument, document_id)
    if document is None:
        raise HTTPException(404, "Document not found")
    if document.owner_id != user.id:
        raise HTTPException(403, "Forbidden")
    return document


def _owned_draft(session: Session, user: User, document_id: str) -> DocumentAIDraft:
    draft = session.scalar(
        select(DocumentAIDraft).where(
            DocumentAIDraft.document_id == document_id,
            DocumentAIDraft.owner_id == user.id,
        )
    )
    if draft is None:
        raise HTTPException(404, "Draft not found")
    return draft


def _object_field(payload: dict, name: str, current_json: str) -> dict:
    if name not in payload:
        return json.loads(current_json)
    value = payload[name]
    if not isinstance(value, dict):
        raise HTTPException(422, f"{name} must be an object")
    return value


def _validate_confidence(confidence: dict) -> None:
    for field, value in confidence.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise HTTPException(422, f"Confidence for {field} must be a number")
        if not 0 <= float(value) <= 1:
            raise HTTPException(422, f"Confidence for {field} must be between 0 and 1")


def _serialize(draft: DocumentAIDraft) -> dict:
    return {
        "id": draft.id,
        "document_id": draft.document_id,
        "vehicle_id": draft.vehicle_id,
        "extracted_text": draft.extracted_text,
        "proposed_fields": json.loads(draft.proposed_fields_json),
        "confidence": json.loads(draft.confidence_json),
        "parser_name": draft.parser_name,
        "parser_version": draft.parser_version,
        "status": draft.status,
        "created_at": draft.created_at.isoformat(),
        "updated_at": draft.updated_at.isoformat(),
    }


@router.patch("/api/documents/{document_id}/draft/review")
def update_document_draft_review(
    document_id: str,
    payload: dict = Body(...),
    user: User = Depends(mutation_guard),
    session: Session = Depends(db),
):
    """Persist owner corrections without confirming or mutating history."""

    document = _owned_document(session, user, document_id)
    draft = _owned_draft(session, user, document.id)
    if document.status != "needs_review" or draft.status != "needs_review":
        raise HTTPException(409, "Draft is not available for owner review")

    extracted_text = payload.get("extracted_text", draft.extracted_text)
    if not isinstance(extracted_text, str):
        raise HTTPException(422, "extracted_text must be a string")

    proposed_fields = _object_field(payload, "proposed_fields", draft.proposed_fields_json)
    confidence = _object_field(payload, "confidence", draft.confidence_json)
    _validate_confidence(confidence)

    timestamp = datetime.now(timezone.utc)
    draft.extracted_text = extracted_text
    draft.proposed_fields_json = json.dumps(proposed_fields, ensure_ascii=False, sort_keys=True)
    draft.confidence_json = json.dumps(confidence, ensure_ascii=False, sort_keys=True)
    draft.updated_at = timestamp
    document.updated_at = timestamp
    session.commit()
    session.refresh(draft)
    return _serialize(draft)
