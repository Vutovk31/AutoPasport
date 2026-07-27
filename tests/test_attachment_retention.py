from datetime import datetime, timedelta, timezone
import hashlib
import os
from pathlib import Path

from sqlalchemy import create_engine, insert
from sqlalchemy.orm import Session

from app.attachment_retention import run_attachment_retention
from app.models import Attachment, Base

NOW = datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc)


def add_attachment(session, *, attachment_id, stored_name, is_deleted, deleted_at=None):
    session.execute(insert(Attachment).values(
        id=attachment_id,
        event_id=None,
        visit_id=None,
        original_name="doc.pdf",
        stored_name=stored_name,
        media_type="application/pdf",
        evidence_type="receipt",
        size_bytes=4,
        sha256=hashlib.sha256(b"data").hexdigest(),
        is_deleted=is_deleted,
        deleted_at=deleted_at,
        purged_at=None,
        purge_reason=None,
    ))
    session.commit()


def setup_retention(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    storage = tmp_path / "storage"
    storage.mkdir()
    return Session(engine), storage


def age(path: Path, days: int):
    stamp = (NOW - timedelta(days=days)).timestamp()
    os.utime(path, (stamp, stamp))


def test_dry_run_does_not_delete_soft_deleted_candidate(tmp_path):
    session, storage = setup_retention(tmp_path)
    physical = storage / "deleted.pdf"
    physical.write_bytes(b"data")
    add_attachment(
        session,
        attachment_id="a",
        stored_name=physical.name,
        is_deleted=True,
        deleted_at=NOW - timedelta(days=40),
    )

    report = run_attachment_retention(
        session,
        storage_root=storage,
        retention_days=30,
        current_time=NOW,
    )

    assert report["mode"] == "dry-run"
    assert physical.exists()
    assert report["summary"]["candidates"] == 1


def test_apply_purges_old_soft_deleted_and_marks_database(tmp_path):
    session, storage = setup_retention(tmp_path)
    physical = storage / "deleted.pdf"
    physical.write_bytes(b"data")
    add_attachment(
        session,
        attachment_id="a",
        stored_name=physical.name,
        is_deleted=True,
        deleted_at=NOW - timedelta(days=40),
    )

    report = run_attachment_retention(
        session,
        storage_root=storage,
        retention_days=30,
        current_time=NOW,
        apply=True,
    )

    row = session.get(Attachment, "a")
    assert not physical.exists()
    assert row.purged_at is not None
    assert row.purge_reason == "retention_expired"
    assert report["actions"][0]["kind"] == "purged_soft_deleted_file"


def test_active_file_is_protected_even_when_old(tmp_path):
    session, storage = setup_retention(tmp_path)
    physical = storage / "active.pdf"
    physical.write_bytes(b"data")
    age(physical, 100)
    add_attachment(session, attachment_id="a", stored_name=physical.name, is_deleted=False)

    report = run_attachment_retention(
        session,
        storage_root=storage,
        retention_days=30,
        current_time=NOW,
        apply=True,
    )

    assert physical.exists()
    assert report["protected"][0]["kind"] == "active_file_protected"


def test_old_orphan_is_purged_and_recent_orphan_retained(tmp_path):
    session, storage = setup_retention(tmp_path)
    old = storage / "old.bin"
    old.write_bytes(b"x")
    age(old, 40)
    recent = storage / "recent.bin"
    recent.write_bytes(b"x")
    age(recent, 2)

    report = run_attachment_retention(
        session,
        storage_root=storage,
        retention_days=30,
        current_time=NOW,
        apply=True,
    )

    assert not old.exists()
    assert recent.exists()
    assert any(item["kind"] == "purged_orphan_file" for item in report["actions"])
    assert any(item["kind"] == "recent_orphan_file" for item in report["retained"])


def test_missing_active_file_blocks_apply_and_preserves_database(tmp_path):
    session, storage = setup_retention(tmp_path)
    add_attachment(session, attachment_id="a", stored_name="missing.pdf", is_deleted=False)

    report = run_attachment_retention(
        session,
        storage_root=storage,
        retention_days=30,
        current_time=NOW,
        apply=True,
    )

    row = session.get(Attachment, "a")
    assert report["missing"][0]["kind"] == "active_file_missing"
    assert report["blocked"] is True
    assert report["mode"] == "apply-blocked"
    assert row.is_deleted is False
    assert row.purged_at is None


def test_json_audit_report_is_written(tmp_path):
    session, storage = setup_retention(tmp_path)
    report_path = tmp_path / "reports" / "cleanup.json"

    report = run_attachment_retention(
        session,
        storage_root=storage,
        retention_days=30,
        current_time=NOW,
        report_path=report_path,
    )

    assert report_path.exists()
    assert report["report_path"] == str(report_path)
