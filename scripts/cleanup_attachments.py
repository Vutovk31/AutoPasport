#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.attachment_retention import run_attachment_retention
from app.config import load_runtime_config
from app.database import SessionLocal


def _default_report_path() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return ROOT / "data" / "reports" / f"attachment-retention-{stamp}.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scan attachment database/storage consistency and safely purge expired soft-deleted files."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Physically delete eligible files. Without this flag the command is dry-run only.",
    )
    parser.add_argument("--retention-days", type=int, help="Override ATTACHMENT_RETENTION_DAYS.")
    parser.add_argument("--storage-path", type=Path, help="Override STORAGE_PATH.")
    parser.add_argument("--report-path", type=Path, help="JSON audit report destination.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_runtime_config()
    retention_days = args.retention_days or config.attachment_retention_days
    storage_path = (args.storage_path or config.storage_path).expanduser().resolve()
    report_path = (args.report_path or _default_report_path()).expanduser().resolve()

    with SessionLocal() as session:
        report = run_attachment_retention(
            session,
            storage_root=storage_path,
            retention_days=retention_days,
            apply=args.apply,
            report_path=report_path,
        )

    print(json.dumps({
        "mode": report["mode"],
        "blocked": report["blocked"],
        "summary": report["summary"],
        "report_path": report["report_path"],
    }, ensure_ascii=False, indent=2))
    return 2 if report["blocked"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
