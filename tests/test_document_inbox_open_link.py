from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "app" / "static" / "document-review-links.js"


def test_inbox_exposes_owner_only_file_endpoint_for_supported_documents():
    script = SCRIPT.read_text(encoding="utf-8")

    assert "const OPEN_LABEL = 'Открыть документ'" in script
    assert "application/pdf" in script
    assert "image/jpeg" in script
    assert "image/png" in script
    assert "VIEWABLE_MEDIA_TYPES.has(inboxItem.media_type)" in script
    assert "/api/documents/${encodeURIComponent(inboxItem.id)}/file" in script


def test_open_link_uses_safe_new_tab_attributes_and_real_document_metadata():
    script = SCRIPT.read_text(encoding="utf-8")

    assert "openLink.target = '_blank'" in script
    assert "openLink.rel = 'noopener'" in script
    assert "inboxItem.original_name" in script
    assert "latestDocuments" in script
    assert "demo" not in script.lower()
    assert "mock" not in script.lower()


def test_open_action_does_not_confirm_or_create_history():
    script = SCRIPT.read_text(encoding="utf-8")

    assert "/draft/confirm" not in script
    assert "POST" not in script
    assert "/visits" not in script
    assert "/events" not in script
