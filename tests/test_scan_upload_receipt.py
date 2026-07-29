from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "app" / "static" / "scan-upload-receipt.js"
REVIEW_LINKS = ROOT / "app" / "static" / "document-review-links.js"


def source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_receipt_module_is_loaded_by_mobile_document_shell():
    assert "import './scan-upload-receipt.js';" in source(REVIEW_LINKS)


def test_successful_document_post_renders_real_server_record():
    script = source(RECEIPT)
    assert "response.clone().json().then(renderAcceptedDocument)" in script
    assert "documentRecord?.id" in script
    assert "documentRecord.original_name" in script
    assert "encodeURIComponent(documentRecord.id)" in script


def test_receipt_offers_original_and_review_only_when_allowed():
    script = source(RECEIPT)
    assert "'application/pdf', 'image/jpeg', 'image/png'" in script
    assert "VIEWABLE_MEDIA_TYPES.has(documentRecord.media_type)" in script
    assert "documentRecord.status === REVIEW_STATUS" in script
    assert "Открыть оригинал" in script
    assert "Проверить данные" in script


def test_receipt_does_not_inject_server_text_as_html():
    script = source(RECEIPT)
    assert "name.textContent = documentRecord.original_name" in script
    assert "innerHTML" not in script


def test_original_opens_safely_and_inbox_can_be_refreshed():
    script = source(RECEIPT)
    assert "link.target = '_blank'" in script
    assert "link.rel = 'noopener'" in script
    assert "document.querySelector('#refreshDocuments')?.click()" in script
    assert "scrollIntoView({ behavior: 'smooth', block: 'start' })" in script


def test_receipt_reacts_only_to_successful_document_uploads():
    script = source(RECEIPT)
    assert "response.ok && method === 'POST'" in script
    assert "/\\/api\\/vehicles\\/[^/]+\\/documents$/" in script
    lowered = script.lower()
    assert "mock" not in lowered
    assert "fixture" not in lowered
    assert "demo document" not in lowered
