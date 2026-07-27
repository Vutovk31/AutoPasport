from __future__ import annotations

from dataclasses import dataclass
import os

from fastapi import HTTPException
from sqlalchemy import event, func, or_, select


DEFAULT_MAX_OWNER_ATTACHMENTS = 100
DEFAULT_MAX_OWNER_STORAGE_BYTES = 250 * 1024 * 1024


@dataclass(frozen=True)
class StorageUsage:
    attachments: int
    bytes_used: int
    max_attachments: int
    max_bytes: int

    @staticmethod
    def _percent(used: int, maximum: int) -> float:
        if maximum <= 0:
            return 0.0
        return round(min(max(used / maximum * 100, 0.0), 100.0), 2)

    def as_dict(self) -> dict[str, int | float]:
        return {
            "attachments": self.attachments,
            "bytes_used": self.bytes_used,
            "max_attachments": self.max_attachments,
            "max_bytes": self.max_bytes,
            "attachments_remaining": max(self.max_attachments - self.attachments, 0),
            "bytes_remaining": max(self.max_bytes - self.bytes_used, 0),
            "attachments_percent": self._percent(self.attachments, self.max_attachments),
            "bytes_percent": self._percent(self.bytes_used, self.max_bytes),
        }


def _positive_limit(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be greater than zero")
    return value


def quota_limits() -> tuple[int, int]:
    return (
        _positive_limit("MAX_OWNER_ATTACHMENTS", DEFAULT_MAX_OWNER_ATTACHMENTS),
        _positive_limit("MAX_OWNER_STORAGE_BYTES", DEFAULT_MAX_OWNER_STORAGE_BYTES),
    )


def storage_usage_for_owner(
    connection,
    owner_id: str,
    *,
    Attachment,
    HistoryEvent,
    ServiceVisit,
    Vehicle,
) -> StorageUsage:
    """Return owner-wide active attachment usage for API and enforcement code."""
    max_attachments, max_bytes = quota_limits()
    vehicle_ids = select(Vehicle.id).where(Vehicle.owner_id == owner_id)
    event_ids = select(HistoryEvent.id).where(HistoryEvent.vehicle_id.in_(vehicle_ids))
    visit_ids = select(ServiceVisit.id).where(ServiceVisit.vehicle_id.in_(vehicle_ids))
    statement = select(
        func.count(Attachment.id),
        func.coalesce(func.sum(Attachment.size_bytes), 0),
    ).where(
        Attachment.is_deleted.is_(False),
        or_(Attachment.event_id.in_(event_ids), Attachment.visit_id.in_(visit_ids)),
    )
    count, bytes_used = connection.execute(statement).one()
    return StorageUsage(int(count or 0), int(bytes_used or 0), max_attachments, max_bytes)


def owner_storage_usage(session, owner_id: str) -> dict[str, int | float]:
    """Public application service used by the authenticated storage usage API."""
    from .models import Attachment, HistoryEvent, ServiceVisit, Vehicle

    usage = storage_usage_for_owner(
        session,
        owner_id,
        Attachment=Attachment,
        HistoryEvent=HistoryEvent,
        ServiceVisit=ServiceVisit,
        Vehicle=Vehicle,
    )
    return usage.as_dict()


def register_storage_quota_listener(*, Attachment, HistoryEvent, ServiceVisit, Vehicle) -> None:
    """Enforce owner-wide attachment quotas before an Attachment row is inserted.

    The check covers active attachments linked to every vehicle owned by the user,
    regardless of whether the file belongs to a legacy event or a service visit.
    """

    def owner_id_for_target(connection, target):
        if target.event_id:
            statement = (
                select(Vehicle.owner_id)
                .join(HistoryEvent, HistoryEvent.vehicle_id == Vehicle.id)
                .where(HistoryEvent.id == target.event_id)
            )
        elif target.visit_id:
            statement = (
                select(Vehicle.owner_id)
                .join(ServiceVisit, ServiceVisit.vehicle_id == Vehicle.id)
                .where(ServiceVisit.id == target.visit_id)
            )
        else:
            return None
        return connection.execute(statement).scalar_one_or_none()

    def before_insert(_mapper, connection, target):
        owner_id = owner_id_for_target(connection, target)
        if owner_id is None:
            raise HTTPException(
                status_code=409,
                detail={"code": "attachment_owner_unresolved", "message": "Attachment owner cannot be resolved"},
            )

        usage = storage_usage_for_owner(
            connection,
            owner_id,
            Attachment=Attachment,
            HistoryEvent=HistoryEvent,
            ServiceVisit=ServiceVisit,
            Vehicle=Vehicle,
        )
        if usage.attachments >= usage.max_attachments:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "owner_attachment_quota_exceeded",
                    "message": "Owner attachment count quota exceeded",
                    "usage": usage.as_dict(),
                },
            )

        projected_bytes = usage.bytes_used + int(target.size_bytes or 0)
        if projected_bytes > usage.max_bytes:
            raise HTTPException(
                status_code=413,
                detail={
                    "code": "owner_storage_quota_exceeded",
                    "message": "Owner storage quota exceeded",
                    "projected_bytes": projected_bytes,
                    "usage": usage.as_dict(),
                },
            )

    event.listen(Attachment, "before_insert", before_insert)
