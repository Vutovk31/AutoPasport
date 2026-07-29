"""Operational command for redelivering durable parser jobs.

Run with::

    python -m app.document_parser_worker

The command only invokes the transport-neutral recovery sweep. It does not read
user document bytes, call OCR/AI providers, create drafts, or mutate vehicle
history.
"""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Callable, Sequence

from sqlalchemy.orm import Session

from .database import SessionLocal
from .document_parser_recovery import ParserRecoveryReport, recover_unqueued_documents

logger = logging.getLogger(__name__)
SessionFactory = Callable[[], Session]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Redeliver persisted uploaded documents to the parser dispatcher.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum documents to inspect in one bounded sweep (1-1000).",
    )
    parser.add_argument(
        "--minimum-age-seconds",
        type=int,
        default=30,
        help="Ignore documents newer than this safety window.",
    )
    return parser


def run_recovery_worker(
    *,
    session_factory: SessionFactory = SessionLocal,
    limit: int = 100,
    minimum_age_seconds: int = 30,
) -> ParserRecoveryReport:
    """Execute one recovery sweep and always close the database session."""

    session = session_factory()
    try:
        return recover_unqueued_documents(
            session,
            limit=limit,
            minimum_age_seconds=minimum_age_seconds,
        )
    finally:
        session.close()


def main(
    argv: Sequence[str] | None = None,
    *,
    session_factory: SessionFactory = SessionLocal,
) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = run_recovery_worker(
            session_factory=session_factory,
            limit=args.limit,
            minimum_age_seconds=args.minimum_age_seconds,
        )
    except Exception:
        logger.exception("Document parser recovery worker failed")
        return 1

    print(
        json.dumps(
            {
                "status": "ok",
                "scanned": report.scanned,
                "accepted": report.accepted,
                "declined": report.declined,
            },
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
