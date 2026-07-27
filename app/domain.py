from datetime import datetime, timezone
import json
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import Attachment, EventAudit, HistoryEvent, ServiceItem, ServiceVisit, VisitAudit

COST_STATUSES = {"known", "included_in_visit", "free", "unknown", "not_applicable"}
VISIT_KINDS = {"repair_visit", "maintenance_visit", "diagnostic_visit", "estimate_visit", "note"}
ITEM_TYPES = {"operation", "part", "fluid", "labor", "diagnostic", "note"}


def now(): return datetime.now(timezone.utc)


def kopecks_from_rubles(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return int(round(float(value) * 100))
    text = str(value).replace(" ", "").replace(",", ".")
    return int(round(float(text) * 100))


def rubles_from_kopecks(value):
    return None if value is None else value / 100


def event_snapshot(event: HistoryEvent):
    return {
        "id": event.id, "kind": event.kind, "event_date": event.event_date.isoformat(),
        "mileage": event.mileage, "title": event.title, "description": event.description,
        "cost_kopecks": event.cost_kopecks, "cost_visible_to_public": event.cost_visible_to_public,
        "trust_level": event.trust_level, "revision": event.revision,
        "is_deleted": event.is_deleted,
    }


def visit_snapshot(visit: ServiceVisit, items=None):
    payload = {
        "id": visit.id,
        "kind": visit.kind,
        "visit_date": visit.visit_date.isoformat(),
        "mileage": visit.mileage,
        "title": visit.title,
        "location": visit.location,
        "description": visit.description,
        "total_cost_kopecks": visit.total_cost_kopecks,
        "total_cost_status": visit.total_cost_status,
        "total_cost_visible_to_public": visit.total_cost_visible_to_public,
        "trust_level": visit.trust_level,
        "revision": visit.revision,
        "is_deleted": visit.is_deleted,
    }
    if items is not None:
        payload["items"] = [item_snapshot(x) for x in items]
    return payload


def item_snapshot(item: ServiceItem):
    return {
        "id": item.id,
        "item_type": item.item_type,
        "title": item.title,
        "description": item.description,
        "brand": item.brand,
        "part_number": item.part_number,
        "quantity": item.quantity,
        "unit": item.unit,
        "cost_kopecks": item.cost_kopecks,
        "cost_status": item.cost_status,
        "is_deleted": item.is_deleted,
    }


def audit(session: Session, event: HistoryEvent, actor_user_id: str, action: str, before=None, after=None):
    session.add(EventAudit(event_id=event.id, actor_user_id=actor_user_id, action=action,
        revision=event.revision, before_json=json.dumps(before, ensure_ascii=False) if before else None,
        after_json=json.dumps(after, ensure_ascii=False) if after else None, created_at=now()))


def visit_audit(session: Session, visit: ServiceVisit, actor_user_id: str, action: str, before=None, after=None):
    session.add(VisitAudit(visit_id=visit.id, actor_user_id=actor_user_id, action=action,
        revision=visit.revision, before_json=json.dumps(before, ensure_ascii=False) if before else None,
        after_json=json.dumps(after, ensure_ascii=False) if after else None, created_at=now()))


def recalc_trust(session: Session, event: HistoryEvent):
    evidence = set(session.scalars(select(Attachment.evidence_type).where(
        Attachment.event_id == event.id, Attachment.is_deleted.is_(False))))
    if evidence & {"receipt", "work_order", "service_act"}:
        event.trust_level = "verified"
    elif evidence & {"mechanic_confirmation", "photo_after"}:
        event.trust_level = "confirmed"
    elif event.kind in {"diagnostic", "estimate"} and evidence & {"diagnostic_report", "estimate", "correspondence"}:
        event.trust_level = "confirmed"
    else:
        event.trust_level = "declared"
    session.flush()


def recalc_visit_trust(session: Session, visit: ServiceVisit):
    evidence = set(session.scalars(select(Attachment.evidence_type).where(
        Attachment.visit_id == visit.id, Attachment.is_deleted.is_(False))))
    if evidence & {"receipt", "work_order", "service_act"}:
        visit.trust_level = "verified"
    elif evidence & {"mechanic_confirmation", "photo_after"}:
        visit.trust_level = "confirmed"
    elif visit.kind in {"diagnostic_visit", "estimate_visit"} and evidence & {"diagnostic_report", "estimate", "correspondence"}:
        visit.trust_level = "confirmed"
    else:
        visit.trust_level = "declared"
    session.flush()


def validate_cost_status(status: str):
    if status not in COST_STATUSES:
        raise ValueError(f"Unsupported cost status: {status}")
    return status


def validate_visit_kind(kind: str):
    if kind not in VISIT_KINDS:
        raise ValueError(f"Unsupported visit kind: {kind}")
    return kind


def validate_item_type(item_type: str):
    if item_type not in ITEM_TYPES:
        raise ValueError(f"Unsupported item type: {item_type}")
    return item_type


def mask_vin(vin: str):
    return vin[:5] + "*******" + vin[-5:] if len(vin) == 17 else "***"
