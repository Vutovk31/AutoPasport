"""Bounded in-process transport for document parser jobs.

This adapter is intended for explicit development and single-process deployments only.
It transports persisted document identifiers to an injected worker callback. It does
not implement OCR, fabricate parser output, or mutate vehicle history.
"""

from __future__ import annotations

from collections.abc import Callable
import logging
from queue import Full, Queue
from threading import Event, Lock, Thread
from typing import Final


logger = logging.getLogger(__name__)
_STOP: Final = object()


class InProcessDocumentParserDispatcher:
    """Deliver parser jobs through one bounded background thread.

    The worker callback owns database-session creation and calls the provider-neutral
    parser runner. ``enqueue`` returns ``False`` when the queue is full or shutdown has
    started, allowing the existing recovery sweep to retry the persisted document.
    """

    def __init__(
        self,
        worker: Callable[[str], None],
        *,
        max_queue_size: int = 100,
        thread_name: str = "document-parser-worker",
    ) -> None:
        if not callable(worker):
            raise TypeError("worker must be callable")
        if isinstance(max_queue_size, bool) or not isinstance(max_queue_size, int):
            raise TypeError("max_queue_size must be an integer")
        if not 1 <= max_queue_size <= 1000:
            raise ValueError("max_queue_size must be between 1 and 1000")

        normalized_thread_name = str(thread_name).strip()
        if not normalized_thread_name:
            raise ValueError("thread_name is required")

        self._worker = worker
        self._queue: Queue[object] = Queue(maxsize=max_queue_size)
        self._closed = Event()
        self._shutdown_lock = Lock()
        self._thread = Thread(
            target=self._run,
            name=normalized_thread_name,
            daemon=True,
        )
        self._thread.start()

    def enqueue(self, *, document_id: str) -> bool:
        normalized_id = str(document_id).strip()
        if not normalized_id:
            raise ValueError("document_id is required")
        if self._closed.is_set():
            return False

        try:
            self._queue.put_nowait(normalized_id)
        except Full:
            return False
        return True

    def shutdown(self, *, wait: bool = True, timeout: float | None = 5.0) -> None:
        """Stop accepting jobs and request graceful worker termination.

        Already accepted jobs remain ahead of the sentinel and are processed first.
        Calling shutdown more than once is safe.
        """

        if timeout is not None and timeout < 0:
            raise ValueError("timeout must be non-negative or None")

        with self._shutdown_lock:
            if not self._closed.is_set():
                self._closed.set()
                self._queue.put(_STOP)

        if wait:
            self._thread.join(timeout=timeout)

    @property
    def is_alive(self) -> bool:
        return self._thread.is_alive()

    def _run(self) -> None:
        while True:
            item = self._queue.get()
            try:
                if item is _STOP:
                    return
                document_id = str(item)
                try:
                    self._worker(document_id)
                except Exception:
                    logger.exception(
                        "In-process document parser worker failed",
                        extra={"document_id": document_id},
                    )
            finally:
                self._queue.task_done()
