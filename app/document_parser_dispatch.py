"""Post-commit dispatch boundary for document parser workers.

Document upload remains durable even when no worker transport is configured. A real
queue adapter can be installed by the application composition root; the default
adapter deliberately declines dispatch and never fabricates parser output.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from threading import RLock
from typing import Protocol, runtime_checkable


logger = logging.getLogger(__name__)


@runtime_checkable
class DocumentParserDispatcher(Protocol):
    """Queue one persisted inbox document for asynchronous parsing."""

    def enqueue(self, *, document_id: str) -> bool:
        """Return True only when a worker transport accepted the job."""


class DisabledDocumentParserDispatcher:
    """Safe default used until a real worker transport is configured."""

    def enqueue(self, *, document_id: str) -> bool:
        del document_id
        return False


@dataclass(frozen=True)
class ParserDispatchResult:
    accepted: bool
    dispatcher: str


_dispatcher_lock = RLock()
_dispatcher: DocumentParserDispatcher = DisabledDocumentParserDispatcher()


def configure_document_parser_dispatcher(dispatcher: DocumentParserDispatcher) -> None:
    """Install the process-wide queue adapter during application startup."""

    if not isinstance(dispatcher, DocumentParserDispatcher):
        raise TypeError("dispatcher must implement DocumentParserDispatcher")
    global _dispatcher
    with _dispatcher_lock:
        _dispatcher = dispatcher


def reset_document_parser_dispatcher() -> None:
    """Restore the disabled adapter, primarily for isolated tests."""

    global _dispatcher
    with _dispatcher_lock:
        _dispatcher = DisabledDocumentParserDispatcher()


def dispatch_document_for_parsing(document_id: str) -> ParserDispatchResult:
    """Attempt dispatch after the document transaction has committed.

    Queue outages must not roll back or delete an already accepted user document.
    The document remains in ``uploaded`` and can be retried by a later recovery
    sweep. Exception details are logged server-side and are not exposed to clients.
    """

    normalized_id = str(document_id).strip()
    if not normalized_id:
        raise ValueError("document_id is required")

    with _dispatcher_lock:
        dispatcher = _dispatcher

    dispatcher_name = type(dispatcher).__name__
    try:
        accepted = bool(dispatcher.enqueue(document_id=normalized_id))
    except Exception:
        logger.exception(
            "Document parser dispatch failed",
            extra={"document_id": normalized_id, "dispatcher": dispatcher_name},
        )
        accepted = False

    return ParserDispatchResult(accepted=accepted, dispatcher=dispatcher_name)
