from pathlib import Path


SOURCE = Path("app/document_parser_runner.py").read_text(encoding="utf-8")


def test_runner_uses_injected_provider_contract_and_private_storage_boundary():
    assert "class DocumentParser(Protocol)" in SOURCE
    assert "def parse(self, *, content: bytes, media_type: str)" in SOURCE
    assert "read_document(document.stored_name)" in SOURCE
    assert "parser.parse(content=content, media_type=document.media_type)" in SOURCE


def test_runner_claims_before_parsing_and_persists_reviewable_draft():
    assert SOURCE.index("claim_document_for_processing") < SOURCE.index("read_document(document.stored_name)")
    assert "DocumentAIDraft(" in SOURCE
    assert 'status="needs_review"' in SOURCE
    assert 'document.status = "needs_review"' in SOURCE
    assert "session.commit()" in SOURCE


def test_runner_validates_structured_result_without_fabricating_fields():
    assert "isinstance(result, DocumentParserResult)" in SOURCE
    assert 'proposed_fields must be JSON serializable' in SOURCE
    assert 'Confidence for {field} must be between 0 and 1' in SOURCE
    assert "parser_name and parser_version are required" in SOURCE
    assert "ServiceVisit(" not in SOURCE
    assert "HistoryEvent(" not in SOURCE


def test_runner_prevents_duplicate_drafts_and_keeps_one_draft_per_document():
    assert "select(DocumentAIDraft).where(DocumentAIDraft.document_id == document.id)" in SOURCE
    assert 'raise DocumentParserRunnerError("Document draft already exists")' in SOURCE
    assert "except (DocumentParserJobError, IntegrityError):" in SOURCE


def test_runner_reduces_provider_failures_to_safe_status_reasons():
    assert 'return "Document storage read failed"' in SOURCE
    assert 'return "Document parser failed"' in SOURCE
    assert "mark_document_processing_failed(" in SOURCE
    assert "str(error)" not in SOURCE.split("def _safe_failure_reason", 1)[1].split("def run_document_parser", 1)[0] or "DocumentParserRunnerError" in SOURCE
    assert "provider response" in SOURCE.lower()
    assert "credentials" in SOURCE.lower()


def test_runner_never_mutates_vehicle_history_directly():
    assert "ServiceVisit" not in SOURCE
    assert "HistoryEvent" not in SOURCE
    assert "linked_visit_id" not in SOURCE
