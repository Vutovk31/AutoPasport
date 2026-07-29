from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_document_file_router_is_registered():
    main = _read("app/main.py")
    assert "document_file_api" in main
    assert "app.include_router(document_file_router)" in main


def test_document_file_endpoint_is_owner_only_and_inline():
    source = _read("app/document_file_api.py")
    assert '@router.get("/api/documents/{document_id}/file"' in source
    assert "document.owner_id != user.id" in source
    assert 'raise HTTPException(403, "Forbidden")' in source
    assert "ALLOWED_INLINE_MEDIA_TYPES" in source
    assert '"application/pdf"' in source
    assert '"image/jpeg"' in source
    assert '"image/png"' in source
    assert '"Content-Disposition": f"inline;' in source
    assert '"X-Content-Type-Options": "nosniff"' in source
    assert '"Cache-Control": "private, no-store"' in source


def test_document_file_delivery_uses_storage_boundary():
    source = _read("app/document_file_api.py")
    storage = _read("app/document_storage.py")

    assert "read_document(document.stored_name)" in source
    assert "resolve_storage_key" not in source
    assert "FileResponse" not in source
    assert "def read(self, storage_key: str) -> bytes:" in storage
    assert "if not path.is_file() or path.is_symlink():" in storage
    assert 'raise DocumentStorageError("Document file not found")' in storage


def test_confirmed_visit_links_real_document_id():
    source = _read("app/confirmed_visit_page.py")
    assert 'href="/api/documents/{document.id}/file"' in source
    assert "Открыть документ" in source
    assert 'target="_blank"' in source
    assert 'rel="noopener"' in source
    assert "example-document" not in source
