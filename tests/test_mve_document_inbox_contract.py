"""Contract checks for the static Document Inbox MVE.

These tests intentionally verify frontend/backend coupling without changing backend models.
"""
from pathlib import Path

HTML = Path("app/static/mve/index.html").read_text(encoding="utf-8")


def test_document_inbox_uses_existing_list_contract():
    assert "/api/vehicles/${encodeURIComponent(vehicleId)}/documents" in HTML
    assert "data.documents" in HTML


def test_document_upload_uses_existing_multipart_contract():
    assert 'name="document_type"' in HTML
    assert 'name="file"' in HTML
    assert "new FormData(form)" in HTML
    assert "method:'POST'" in HTML


def test_ui_does_not_claim_visit_creation_or_ocr_completion():
    assert "Запись об обслуживании появится только после вашей проверки и подтверждения" in HTML
    assert "OCR завершён" not in HTML
    assert "визит создан автоматически" not in HTML


def test_mobile_and_accessibility_guards_are_present():
    assert "max-width:430px" in HTML
    assert "min-width:320px" in HTML
    assert 'aria-live="polite"' in HTML
    assert 'aria-modal="true"' in HTML
    assert 'role="status"' in HTML
