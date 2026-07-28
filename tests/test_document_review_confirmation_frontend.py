from pathlib import Path


REVIEW_PAGE = Path("app/document_review_page.py")


def source() -> str:
    return REVIEW_PAGE.read_text(encoding="utf-8")


def test_review_screen_has_explicit_confirmation_action():
    page = source()

    assert "Подтвердить и добавить в историю" in page
    assert "Подтверждение создаст запись в истории" in page
    assert "window.confirm(" in page
    assert "/api/documents/${documentId}/draft/confirm" in page
    assert "method:'POST'" in page


def test_confirmation_saves_current_corrections_before_creating_visit():
    page = source()
    handler = page.split("confirmButton.addEventListener", 1)[1]

    assert handler.index("await saveDraft()") < handler.index("draft/confirm")
    assert "X-CSRF-Token" in page
    assert "credentials:'same-origin'" in page


def test_confirmation_blocks_repeat_action_and_reports_created_visit():
    page = source()

    assert "if (confirmed) return" in page
    assert "confirmed = true" in page
    assert "confirmButton.disabled = true" in page
    assert "Добавлено в историю" in page
    assert "result.visit_id" in page
    assert "'/#history'" in page


def test_review_screen_does_not_fabricate_parser_results():
    page = source()

    assert "request(`/api/documents/${documentId}/draft`)" in page
    assert "data.proposed_fields" in page
    assert "data.confidence" in page
    assert "Math.random" not in page
    assert "fixture" not in page.lower()


def test_rendered_item_values_are_escaped():
    page = source()

    assert "function escapeHtml" in page
    assert "escapeHtml(item.title" in page
    assert "escapeHtml(item.brand" in page
    assert "escapeHtml(item.cost_rubles" in page
