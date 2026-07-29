from pathlib import Path

import pytest

from app import document_storage


def test_resolve_storage_key_stays_inside_root(tmp_path, monkeypatch):
    monkeypatch.setattr(document_storage, "STORAGE_ROOT", tmp_path.resolve())

    resolved = document_storage.resolve_storage_key("document_inbox/receipt.pdf")

    assert resolved == (tmp_path / "document_inbox" / "receipt.pdf").resolve()


def test_resolve_storage_key_rejects_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(document_storage, "STORAGE_ROOT", tmp_path.resolve())

    with pytest.raises(document_storage.DocumentStorageError):
        document_storage.resolve_storage_key("../outside.pdf")


@pytest.mark.parametrize("storage_key", ["", "   ", None])
def test_resolve_storage_key_rejects_empty_values(tmp_path, monkeypatch, storage_key):
    monkeypatch.setattr(document_storage, "STORAGE_ROOT", tmp_path.resolve())

    with pytest.raises(document_storage.DocumentStorageError):
        document_storage.resolve_storage_key(storage_key)


def test_atomic_write_publishes_complete_file(tmp_path, monkeypatch):
    monkeypatch.setattr(document_storage, "STORAGE_ROOT", tmp_path.resolve())
    payload = b"%PDF-1.7\nprivate document"

    destination = document_storage.write_document_atomic("document_inbox/source.pdf", payload)

    assert destination.read_bytes() == payload
    assert list(destination.parent.glob("*.upload")) == []
    assert list(destination.parent.glob(".*.upload")) == []


def test_delete_document_uses_validated_key(tmp_path, monkeypatch):
    monkeypatch.setattr(document_storage, "STORAGE_ROOT", tmp_path.resolve())
    stored = document_storage.write_document_atomic("document_inbox/source.png", b"png")

    document_storage.delete_document("document_inbox/source.png")

    assert not stored.exists()


def test_file_api_uses_shared_storage_boundary():
    source = Path("app/document_file_api.py").read_text(encoding="utf-8")

    assert "resolve_storage_key(document.stored_name)" in source
    assert "path.is_symlink()" in source
    assert "STORAGE_ROOT / document.stored_name" not in source
