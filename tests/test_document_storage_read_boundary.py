from pathlib import Path

import pytest

from app import document_storage


def test_local_backend_reads_complete_document(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setattr(document_storage, "STORAGE_ROOT", tmp_path)
    payload = b"%PDF-1.7\nprivate document"

    document_storage.write_document_atomic("document_inbox/source.pdf", payload)

    assert document_storage.read_document("document_inbox/source.pdf") == payload


def test_local_backend_rejects_missing_document(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setattr(document_storage, "STORAGE_ROOT", tmp_path)

    with pytest.raises(document_storage.DocumentStorageError, match="not found"):
        document_storage.read_document("document_inbox/missing.pdf")


def test_local_backend_rejects_symlink(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setattr(document_storage, "STORAGE_ROOT", tmp_path)
    outside = tmp_path.parent / "outside-document.pdf"
    outside.write_bytes(b"private")
    link = tmp_path / "document_inbox" / "link.pdf"
    link.parent.mkdir(parents=True)
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are unavailable in this environment")

    with pytest.raises(document_storage.DocumentStorageError, match="not found"):
        document_storage.read_document("document_inbox/link.pdf")


def test_file_api_uses_backend_neutral_read_boundary():
    source = Path("app/document_file_api.py").read_text(encoding="utf-8")

    assert "read_document" in source
    assert "resolve_storage_key" not in source
    assert "FileResponse" not in source
    assert ".is_file()" not in source
    assert ".is_symlink()" not in source
    assert "Response(" in source
