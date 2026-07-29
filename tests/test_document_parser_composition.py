from __future__ import annotations

from threading import Event

import pytest

from app import document_parser_composition as composition
from app.document_parser_runner import DocumentParserResult


class FakeSession:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeParser:
    def parse(self, *, content: bytes, media_type: str) -> DocumentParserResult:
        raise AssertionError("runner is patched in composition tests")


def test_disabled_is_safe_default(monkeypatch):
    reset_calls = []
    monkeypatch.setattr(composition, "reset_document_parser_dispatcher", lambda: reset_calls.append(True))

    runtime = composition.configure_document_parser_from_environment(environ={})

    assert runtime.backend == "disabled"
    assert runtime.dispatcher is None
    assert reset_calls == [True]


def test_unknown_backend_is_rejected():
    with pytest.raises(composition.DocumentParserConfigurationError, match="Unsupported"):
        composition.configure_document_parser_from_environment(
            environ={"PARSER_DISPATCH_BACKEND": "redis"}
        )


def test_inprocess_requires_real_parser_factory():
    with pytest.raises(composition.DocumentParserConfigurationError, match="real parser factory"):
        composition.configure_document_parser_from_environment(
            environ={"PARSER_DISPATCH_BACKEND": "inprocess"}
        )


@pytest.mark.parametrize("value", ["0", "1001", "abc"])
def test_inprocess_queue_size_is_bounded(value):
    with pytest.raises(composition.DocumentParserConfigurationError):
        composition.configure_document_parser_from_environment(
            parser_factory=FakeParser,
            environ={
                "PARSER_DISPATCH_BACKEND": "inprocess",
                "PARSER_INPROCESS_QUEUE_SIZE": value,
            },
        )


def test_inprocess_worker_owns_and_closes_session(monkeypatch):
    session = FakeSession()
    processed = Event()
    configured = []
    calls = []

    def fake_run(active_session, document_id, parser):
        calls.append((active_session, document_id, parser))
        processed.set()

    monkeypatch.setattr(composition, "run_document_parser", fake_run)
    monkeypatch.setattr(
        composition,
        "configure_document_parser_dispatcher",
        lambda dispatcher: configured.append(dispatcher),
    )

    runtime = composition.configure_document_parser_from_environment(
        parser_factory=FakeParser,
        session_factory=lambda: session,
        environ={
            "PARSER_DISPATCH_BACKEND": "inprocess",
            "PARSER_INPROCESS_QUEUE_SIZE": "2",
        },
    )
    try:
        assert runtime.dispatcher is configured[0]
        assert runtime.dispatcher.enqueue(document_id="doc-1") is True
        assert processed.wait(timeout=1.0)
        assert calls[0][0] is session
        assert calls[0][1] == "doc-1"
        assert isinstance(calls[0][2], FakeParser)
        assert session.closed is True
    finally:
        runtime.shutdown()


def test_runtime_shutdown_resets_dispatcher(monkeypatch):
    reset_calls = []
    monkeypatch.setattr(composition, "reset_document_parser_dispatcher", lambda: reset_calls.append(True))

    runtime = composition.DocumentParserRuntime(backend="disabled")
    runtime.shutdown()
    runtime.shutdown()

    assert reset_calls == [True]
