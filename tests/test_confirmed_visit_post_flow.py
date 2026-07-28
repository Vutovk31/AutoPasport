from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_confirmed_visit_page_is_owner_scoped_and_shows_source_document():
    source = (ROOT / "app" / "confirmed_visit_page.py").read_text(encoding="utf-8")
    compile(source, "confirmed_visit_page.py", "exec")

    assert '@router.get("/visits/{visit_id}/confirmed"' in source
    assert "vehicle.owner_id != user.id" in source
    assert "DocumentInboxDocument.linked_visit_id == visit.id" in source
    assert 'DocumentInboxDocument.status == "confirmed"' in source
    assert "Работы и детали" in source
    assert "Исходный документ" in source
    assert "document.original_name" in source
    assert "document.sha256[:12]" in source


def test_review_screen_opens_exact_created_visit_without_hash_dependency():
    source = (ROOT / "app" / "document_review_page.py").read_text(encoding="utf-8")
    compile(source, "document_review_page.py", "exec")

    assert "encodeURIComponent(result.visit_id)" in source
    assert "`/visits/${encodeURIComponent(result.visit_id)}/confirmed`" in source
    assert "Открыть созданный визит" in source
    assert "ID визита:" not in source
    assert "href = '/#history'" not in source


def test_confirmed_visit_router_is_registered():
    source = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    compile(source, "main.py", "exec")

    assert "confirmed_visit_page_router" in source
    assert "app.include_router(confirmed_visit_page_router)" in source
