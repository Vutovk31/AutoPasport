from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCAN_REVIEW = ROOT / "app" / "static" / "scan-review.js"
REVIEW_LINKS = ROOT / "app" / "static" / "document-review-links.js"


def source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_scan_review_module_is_loaded_by_mobile_shell():
    assert "import './scan-review.js';" in source(REVIEW_LINKS)


def test_selected_file_is_staged_before_network_upload():
    script = source(SCAN_REVIEW)
    change_handler = script.index("document.addEventListener('change'")
    stage_call = script.index("stageFile(file);", change_handler)
    upload_function = script.index("async function uploadStagedFile()")

    assert stage_call > change_handler
    assert upload_function < change_handler
    assert "panel.hidden = false" in script
    assert "До подтверждения файл не отправляется" in script


def test_upload_requires_explicit_confirmation():
    script = source(SCAN_REVIEW)
    assert "id=\"confirmScanUpload\"" in script
    assert "addEventListener('click', uploadStagedFile)" in script
    assert "fetch(`/api/vehicles/${encodeURIComponent(vehicleId)}/documents`" in script


def test_user_can_cancel_without_uploading():
    script = source(SCAN_REVIEW)
    assert "id=\"cancelScanUpload\"" in script
    assert "addEventListener('click', resetStagedFile)" in script
    assert "URL.revokeObjectURL(previewUrl)" in script
    assert "input.value = ''" in script


def test_preview_supports_only_server_accepted_formats():
    script = source(SCAN_REVIEW)
    assert "'application/pdf', 'image/jpeg', 'image/png'" in script
    assert "Поддерживаются PDF, JPEG и PNG" in script
    assert "URL.createObjectURL(file)" in script
    assert "scan-pdf-preview" in script


def test_scan_upload_keeps_csrf_and_vehicle_ownership_context():
    script = source(SCAN_REVIEW)
    assert "selectedVehicleId()" in script
    assert "'X-CSRF-Token': csrfToken()" in script
    assert "credentials: 'same-origin'" in script
    assert "document.querySelector('#refreshDocuments')?.click()" in script


def test_no_demo_document_or_vehicle_is_added():
    script = source(SCAN_REVIEW).lower()
    assert "mock" not in script
    assert "fixture" not in script
    assert "demo document" not in script
