"""Storage boundary for private Document Inbox files.

Application code uses the module-level compatibility functions below. They delegate to
an explicit backend selected with ``STORAGE_BACKEND`` so HTTP handlers remain
independent from the physical storage implementation.
"""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
from typing import Protocol, runtime_checkable


STORAGE_ROOT = Path(os.getenv("STORAGE_PATH", "./data/storage")).resolve()
SUPPORTED_STORAGE_BACKENDS = {"local"}


class DocumentStorageError(RuntimeError):
    """Raised when a document cannot be addressed or persisted safely."""


@runtime_checkable
class DocumentStorageBackend(Protocol):
    """Minimal contract required by upload and file-delivery boundaries."""

    def resolve(self, storage_key: str) -> Path:
        """Return a local readable path for a validated storage key."""

    def write_atomic(self, storage_key: str, data: bytes) -> Path:
        """Persist a complete object atomically and return its local path."""

    def delete(self, storage_key: str) -> None:
        """Delete an object after validating its storage key."""


class LocalDocumentStorage:
    """Filesystem implementation rooted at a configured private directory."""

    def __init__(self, root: Path):
        self.root = root.resolve()

    def resolve(self, storage_key: str) -> Path:
        if not isinstance(storage_key, str) or not storage_key.strip():
            raise DocumentStorageError("Document storage key is empty")

        candidate = (self.root / storage_key).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as error:
            raise DocumentStorageError("Document storage key escapes storage root") from error
        return candidate

    def write_atomic(self, storage_key: str, data: bytes) -> Path:
        destination = self.resolve(storage_key)
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

    def delete(self, storage_key: str) -> None:
        self.resolve(storage_key).unlink(missing_ok=True)


def get_document_storage() -> DocumentStorageBackend:
    """Build the configured backend and fail fast for unsupported values."""

    backend_name = os.getenv("STORAGE_BACKEND", "local").strip().lower()
    if backend_name == "local":
        return LocalDocumentStorage(STORAGE_ROOT)
    raise DocumentStorageError(
        f"Unsupported STORAGE_BACKEND: {backend_name or '<empty>'}. "
        f"Supported backends: {', '.join(sorted(SUPPORTED_STORAGE_BACKENDS))}"
    )


def resolve_storage_key(storage_key: str) -> Path:
    """Compatibility boundary used by file delivery."""

    return get_document_storage().resolve(storage_key)


def write_document_atomic(storage_key: str, data: bytes) -> Path:
    """Compatibility boundary used by document upload."""

    return get_document_storage().write_atomic(storage_key, data)


def delete_document(storage_key: str) -> None:
    """Compatibility boundary used by rollback cleanup."""

    get_document_storage().delete(storage_key)
