"""Filesystem boundary for private Document Inbox files.

The current backend is local filesystem storage. All callers must use this module
instead of joining untrusted database values to STORAGE_PATH directly. The API is
small enough to replace with an object-storage adapter in a later increment.
"""

from __future__ import annotations

import os
from pathlib import Path
import tempfile


STORAGE_ROOT = Path(os.getenv("STORAGE_PATH", "./data/storage")).resolve()


class DocumentStorageError(RuntimeError):
    """Raised when a document storage key is unsafe or cannot be persisted."""


def resolve_storage_key(storage_key: str) -> Path:
    """Resolve a relative storage key without allowing traversal or symlinks."""

    if not isinstance(storage_key, str) or not storage_key.strip():
        raise DocumentStorageError("Document storage key is empty")

    candidate = (STORAGE_ROOT / storage_key).resolve()
    try:
        candidate.relative_to(STORAGE_ROOT)
    except ValueError as error:
        raise DocumentStorageError("Document storage key escapes storage root") from error

    return candidate


def write_document_atomic(storage_key: str, data: bytes) -> Path:
    """Persist bytes atomically so readers never observe a partial upload."""

    destination = resolve_storage_key(storage_key)
    destination.parent.mkdir(parents=True, exist_ok=True)

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".upload",
            delete=False,
        ) as temporary:
            temporary.write(data)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)

        temporary_path.replace(destination)
        return destination
    except OSError as error:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise DocumentStorageError("Unable to persist document") from error


def delete_document(storage_key: str) -> None:
    """Delete a stored object after validating its key."""

    resolve_storage_key(storage_key).unlink(missing_ok=True)
