from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os

from sqlalchemy import event, func, select
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from .models import ShareLink, Vehicle


MAX_ACTIVE_SHARE_LINKS_PER_VEHICLE = int(os.getenv("MAX_ACTIVE_SHARE_LINKS_PER_VEHICLE", "1"))
MAX_ACTIVE_SHARE_LINKS_PER_OWNER = int(os.getenv("MAX_ACTIVE_SHARE_LINKS_PER_OWNER", "10"))


class ShareQuotaExceeded(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ShareUsage:
    active_owner_links: int
    active_vehicle_links: int


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _active_filter(now: datetime):
    return (
        ShareLink.revoked_at.is_(None),
        ShareLink.expires_at > now,
    )


def share_usage_for_owner(
    session: Session,
    owner_id: str,
    *,
    vehicle_id: str | None = None,
    now: datetime | None = None,
) -> ShareUsage:
    current = now or _now()
    owner_count = session.scalar(
        select(func.count(ShareLink.id))
        .join(Vehicle, Vehicle.id == ShareLink.vehicle_id)
        .where(Vehicle.owner_id == owner_id, *_active_filter(current))
    ) or 0
    vehicle_count = 0
    if vehicle_id:
        vehicle_count = session.scalar(
            select(func.count(ShareLink.id)).where(
                ShareLink.vehicle_id == vehicle_id,
                *_active_filter(current),
            )
        ) or 0
    return ShareUsage(int(owner_count), int(vehicle_count))


def owner_share_usage(session: Session, owner_id: str) -> dict:
    usage = share_usage_for_owner(session, owner_id)
    return {
        "active_links": usage.active_owner_links,
        "max_active_links": MAX_ACTIVE_SHARE_LINKS_PER_OWNER,
        "remaining_links": max(0, MAX_ACTIVE_SHARE_LINKS_PER_OWNER - usage.active_owner_links),
    }


def _owner_id(connection: Connection, vehicle_id: str) -> str:
    owner_id = connection.scalar(select(Vehicle.owner_id).where(Vehicle.id == vehicle_id))
    if not owner_id:
        raise ShareQuotaExceeded("share_owner_unresolved", "Vehicle owner could not be resolved")
    return str(owner_id)


@event.listens_for(ShareLink, "before_insert")
def enforce_share_limits(_mapper, connection: Connection, target: ShareLink) -> None:
    current = _now()
    owner_id = _owner_id(connection, target.vehicle_id)

    vehicle_count = connection.scalar(
        select(func.count(ShareLink.id)).where(
            ShareLink.vehicle_id == target.vehicle_id,
            *_active_filter(current),
        )
    ) or 0
    if int(vehicle_count) >= MAX_ACTIVE_SHARE_LINKS_PER_VEHICLE:
        raise ShareQuotaExceeded(
            "vehicle_share_link_quota_exceeded",
            "Active public link limit reached for this vehicle",
        )

    owner_count = connection.scalar(
        select(func.count(ShareLink.id))
        .join(Vehicle, Vehicle.id == ShareLink.vehicle_id)
        .where(Vehicle.owner_id == owner_id, *_active_filter(current))
    ) or 0
    if int(owner_count) >= MAX_ACTIVE_SHARE_LINKS_PER_OWNER:
        raise ShareQuotaExceeded(
            "owner_share_link_quota_exceeded",
            "Active public link limit reached for this owner",
        )
