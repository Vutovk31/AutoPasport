"""Owner-only delivery of files stored in the Document Inbox."""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .document_storage import DocumentStorageError, resolve_storage_key
from .models import DocumentInboxDocument, User
from .security import current_user, db


router = APIRouter(tags=["document-files"])
ALLOWED_INLINE_MEDIA_TYPES = {"application/pdf", "image/jpeg", "image/png"}


def _owned_document(session: Session, user: User, document_id: str) -> DocumentInboxDocument:
    document = session.get(DocumentInboxDocument, document_id)
    if document is None:
        raise HTTPException(404, "Document not found")
    if document.owner_id != user.id:
        raise HTTPException(403, "Forbidden")
    return document


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

    try:
        path = resolve_storage_key(document.stored_name)
    except DocumentStorageError as error:
        raise HTTPException(404, "Document file not found") from error

    if not path.is_file() or path.is_symlink():
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
