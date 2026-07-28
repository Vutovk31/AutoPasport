"""Owner-only delivery of files stored in the Document Inbox."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .models import DocumentInboxDocument, User
from .security import current_user, db


router = APIRouter(tags=["document-files"])
STORAGE_ROOT = Path(os.getenv("STORAGE_PATH", "./data/storage")).resolve()
ALLOWED_INLINE_MEDIA_TYPES = {"application/pdf", "image/jpeg", "image/png"}


def _owned_document(session: Session, user: User, document_id: str) -> DocumentInboxDocument:
    document = session.get(DocumentInboxDocument, document_id)
    if document is None:
        raise HTTPException(404, "Document not found")
    if document.owner_id != user.id:
        raise HTTPException(403, "Forbidden")
    return document


def _stored_path(stored_name: str) -> Path:
    candidate = (STORAGE_ROOT / stored_name).resolve()
    try:
        candidate.relative_to(STORAGE_ROOT)
    except ValueError as error:
        raise HTTPException(404, "Document file not found") from error
    return candidate


@router.get("/api/documents/{document_id}/file", response_class=FileResponse)
def open_document_file(
    document_id: str,
    user: User = Depends(current_user),
    session: Session = Depends(db),
):
    """Return an inbox PDF/JPEG/PNG inline only to its owning user."""

    document = _owned_document(session, user, document_id)
    if document.media_type not in ALLOWED_INLINE_MEDIA_TYPES:
        raise HTTPException(415, "Unsupported document media type")

    path = _stored_path(document.stored_name)
    if not path.is_file():
        raise HTTPException(404, "Document file not found")

    encoded_name = quote(document.original_name, safe="")
    return FileResponse(
        path=path,
        media_type=document.media_type,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{encoded_name}",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )
