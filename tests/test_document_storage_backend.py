from pathlib import Path

import pytest

from app import document_storage


def test_default_backend_is_local(tmp_path, monkeypatch):
    monkeypatch.delenv("STORAGE_BACKEND", raising=False)
    monkeypatch.setattr(document_storage, "STORAGE_ROOT", tmp_path)

    backend = document_storage.get_document_storage()

    assert isinstance(backend, document_storage.LocalDocumentStorage)
    assert isinstance(backend, document_storage.DocumentStorageBackend)
    assert backend.root == tmp_path.resolve()


def test_explicit_local_backend_preserves_compatibility_functions(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setattr(document_storage, "STORAGE_ROOT", tmp_path)

    destination = document_storage.write_document_atomic(
        "document_inbox/source.pdf", b"%PDF-1.7\nprivate document"
    )

    assert destination == (tmp_path / "document_inbox" / "source.pdf").resolve()
    assert document_storage.resolve_storage_key("document_inbox/source.pdf") == destination
    document_storage.delete_document("document_inbox/source.pdf")
    assert not destination.exists()


def test_s3_backend_requires_explicit_bucket(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.delenv("S3_BUCKET", raising=False)

    with pytest.raises(document_storage.DocumentStorageError, match="S3_BUCKET is required"):
        document_storage.get_document_storage()


def test_unsupported_backend_fails_fast(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "azure")

    with pytest.raises(document_storage.DocumentStorageError, match="Unsupported STORAGE_BACKEND: azure"):
        document_storage.get_document_storage()


def test_empty_backend_value_is_rejected(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "   ")

    with pytest.raises(document_storage.DocumentStorageError, match="<empty>"):
        document_storage.get_document_storage()


def test_http_boundaries_remain_backend_agnostic():
    inbox_source = Path("app/document_inbox_api.py").read_text(encoding="utf-8")
    file_source = Path("app/document_file_api.py").read_text(encoding="utf-8")

    assert "LocalDocumentStorage" not in inbox_source
    assert "LocalDocumentStorage" not in file_source
    assert "STORAGE_BACKEND" not in inbox_source
    assert "STORAGE_BACKEND" not in file_source
