"""Operational readiness probe for the configured document storage backend."""

from __future__ import annotations

import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from .document_storage import (
    DocumentStorageError,
    LocalDocumentStorage,
    S3DocumentStorage,
    get_document_storage,
)

router = APIRouter()


def probe_document_storage() -> dict[str, str]:
    """Verify that the selected backend is reachable without creating user data."""

    backend_name = os.getenv("STORAGE_BACKEND", "local").strip().lower()
    backend = get_document_storage()

    try:
        if isinstance(backend, LocalDocumentStorage):
            backend.root.mkdir(parents=True, exist_ok=True)
            if not backend.root.is_dir():
                raise DocumentStorageError("Local storage root is not a directory")
            if not os.access(backend.root, os.R_OK | os.W_OK | os.X_OK):
                raise DocumentStorageError("Local storage root is not readable and writable")
        elif isinstance(backend, S3DocumentStorage):
            backend.client.head_bucket(Bucket=backend.bucket)
        else:
            raise DocumentStorageError("Unknown document storage backend instance")
    except DocumentStorageError:
        raise
    except Exception as error:
        raise DocumentStorageError("Document storage readiness probe failed") from error

    return {"status": "ok", "backend": backend_name}


@router.get("/health/storage", tags=["operations"])
def document_storage_health():
    try:
        return probe_document_storage()
    except DocumentStorageError as error:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "backend": os.getenv("STORAGE_BACKEND", "local").strip().lower(),
                "detail": str(error),
            },
        )
