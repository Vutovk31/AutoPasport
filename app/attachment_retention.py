from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any
import json
import os
import tempfile

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Attachment

DEFAULT_RETENTION_DAYS = 30
PURGE_REASON_RETENTION = "retention_expired"
PURGE_REASON_MISSING = "missing_before_cleanup"


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _safe_relative_name(stored_name: str) -> str:
    normalized = stored_name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        not normalized
        or normalized.startswith("/")
        or path.is_absolute()
        or len(path.parts) != 1
        or path.parts[0] in {".", ".."}
    ):
        raise ValueError("Unsafe attachment stored_name")
    return path.as_posix()


def _safe_storage_path(storage_root: Path, relative_name: str, *, require_basename: bool = True) -> Path:
    normalized = relative_name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        not normalized
        or normalized.startswith("/")
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
        or (require_basename and len(path.parts) != 1)
    ):
        raise ValueError("Unsafe storage path")
    root = storage_root.resolve()
    target = (root / path.as_posix()).resolve(strict=False)
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("Attachment path escapes storage root") from exc
    return target


def _record(kind: str, **values: Any) -> dict[str, Any]:
    return {"kind": kind, **values}


def _iter_physical_files(storage_root: Path):
    if not storage_root.exists():
        return
    for path in storage_root.rglob("*"):
        if path.is_symlink():
            yield path, "symlink"
        elif path.is_file():
            yield path, "file"


def scan_attachment_retention(
    session: Session,
    *,
    storage_root: Path,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    current_time: datetime | None = None,
) -> dict[str, Any]:
    if retention_days <= 0:
        raise ValueError("retention_days must be greater than zero")

    current = _aware(current_time or datetime.now(timezone.utc))
    cutoff = current - timedelta(days=retention_days)
    root = storage_root.resolve()
    rows = list(session.scalars(select(Attachment).order_by(Attachment.id)))

    report: dict[str, Any] = {
        "generated_at": current.isoformat(),
        "retention_days": retention_days,
        "cutoff": cutoff.isoformat(),
        "storage_root": str(root),
        "candidates": [],
        "protected": [],
        "retained": [],
        "missing": [],
        "unsafe": [],
        "actions": [],
    }

    referenced_names: set[str] = set()
    for attachment in rows:
        try:
            relative_name = _safe_relative_name(attachment.stored_name)
            physical = _safe_storage_path(root, attachment.stored_name)
        except ValueError as exc:
            report["unsafe"].append(
                _record(
                    "unsafe_database_reference",
                    attachment_id=attachment.id,
                    stored_name=attachment.stored_name,
                    error=str(exc),
                )
            )
            continue

        referenced_names.add(relative_name)
        exists = physical.exists() and physical.is_file() and not physical.is_symlink()

        if not attachment.is_deleted:
            bucket = "protected" if exists else "missing"
            kind = "active_file_protected" if exists else "active_file_missing"
            report[bucket].append(
                _record(kind, attachment_id=attachment.id, stored_name=relative_name)
            )
            continue

        if attachment.purged_at is not None:
            if exists:
                report["unsafe"].append(
                    _record(
                        "purged_record_file_reappeared",
                        attachment_id=attachment.id,
                        stored_name=relative_name,
                    )
                )
            else:
                report["retained"].append(
                    _record(
                        "already_purged",
                        attachment_id=attachment.id,
                        stored_name=relative_name,
                        purged_at=_aware(attachment.purged_at).isoformat(),
                    )
                )
            continue

        if attachment.deleted_at is None:
            report["unsafe"].append(
                _record(
                    "soft_deleted_without_deleted_at",
                    attachment_id=attachment.id,
                    stored_name=relative_name,
                )
            )
            continue

        deleted_at = _aware(attachment.deleted_at)
        if deleted_at > cutoff:
            report["retained"].append(
                _record(
                    "retention_not_elapsed",
                    attachment_id=attachment.id,
                    stored_name=relative_name,
                    deleted_at=deleted_at.isoformat(),
                )
            )
        elif exists:
            report["candidates"].append(
                _record(
                    "soft_deleted_file",
                    attachment_id=attachment.id,
                    stored_name=relative_name,
                    deleted_at=deleted_at.isoformat(),
                )
            )
        else:
            report["missing"].append(
                _record(
                    "soft_deleted_file_missing",
                    attachment_id=attachment.id,
                    stored_name=relative_name,
                    deleted_at=deleted_at.isoformat(),
                )
            )

    for physical, physical_kind in _iter_physical_files(root) or ():
        relative_name = physical.relative_to(root).as_posix()
        if relative_name.startswith("."):
            continue
        if physical_kind == "symlink":
            report["unsafe"].append(_record("storage_symlink_skipped", stored_name=relative_name))
            continue
        if relative_name in referenced_names:
            continue
        modified_at = datetime.fromtimestamp(physical.stat().st_mtime, timezone.utc)
        target = report["candidates"] if modified_at <= cutoff else report["retained"]
        kind = "orphan_file" if modified_at <= cutoff else "recent_orphan_file"
        target.append(_record(kind, stored_name=relative_name, modified_at=modified_at.isoformat()))

    report["summary"] = {
        key: len(report[key])
        for key in ("candidates", "protected", "retained", "missing", "unsafe", "actions")
    }
    return report


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temp_name, path)
    finally:
        Path(temp_name).unlink(missing_ok=True)


def run_attachment_retention(
    session: Session,
    *,
    storage_root: Path,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    apply: bool = False,
    report_path: Path | None = None,
    current_time: datetime | None = None,
) -> dict[str, Any]:
    current = _aware(current_time or datetime.now(timezone.utc))
    report = scan_attachment_retention(
        session,
        storage_root=storage_root,
        retention_days=retention_days,
        current_time=current,
    )
    blocking_missing = [item for item in report["missing"] if item["kind"] == "active_file_missing"]
    report["blocked"] = bool(report["unsafe"] or blocking_missing)
    report["mode"] = "apply-blocked" if apply and report["blocked"] else ("apply" if apply else "dry-run")

    if apply and not report["blocked"]:
        cutoff = current - timedelta(days=retention_days)
        root = storage_root.resolve()
        for candidate in list(report["candidates"]):
            kind = candidate["kind"]
            stored_name = candidate["stored_name"]
            physical = _safe_storage_path(root, stored_name, require_basename=(kind == "soft_deleted_file"))

            if kind == "soft_deleted_file":
                attachment = session.get(Attachment, candidate["attachment_id"])
                if attachment is None:
                    report["actions"].append(_record("skip_attachment_disappeared", stored_name=stored_name))
                    continue
                if (
                    not attachment.is_deleted
                    or attachment.purged_at is not None
                    or attachment.deleted_at is None
                    or _aware(attachment.deleted_at) > cutoff
                    or attachment.stored_name != stored_name
                ):
                    report["actions"].append(
                        _record("skip_attachment_no_longer_eligible", attachment_id=attachment.id, stored_name=stored_name)
                    )
                    continue
                if physical.is_symlink():
                    report["actions"].append(_record("skip_symlink", attachment_id=attachment.id, stored_name=stored_name))
                    continue
                try:
                    physical.unlink()
                    attachment.purged_at = current
                    attachment.purge_reason = PURGE_REASON_RETENTION
                    report["actions"].append(
                        _record("purged_soft_deleted_file", attachment_id=attachment.id, stored_name=stored_name)
                    )
                except FileNotFoundError:
                    attachment.purged_at = current
                    attachment.purge_reason = PURGE_REASON_MISSING
                    report["actions"].append(
                        _record("marked_missing_soft_deleted_file", attachment_id=attachment.id, stored_name=stored_name)
                    )
            elif kind == "orphan_file":
                reference = session.scalar(select(Attachment.id).where(Attachment.stored_name == stored_name).limit(1))
                if reference is not None:
                    report["actions"].append(_record("skip_orphan_now_referenced", stored_name=stored_name))
                    continue
                if physical.is_symlink():
                    report["actions"].append(_record("skip_symlink", stored_name=stored_name))
                    continue
                try:
                    physical.unlink()
                    report["actions"].append(_record("purged_orphan_file", stored_name=stored_name))
                except FileNotFoundError:
                    report["actions"].append(_record("orphan_already_missing", stored_name=stored_name))
        session.commit()

    report["summary"] = {
        key: len(report[key])
        for key in ("candidates", "protected", "retained", "missing", "unsafe", "actions")
    }
    if report_path is not None:
        report["report_path"] = str(report_path)
        _atomic_write_json(report_path, report)
    return report
