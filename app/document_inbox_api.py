"""HTTP boundary for the vehicle Document Inbox.

Uploaded files pass the shared document-intake validator, are persisted under the
configured storage root and remain independent from service visits. No OCR and no
vehicle-history mutation happen in this module.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import os
import secrets

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from .document_intake import DocumentIntakeError, validate_document_intake
from .models import DocumentInboxDocument, User, Vehicle
from .security import current_user, db, mutation_guard


router = APIRouter(tags=["document-inbox"])
STORAGE_ROOT = Path(os.getenv("STORAGE_PATH", "./data/storage")).resolve()
INBOX_STORAGE = STORAGE_ROOT / "document_inbox"
INBOX_STORAGE.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))


def _owned_vehicle(session: Session, user: User, vehicle_id: str) -> Vehicle:
    vehicle = session.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(404, "Vehicle not found")
    if vehicle.owner_id != user.id:
        raise HTTPException(403, "Forbidden")
    return vehicle


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
    """List the current owner's inbox documents for one vehicle."""

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
    """Validate and persist one unprocessed vehicle document.

    The resulting record always starts in ``uploaded`` and is not linked to a
    service visit. A later owner-reviewed workflow is responsible for that link.
    """

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
    physical_path = STORAGE_ROOT / stored_name
    physical_path.parent.mkdir(parents=True, exist_ok=True)
    physical_path.write_bytes(data)

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
        physical_path.unlink(missing_ok=True)
        raise

    return _serialize_document(document)
