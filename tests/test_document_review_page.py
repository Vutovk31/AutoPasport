from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "app" / "document_review_page.py"
MAIN = ROOT / "app" / "main.py"


def test_review_screen_is_registered_and_owner_only():
    page = PAGE.read_text(encoding="utf-8")
    main = MAIN.read_text(encoding="utf-8")

    assert '@router.get("/documents/{document_id}/review"' in page
    assert "user: User = Depends(current_user)" in page
    assert "if document.owner_id != user.id" in page
    assert "document_review_page_router" in main
    assert "app.include_router(document_review_page_router)" in main


def test_review_screen_loads_updates_and_confirms_existing_draft_api():
    page = PAGE.read_text(encoding="utf-8")

    assert "`/api/documents/${documentId}/draft`" in page
    assert "`/api/documents/${documentId}/draft/review`" in page
    assert "`/api/documents/${documentId}/draft/confirm`" in page
    assert "method:'PATCH'" in page
    assert "method:'POST'" in page
    assert "X-CSRF-Token" in page
    assert "proposed_fields" in page
    assert "extracted_text" in page


def test_review_screen_exposes_core_fields_and_confidence():
    page = PAGE.read_text(encoding="utf-8")

    for field in (
        "visit_date",
        "mileage",
        "service_name",
        "total_cost_rubles",
        "title",
    ):
        assert f'name="{field}"' in page
        assert f'data-confidence="{field}"' in page

    assert "confidenceLabel" in page
    assert "Math.round(value * 100)" in page
    assert "renderItems(fields.items)" in page


def test_review_screen_preserves_explicit_owner_confirmation_boundary():
    page = PAGE.read_text(encoding="utf-8")

    assert "До явного подтверждения история автомобиля не изменяется" in page
    assert "Подтверждение создаст запись в истории" in page
    assert "window.confirm(" in page
    assert "await saveDraft()" in page
    assert "if (confirmed) return" in page
    assert "confirmed = true" in page
    assert "encodeURIComponent(result.visit_id)" in page
    assert "service_visits" not in page
