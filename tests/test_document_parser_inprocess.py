from __future__ import annotations

from threading import Event

import pytest

from app.document_parser_inprocess import InProcessDocumentParserDispatcher


def test_dispatcher_delivers_real_document_id() -> None:
    delivered: list[str] = []
    handled = Event()

    def worker(document_id: str) -> None:
        delivered.append(document_id)
        handled.set()

    dispatcher = InProcessDocumentParserDispatcher(worker, max_queue_size=2)
    try:
        assert dispatcher.enqueue(document_id="  doc-123  ") is True
        assert handled.wait(timeout=1.0) is True
        assert delivered == ["doc-123"]
    finally:
        dispatcher.shutdown()


def test_dispatcher_rejects_new_jobs_after_shutdown() -> None:
    dispatcher = InProcessDocumentParserDispatcher(lambda document_id: None)
    dispatcher.shutdown()

    assert dispatcher.enqueue(document_id="doc-123") is False
    assert dispatcher.is_alive is False


def test_worker_failure_does_not_stop_following_jobs() -> None:
    delivered: list[str] = []
    second_handled = Event()

    def worker(document_id: str) -> None:
        if document_id == "bad":
            raise RuntimeError("provider unavailable")
        delivered.append(document_id)
        second_handled.set()

    dispatcher = InProcessDocumentParserDispatcher(worker, max_queue_size=2)
    try:
        assert dispatcher.enqueue(document_id="bad") is True
        assert dispatcher.enqueue(document_id="good") is True
        assert second_handled.wait(timeout=1.0) is True
        assert delivered == ["good"]
    finally:
        dispatcher.shutdown()


@pytest.mark.parametrize("value", [0, 1001, -1])
def test_queue_size_is_bounded(value: int) -> None:
    with pytest.raises(ValueError):
        InProcessDocumentParserDispatcher(lambda document_id: None, max_queue_size=value)


def test_document_id_is_required() -> None:
    dispatcher = InProcessDocumentParserDispatcher(lambda document_id: None)
    try:
        with pytest.raises(ValueError):
            dispatcher.enqueue(document_id="  ")
    finally:
        dispatcher.shutdown()


def test_negative_shutdown_timeout_is_rejected() -> None:
    dispatcher = InProcessDocumentParserDispatcher(lambda document_id: None)
    try:
        with pytest.raises(ValueError):
            dispatcher.shutdown(timeout=-1)
    finally:
        dispatcher.shutdown()
