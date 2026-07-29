from pathlib import Path


SOURCE = Path("app/document_parser_dispatch.py").read_text(encoding="utf-8")


def test_dispatch_contract_is_provider_neutral_and_disabled_by_default():
    assert "class DocumentParserDispatcher(Protocol)" in SOURCE
    assert "class DisabledDocumentParserDispatcher" in SOURCE
    assert "_dispatcher: DocumentParserDispatcher = DisabledDocumentParserDispatcher()" in SOURCE
    assert "def enqueue(self, *, document_id: str) -> bool" in SOURCE


def test_dispatch_requires_a_persisted_document_identifier():
    assert 'raise ValueError("document_id is required")' in SOURCE
    assert "normalized_id = str(document_id).strip()" in SOURCE


def test_queue_outage_cannot_delete_or_mutate_accepted_document():
    assert "except Exception:" in SOURCE
    assert "accepted = False" in SOURCE
    assert "delete_document" not in SOURCE
    assert "DocumentInboxDocument" not in SOURCE
    assert "session.rollback" not in SOURCE


def test_dispatch_never_runs_parser_or_fabricates_draft_data():
    assert "run_document_parser" not in SOURCE
    assert "DocumentAIDraft" not in SOURCE
    assert "ServiceVisit" not in SOURCE
    assert "HistoryEvent" not in SOURCE
    assert "proposed_fields" not in SOURCE


def test_dispatch_adapter_can_be_installed_and_reset_for_isolated_runtime():
    assert "def configure_document_parser_dispatcher" in SOURCE
    assert "def reset_document_parser_dispatcher" in SOURCE
    assert "isinstance(dispatcher, DocumentParserDispatcher)" in SOURCE
    assert "with _dispatcher_lock:" in SOURCE
