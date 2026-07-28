from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "app" / "static" / "index.html"
SCRIPT = ROOT / "app" / "static" / "document-review-links.js"


def test_review_link_script_loads_before_main_app():
    html = INDEX.read_text(encoding="utf-8")
    review_script = '<script type="module" src="/static/document-review-links.js"></script>'
    main_script = '<script type="module" src="/static/main.js"></script>'

    assert review_script in html
    assert html.index(review_script) < html.index(main_script)


def test_only_needs_review_documents_receive_review_link():
    script = SCRIPT.read_text(encoding="utf-8")

    assert "const REVIEW_STATUS = 'needs_review'" in script
    assert "inboxItem.status !== REVIEW_STATUS" in script
    assert "Проверить данные" in script
    assert "/documents/${encodeURIComponent(inboxItem.id)}/review" in script


def test_review_link_uses_real_inbox_api_response_and_no_confirmation():
    script = SCRIPT.read_text(encoding="utf-8")

    assert "response.clone().json()" in script
    assert "api\\/vehicles\\/" in script
    assert "latestDocuments" in script
    assert "/confirm" not in script
    assert "/visits" not in script
    assert "/events" not in script
