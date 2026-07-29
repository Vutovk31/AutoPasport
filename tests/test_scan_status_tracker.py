from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRACKER = ROOT / "app" / "static" / "scan-status-tracker.js"
RECEIPT = ROOT / "app" / "static" / "scan-upload-receipt.js"
ENTRYPOINT = ROOT / "app" / "static" / "document-review-links.js"


def test_status_tracker_is_loaded_by_mobile_document_entrypoint():
    source = ENTRYPOINT.read_text(encoding="utf-8")
    assert "import './scan-status-tracker.js';" in source


def test_upload_receipt_dispatches_real_document_record():
    source = RECEIPT.read_text(encoding="utf-8")
    assert "autopassport:document-accepted" in source
    assert "detail: { document: documentRecord }" in source
    assert "dataset.documentId" in source
    assert "dataset.vehicleId" in source
    assert "scan-upload-receipt-status" in source


def test_tracker_polls_existing_vehicle_document_inbox_contract():
    source = TRACKER.read_text(encoding="utf-8")
    assert "/api/vehicles/${encodeURIComponent(vehicleId)}/documents" in source
    assert "credentials: 'same-origin'" in source
    assert "payload.documents.find" in source
    assert "String(item.id) === String(documentId)" in source


def test_tracker_has_bounded_polling_and_terminal_states():
    source = TRACKER.read_text(encoding="utf-8")
    assert "POLL_INTERVAL_MS = 3000" in source
    assert "MAX_ATTEMPTS = 20" in source
    assert "needs_review" in source
    assert "confirmed" in source
    assert "failed" in source
    assert "tracker.cancelled" in source


def test_tracker_adds_review_action_only_for_needs_review():
    source = TRACKER.read_text(encoding="utf-8")
    assert "documentRecord.status === 'needs_review'" in source
    assert "scan-upload-review" in source
    assert "/documents/${encodeURIComponent(documentRecord.id)}/review" in source
    assert "reviewLink?.remove()" in source


def test_tracker_does_not_contain_mock_document_data():
    source = TRACKER.read_text(encoding="utf-8").lower()
    assert "mock" not in source
    assert "demo" not in source
    assert "fixture" not in source
