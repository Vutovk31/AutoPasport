from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_JS = ROOT / "app" / "static" / "main.js"


def test_scan_screen_uses_real_document_inbox_api():
    source = MAIN_JS.read_text(encoding="utf-8")

    assert "POST" in source
    assert "/api/vehicles/${vehicleId}/documents" in source
    assert "document_type" in source
    assert "body.append('file', file)" in source
    assert "refreshDocumentInbox" in source


def test_scan_screen_does_not_claim_ocr_or_automatic_history_mutation():
    source = MAIN_JS.read_text(encoding="utf-8")

    assert "Загружен, ожидает обработки" in source
    assert "загружен в архив" in source
    assert "автоматически распознан" not in source
    assert "автоматически сохранён в историю" not in source


def test_document_inbox_ui_escapes_server_values():
    source = MAIN_JS.read_text(encoding="utf-8")

    assert "escapeHtml(document.original_name)" in source
    assert "escapeHtml(DOCUMENT_STATUS_LABELS[document.status]" in source
    assert "escapeHtml(error.message)" in source
