from pathlib import Path

import pytest

from app.document_storage import DocumentStorageError, LocalDocumentStorage, S3DocumentStorage
from app.document_storage_health import document_storage_health, probe_document_storage


class FakeS3Client:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def head_bucket(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error


def test_local_storage_probe_creates_and_checks_root(monkeypatch, tmp_path: Path):
    backend = LocalDocumentStorage(tmp_path / "documents")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setattr("app.document_storage_health.get_document_storage", lambda: backend)

    result = probe_document_storage()

    assert result == {"status": "ok", "backend": "local"}
    assert backend.root.is_dir()


def test_s3_storage_probe_uses_head_bucket(monkeypatch):
    client = FakeS3Client()
    backend = S3DocumentStorage(client=client, bucket="private-documents", prefix="production")
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setattr("app.document_storage_health.get_document_storage", lambda: backend)

    assert probe_document_storage() == {"status": "ok", "backend": "s3"}
    assert client.calls == [{"Bucket": "private-documents"}]


def test_s3_storage_probe_converts_client_failure(monkeypatch):
    backend = S3DocumentStorage(
        client=FakeS3Client(error=RuntimeError("credentials rejected")),
        bucket="private-documents",
    )
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setattr("app.document_storage_health.get_document_storage", lambda: backend)

    with pytest.raises(DocumentStorageError, match="readiness probe failed"):
        probe_document_storage()


def test_health_endpoint_returns_503_without_credentials_detail(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setattr(
        "app.document_storage_health.probe_document_storage",
        lambda: (_ for _ in ()).throw(DocumentStorageError("Document storage readiness probe failed")),
    )

    response = document_storage_health()

    assert response.status_code == 503
    assert b"credentials rejected" not in response.body
    assert b'"backend":"s3"' in response.body


def test_main_registers_storage_health_router():
    source = Path("app/main.py").read_text(encoding="utf-8")

    assert "document_storage_health_router" in source
    assert "app.include_router(document_storage_health_router)" in source
