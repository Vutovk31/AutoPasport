"""HTTP boundary for the vehicle Document Inbox.

Uploaded files pass the shared document-intake validator, are persisted under the
configured storage root and remain independent from service visits. Parser results
are stored only as owner-reviewable drafts. No endpoint in this module mutates
vehicle history.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import secrets

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from .document_intake import DocumentIntakeError, validate_document_intake
from .document_storage import delete_document, write_document_atomic
from .models import DocumentAIDraft, DocumentInboxDocument, User, Vehicle
from .security import current_user, db, mutation_guard


router = APIRouter(tags=["document-inbox"])
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))


def _owned_vehicle(session: Session, user: User, vehicle_id: str) -> Vehicle:
    vehicle = session.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(404, "Vehicle not found")
    if vehicle.owner_id != user.id:
        raise HTTPException(403, "Forbidden")
    return vehicle


def _owned_document(session: Session, user: User, document_id: str) -> DocumentInboxDocument:
    document = session.get(DocumentInboxDocument, document_id)
    if document is None:
        raise HTTPException(404, "Document not found")
    if document.owner_id != user.id:
        raise HTTPException(403, "Forbidden")
    return document


def _serialize_document(document: DocumentInboxDocument) -> dict:
    return {
        "id": document.id,
        "vehicle_id": document.vehicle_id,
        "linked_visit_id": document.linked_visit_id,
        "document_type": document.document_type,
        "original_name": document.original_name,
        "media_type": document.media_type,
        "size_bytes": document.size_bytes,
        "sha256": document.sha256,
        "status": document.status,
        "failure_reason": document.failure_reason,
        "created_at": document.created_at.isoformat(),
        "updated_at": document.updated_at.isoformat(),
    }


def _serialize_draft(draft: DocumentAIDraft) -> dict:
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


def _json_object(payload: dict, field: str) -> dict:
    value = payload.get(field, {})
    if not isinstance(value, dict):
        raise HTTPException(422, f"{field} must be an object")
    return value


def _validate_confidence(confidence: dict) -> None:
    for field, value in confidence.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise HTTPException(422, f"Confidence for {field} must be a number")
        if not 0 <= float(value) <= 1:
            raise HTTPException(422, f"Confidence for {field} must be between 0 and 1")


def _intake_http_error(error: DocumentIntakeError) -> HTTPException:
    message = str(error)
    if message == "Document exceeds upload limit":
        return HTTPException(413, message)
    if message in {
        "Unsupported media type",
        "Document content does not match media type",
    }:
        return HTTPException(415, message)
    return HTTPException(422, message)


@router.get("/api/vehicles/{vehicle_id}/documents")
def list_vehicle_documents(
    vehicle_id: str,
    user: User = Depends(current_user),
    session: Session = Depends(db),
):
    vehicle = _owned_vehicle(session, user, vehicle_id)
    rows = session.scalars(
        select(DocumentInboxDocument)
        .where(
            DocumentInboxDocument.owner_id == user.id,
            DocumentInboxDocument.vehicle_id == vehicle.id,
        )
        .order_by(DocumentInboxDocument.created_at.desc())
    )
    return {"documents": [_serialize_document(row) for row in rows]}


@router.post("/api/vehicles/{vehicle_id}/documents", status_code=201)
async def upload_vehicle_document(
    vehicle_id: str,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(mutation_guard),
    session: Session = Depends(db),
):
    vehicle = _owned_vehicle(session, user, vehicle_id)
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    try:
        validated = validate_document_intake(
            document_type=document_type,
            filename=file.filename,
            media_type=file.content_type,
            data=data,
            max_upload_bytes=MAX_UPLOAD_BYTES,
        )
    except DocumentIntakeError as error:
        raise _intake_http_error(error) from error

    stored_name = f"document_inbox/{secrets.token_urlsafe(18)}{validated.suffix}"
    write_document_atomic(stored_name, data)

    timestamp = datetime.now(timezone.utc)
    document = DocumentInboxDocument(
        owner_id=user.id,
        vehicle_id=vehicle.id,
        linked_visit_id=None,
        document_type=validated.document_type,
        original_name=validated.original_name,
        stored_name=stored_name,
        media_type=validated.media_type,
        size_bytes=validated.size_bytes,
        sha256=validated.sha256,
        status="uploaded",
        failure_reason=None,
        created_at=timestamp,
        updated_at=timestamp,
    )

    try:
        session.add(document)
        session.commit()
        session.refresh(document)
    except Exception:
        session.rollback()
        delete_document(stored_name)
        raise

    return _serialize_document(document)


@router.get("/api/documents/{document_id}/draft")
def get_document_draft(
    document_id: str,
    user: User = Depends(current_user),
    session: Session = Depends(db),
):
    document = _owned_document(session, user, document_id)
    draft = session.scalar(
        select(DocumentAIDraft).where(
            DocumentAIDraft.document_id == document.id,
            DocumentAIDraft.owner_id == user.id,
        )
    )
    if draft is None:
        raise HTTPException(404, "Draft not found")
    return _serialize_draft(draft)


@router.post("/api/documents/{document_id}/draft", status_code=201)
def create_document_draft(
    document_id: str,
    payload: dict = Body(...),
    user: User = Depends(mutation_guard),
    session: Session = Depends(db),
):
    """Persist parser output as a reviewable draft without changing history."""

    document = _owned_document(session, user, document_id)
    if document.status not in {"uploaded", "processing", "failed"}:
        raise HTTPException(409, "Document is not ready for draft creation")
    existing = session.scalar(select(DocumentAIDraft).where(DocumentAIDraft.document_id == document.id))
    if existing is not None:
        raise HTTPException(409, "Document draft already exists")

    extracted_text = payload.get("extracted_text", "")
    parser_name = str(payload.get("parser_name", "")).strip()
    parser_version = str(payload.get("parser_version", "")).strip()
    if not isinstance(extracted_text, str):
        raise HTTPException(422, "extracted_text must be a string")
    if not parser_name or not parser_version:
        raise HTTPException(422, "parser_name and parser_version are required")

    proposed_fields = _json_object(payload, "proposed_fields")
    confidence = _json_object(payload, "confidence")
    _validate_confidence(confidence)
    timestamp = datetime.now(timezone.utc)
    draft = DocumentAIDraft(
        document_id=document.id,
        owner_id=user.id,
        vehicle_id=document.vehicle_id,
        extracted_text=extracted_text,
        proposed_fields_json=json.dumps(proposed_fields, ensure_ascii=False, sort_keys=True),
        confidence_json=json.dumps(confidence, ensure_ascii=False, sort_keys=True),
        parser_name=parser_name[:80],
        parser_version=parser_version[:40],
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
    return _serialize_draft(draft)
