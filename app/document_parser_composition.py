"""Environment-driven composition for document parser dispatch.

Production remains disabled unless an explicit backend and a real parser factory are
provided. This module wires transport to the provider-neutral runner; it does not
implement OCR, fabricate drafts, or create vehicle-history records.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import os
from typing import Any

from .database import SessionLocal
from .document_parser_dispatch import (
    configure_document_parser_dispatcher,
    reset_document_parser_dispatcher,
)
from .document_parser_inprocess import InProcessDocumentParserDispatcher
from .document_parser_runner import DocumentParser, run_document_parser


class DocumentParserConfigurationError(RuntimeError):
    """Raised when parser dispatch configuration is unsafe or unsupported."""


ParserFactory = Callable[[], DocumentParser]
SessionFactory = Callable[[], Any]


@dataclass
class DocumentParserRuntime:
    """Own the configured dispatcher and release it during application shutdown."""

    backend: str
    dispatcher: InProcessDocumentParserDispatcher | None = None
    _closed: bool = False

    def shutdown(self, *, wait: bool = True, timeout: float | None = 5.0) -> None:
        if self._closed:
            return
        self._closed = True
        reset_document_parser_dispatcher()
        if self.dispatcher is not None:
            self.dispatcher.shutdown(wait=wait, timeout=timeout)


def _queue_size(raw_value: str) -> int:
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as error:
        raise DocumentParserConfigurationError(
            "PARSER_INPROCESS_QUEUE_SIZE must be an integer"
        ) from error
    if not 1 <= value <= 1000:
        raise DocumentParserConfigurationError(
            "PARSER_INPROCESS_QUEUE_SIZE must be between 1 and 1000"
        )
    return value


def configure_document_parser_from_environment(
    *,
    parser_factory: ParserFactory | None = None,
    session_factory: SessionFactory = SessionLocal,
    environ: Mapping[str, str] | None = None,
) -> DocumentParserRuntime:
    """Configure the process-wide parser dispatcher from explicit environment values.

    Supported backends:
    - ``disabled`` (default): durable uploads remain available for later recovery.
    - ``inprocess``: development/single-process transport requiring a real parser factory.
    """

    values = os.environ if environ is None else environ
    backend = values.get("PARSER_DISPATCH_BACKEND", "disabled").strip().lower()

    if backend == "disabled":
        reset_document_parser_dispatcher()
        return DocumentParserRuntime(backend="disabled")

    if backend != "inprocess":
        raise DocumentParserConfigurationError(
            f"Unsupported PARSER_DISPATCH_BACKEND: {backend or '<empty>'}"
        )
    if parser_factory is None:
        raise DocumentParserConfigurationError(
            "PARSER_DISPATCH_BACKEND=inprocess requires a real parser factory"
        )
    if not callable(parser_factory):
        raise TypeError("parser_factory must be callable")
    if not callable(session_factory):
        raise TypeError("session_factory must be callable")

    max_queue_size = _queue_size(values.get("PARSER_INPROCESS_QUEUE_SIZE", "100"))

    def worker(document_id: str) -> None:
        session = session_factory()
        try:
            parser = parser_factory()
            if not isinstance(parser, DocumentParser):
                raise DocumentParserConfigurationError(
                    "parser_factory must return a DocumentParser implementation"
                )
            run_document_parser(session, document_id, parser)
        finally:
            session.close()

    dispatcher = InProcessDocumentParserDispatcher(
        worker,
        max_queue_size=max_queue_size,
    )
    configure_document_parser_dispatcher(dispatcher)
    return DocumentParserRuntime(backend="inprocess", dispatcher=dispatcher)
