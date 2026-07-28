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


def test_document_file_path_cannot_escape_storage_root():
    source = _read("app/document_file_api.py")
    assert "candidate = (STORAGE_ROOT / stored_name).resolve()" in source
    assert "candidate.relative_to(STORAGE_ROOT)" in source
    assert "if not path.is_file()" in source


def test_confirmed_visit_links_real_document_id():
    source = _read("app/confirmed_visit_page.py")
    assert 'href="/api/documents/{document.id}/file"' in source
    assert "Открыть документ" in source
    assert 'target="_blank"' in source
    assert 'rel="noopener"' in source
    assert "example-document" not in source
