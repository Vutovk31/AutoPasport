"""Storage boundary for private Document Inbox files.

Application code uses the module-level compatibility functions below. They delegate to
an explicit backend selected with ``STORAGE_BACKEND`` so HTTP handlers remain
independent from the physical storage implementation.
"""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
import tempfile
from typing import Any, Protocol, runtime_checkable


STORAGE_ROOT = Path(os.getenv("STORAGE_PATH", "./data/storage")).resolve()
SUPPORTED_STORAGE_BACKENDS = {"local", "s3"}


class DocumentStorageError(RuntimeError):
    """Raised when a document cannot be addressed or persisted safely."""


def _validate_storage_key(storage_key: str) -> str:
    """Return a normalized relative object key or reject unsafe input."""

    if not isinstance(storage_key, str) or not storage_key.strip():
        raise DocumentStorageError("Document storage key is empty")

    normalized = storage_key.strip().replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise DocumentStorageError("Document storage key is unsafe")
    return str(path)


@runtime_checkable
class DocumentStorageBackend(Protocol):
    """Minimal contract required by upload and file-delivery boundaries."""

    def resolve(self, storage_key: str) -> Path:
        """Return a local readable path when the backend supports local paths."""

    def read(self, storage_key: str) -> bytes:
        """Return the complete private object for an authorized delivery boundary."""

    def write_atomic(self, storage_key: str, data: bytes) -> Path | str:
        """Persist a complete object and return its backend location."""

    def delete(self, storage_key: str) -> None:
        """Delete an object after validating its storage key."""


class LocalDocumentStorage:
    """Filesystem implementation rooted at a configured private directory."""

    def __init__(self, root: Path):
        self.root = root.resolve()

    def resolve(self, storage_key: str) -> Path:
        safe_key = _validate_storage_key(storage_key)
        candidate = (self.root / safe_key).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as error:
            raise DocumentStorageError("Document storage key escapes storage root") from error
        return candidate

    def read(self, storage_key: str) -> bytes:
        path = self.resolve(storage_key)
        if not path.is_file() or path.is_symlink():
            raise DocumentStorageError("Document file not found")
        try:
            return path.read_bytes()
        except OSError as error:
            raise DocumentStorageError("Unable to read document") from error

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


class S3DocumentStorage:
    """Private S3-compatible object storage implementation.

    The client is injectable so the adapter can be verified without network access.
    Objects remain private: no ACL or public URL is created by this boundary.
    """

    def __init__(self, client: Any, bucket: str, prefix: str = ""):
        if not bucket.strip():
            raise DocumentStorageError("S3 bucket is required")
        self.client = client
        self.bucket = bucket.strip()
        self.prefix = prefix.strip().strip("/")

    def _object_key(self, storage_key: str) -> str:
        safe_key = _validate_storage_key(storage_key)
        return f"{self.prefix}/{safe_key}" if self.prefix else safe_key

    def resolve(self, storage_key: str) -> Path:
        _validate_storage_key(storage_key)
        raise DocumentStorageError("S3 backend does not expose local file paths")

    def read(self, storage_key: str) -> bytes:
        key = self._object_key(storage_key)
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            body = response["Body"]
            content = body.read()
            if not isinstance(content, bytes):
                raise TypeError("S3 object body did not return bytes")
            return content
        except Exception as error:
            raise DocumentStorageError("Unable to read document") from error

    def write_atomic(self, storage_key: str, data: bytes) -> str:
        if not isinstance(data, bytes):
            raise DocumentStorageError("Document payload must be bytes")
        key = self._object_key(storage_key)
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType="application/octet-stream",
            )
            return key
        except Exception as error:
            raise DocumentStorageError("Unable to persist document") from error

    def delete(self, storage_key: str) -> None:
        key = self._object_key(storage_key)
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except Exception as error:
            raise DocumentStorageError("Unable to delete document") from error


def _build_s3_storage() -> S3DocumentStorage:
    bucket = os.getenv("S3_BUCKET", "").strip()
    if not bucket:
        raise DocumentStorageError("S3_BUCKET is required for STORAGE_BACKEND=s3")

    try:
        import boto3
    except ImportError as error:
        raise DocumentStorageError("boto3 is required for STORAGE_BACKEND=s3") from error

    client_kwargs: dict[str, str] = {}
    endpoint_url = os.getenv("S3_ENDPOINT_URL", "").strip()
    region_name = os.getenv("S3_REGION", "").strip()
    if endpoint_url:
        client_kwargs["endpoint_url"] = endpoint_url
    if region_name:
        client_kwargs["region_name"] = region_name

    return S3DocumentStorage(
        client=boto3.client("s3", **client_kwargs),
        bucket=bucket,
        prefix=os.getenv("S3_PREFIX", "").strip(),
    )


def get_document_storage() -> DocumentStorageBackend:
    """Build the configured backend and fail fast for unsupported values."""

    backend_name = os.getenv("STORAGE_BACKEND", "local").strip().lower()
    if backend_name == "local":
        return LocalDocumentStorage(STORAGE_ROOT)
    if backend_name == "s3":
        return _build_s3_storage()
    raise DocumentStorageError(
        f"Unsupported STORAGE_BACKEND: {backend_name or '<empty>'}. "
        f"Supported backends: {', '.join(sorted(SUPPORTED_STORAGE_BACKENDS))}"
    )


def resolve_storage_key(storage_key: str) -> Path:
    """Compatibility boundary retained for local storage maintenance and tests."""

    return get_document_storage().resolve(storage_key)


def read_document(storage_key: str) -> bytes:
    """Backend-neutral boundary used by owner-only file delivery."""

    return get_document_storage().read(storage_key)


def write_document_atomic(storage_key: str, data: bytes) -> Path | str:
    """Backend-neutral boundary used by document upload."""

    return get_document_storage().write_atomic(storage_key, data)


def delete_document(storage_key: str) -> None:
    """Backend-neutral boundary used by rollback cleanup."""

    get_document_storage().delete(storage_key)
