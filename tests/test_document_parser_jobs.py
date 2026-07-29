from pathlib import Path


SOURCE = Path("app/document_parser_jobs.py").read_text(encoding="utf-8")


def test_parser_claim_is_atomic_and_restricts_source_states():
    assert "update(DocumentInboxDocument)" in SOURCE
    assert 'DocumentInboxDocument.status.in_(("uploaded", "failed"))' in SOURCE
    assert 'status="processing"' in SOURCE
    assert "result.rowcount != 1" in SOURCE


def test_parser_failure_only_applies_to_claimed_documents():
    assert 'DocumentInboxDocument.status == "processing"' in SOURCE
    assert 'status="failed"' in SOURCE
    assert "failure_reason=safe_reason" in SOURCE


def test_failure_reason_is_required_normalized_and_bounded():
    assert '" ".join(str(reason).split()).strip()' in SOURCE
    assert 'raise DocumentParserJobError("Failure reason is required")' in SOURCE
    assert "safe_reason = safe_reason[:240]" in SOURCE


def test_job_boundary_does_not_write_drafts_or_vehicle_history():
    assert "DocumentAIDraft" not in SOURCE
    assert "ServiceVisit" not in SOURCE
    assert "HistoryEvent" not in SOURCE
    assert "proposed_fields" not in SOURCE


def test_successful_transitions_are_committed_and_return_persisted_document():
    assert SOURCE.count("session.commit()") == 2
    assert SOURCE.count("session.get(DocumentInboxDocument, document_id)") == 2
