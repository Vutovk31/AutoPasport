from datetime import datetime, timezone

import pytest

from app.document_inbox import (
    ARCHIVED,
    CONFIRMED,
    FAILED,
    NEEDS_REVIEW,
    PROCESSING,
    UPLOADED,
    DocumentInboxError,
    DocumentInboxItem,
    transition_document,
)


SHA256 = "a" * 64


def inbox_item(**overrides):
    values = {
        "id": "doc-1",
        "owner_id": "owner-1",
        "vehicle_id": "vehicle-1",
        "document_type": "work_order",
        "original_name": "order.pdf",
        "stored_name": "stored-order.pdf",
        "media_type": "application/pdf",
        "size_bytes": 128,
        "sha256": SHA256,
        "status": UPLOADED,
    }
    values.update(overrides)
    return DocumentInboxItem(**values)


def test_document_starts_uploaded_without_history_link():
    item = inbox_item()

    assert item.status == UPLOADED
    assert item.linked_visit_id is None
    assert item.failure_reason is None


def test_happy_path_requires_review_before_owner_confirmation():
    started = inbox_item()
    processing = transition_document(started, PROCESSING)
    review = transition_document(processing, NEEDS_REVIEW)
    confirmed = transition_document(review, CONFIRMED, linked_visit_id="visit-1")

    assert processing.status == PROCESSING
    assert review.status == NEEDS_REVIEW
    assert confirmed.status == CONFIRMED
    assert confirmed.linked_visit_id == "visit-1"
    assert started.status == UPLOADED


def test_document_cannot_be_confirmed_directly_from_uploaded():
    with pytest.raises(DocumentInboxError, match="not allowed"):
        transition_document(inbox_item(), CONFIRMED, linked_visit_id="visit-1")


def test_confirmation_requires_explicit_visit_link():
    review = inbox_item(status=NEEDS_REVIEW)

    with pytest.raises(DocumentInboxError, match="requires a linked visit"):
        transition_document(review, CONFIRMED)


def test_processing_failure_records_reason_and_can_be_retried():
    processing = inbox_item(status=PROCESSING)
    failed = transition_document(
        processing,
        FAILED,
        failure_reason="Text extraction timed out",
    )
    retried = transition_document(failed, PROCESSING)

    assert failed.status == FAILED
    assert failed.failure_reason == "Text extraction timed out"
    assert retried.status == PROCESSING
    assert retried.failure_reason is None


def test_failed_transition_requires_reason():
    with pytest.raises(DocumentInboxError, match="requires a failure reason"):
        transition_document(inbox_item(status=PROCESSING), FAILED)


def test_archived_document_is_terminal():
    archived = transition_document(inbox_item(), ARCHIVED)

    with pytest.raises(DocumentInboxError, match="not allowed"):
        transition_document(archived, PROCESSING)


def test_visit_link_is_rejected_before_confirmation():
    with pytest.raises(DocumentInboxError, match="only after owner confirmation"):
        inbox_item(linked_visit_id="visit-1")


def test_failed_item_requires_failure_reason_at_construction():
    with pytest.raises(DocumentInboxError, match="requires a failure reason"):
        inbox_item(status=FAILED)


def test_sha256_must_be_valid_hex_digest():
    with pytest.raises(DocumentInboxError, match="hexadecimal"):
        inbox_item(sha256="z" * 64)


def test_transition_records_supplied_timestamp():
    timestamp = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)
    processing = transition_document(inbox_item(), PROCESSING, changed_at=timestamp)

    assert processing.updated_at == timestamp
