from pathlib import Path


SOURCE = Path("app/document_inbox_api.py").read_text(encoding="utf-8")


def test_upload_dispatches_only_after_document_commit_and_refresh():
    commit_position = SOURCE.index("session.commit()")
    refresh_position = SOURCE.index("session.refresh(document)", commit_position)
    dispatch_position = SOURCE.index("dispatch_document_for_parsing(document.id)")

    assert commit_position < refresh_position < dispatch_position


def test_upload_dispatch_uses_real_persisted_document_identifier():
    assert "from .document_parser_dispatch import dispatch_document_for_parsing" in SOURCE
    assert "dispatch_document_for_parsing(document.id)" in SOURCE
    assert 'dispatch_document_for_parsing("' not in SOURCE


def test_queue_failure_does_not_enter_upload_rollback_boundary():
    rollback_boundary = SOURCE[
        SOURCE.index("try:\n        session.add(document)") : SOURCE.index(
            "dispatch_document_for_parsing(document.id)"
        )
    ]

    assert "session.rollback()" in rollback_boundary
    assert "delete_document(stored_name)" in rollback_boundary
    assert "dispatch_document_for_parsing" not in rollback_boundary


def test_upload_response_is_returned_after_best_effort_dispatch():
    dispatch_position = SOURCE.index("dispatch_document_for_parsing(document.id)")
    response_position = SOURCE.index("return _serialize_document(document)", dispatch_position)

    assert dispatch_position < response_position


def test_upload_integration_does_not_run_parser_or_fabricate_draft_data():
    upload_section = SOURCE[
        SOURCE.index("async def upload_vehicle_document(") : SOURCE.index(
            '@router.get("/api/documents/{document_id}/draft")'
        )
    ]

    assert "run_document_parser" not in upload_section
    assert "DocumentAIDraft(" not in upload_section
    assert "proposed_fields" not in upload_section
    assert "ServiceVisit" not in upload_section
    assert "HistoryEvent" not in upload_section
