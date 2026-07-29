from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INBOX_API = ROOT / "app" / "document_inbox_api.py"


def _source() -> str:
    return INBOX_API.read_text(encoding="utf-8")


def test_upload_uses_shared_atomic_storage_boundary() -> None:
    source = _source()

    assert "from .document_storage import delete_document, write_document_atomic" in source
    assert "write_document_atomic(stored_name, data)" in source
    assert "delete_document(stored_name)" in source


def test_upload_does_not_write_or_delete_paths_directly() -> None:
    source = _source()

    assert ".write_bytes(" not in source
    assert ".unlink(" not in source
    assert "STORAGE_ROOT / stored_name" not in source


def test_document_inbox_api_remains_valid_python() -> None:
    ast.parse(_source(), filename=str(INBOX_API))
