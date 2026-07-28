"""Explicit owner confirmation boundary for reviewed document drafts.

A reviewed AI draft may create exactly one service visit only after an authenticated
owner confirms it. The source document is then linked to that visit. Repeated or
partial confirmation is rejected; parser output never mutates history by itself.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .domain import (
    kopecks_from_rubles,
    validate_cost_status,
    validate_item_type,
    validate_visit_kind,
    visit_audit,
    visit_snapshot,
)
from .models import (
    DocumentAIDraft,
    DocumentInboxDocument,
    ServiceItem,
    ServiceVisit,
    User,
    Vehicle,
)
from .security import db, mutation_guard


router = APIRouter(tags=["document-draft-confirmation"])


def _required_text(fields: dict, name: str) -> str:
    value = fields.get(name)
    if not isinstance(value, str) or not value.strip():
        raise HTTPException(422, f"{name} is required")
    return value.strip()


def _optional_text(fields: dict, name: str) -> str | None:
    value = fields.get(name)
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise HTTPException(422, f"{name} must be a string")
    return value.strip() or None


def _optional_mileage(fields: dict) -> int | None:
    value = fields.get("mileage")
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise HTTPException(422, "mileage must be a non-negative integer")
    try:
        mileage = int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(422, "mileage must be a non-negative integer") from exc
    if mileage < 0:
        raise HTTPException(422, "mileage must be a non-negative integer")
    return mileage


def _visit_date(fields: dict) -> date:
    value = _required_text(fields, "visit_date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(422, "visit_date must use YYYY-MM-DD") from exc


def _cost(fields: dict, status_name: str, value_name: str) -> tuple[str, int | None]:
    try:
        status = validate_cost_status(str(fields.get(status_name, "unknown")))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    value = fields.get(value_name)
    if status == "known":
        if value in (None, ""):
            raise HTTPException(422, f"{value_name} is required when {status_name}=known")
        try:
            amount = kopecks_from_rubles(value)
        except (TypeError, ValueError) as exc:
            raise HTTPException(422, f"{value_name} must be a number") from exc
        if amount is None or amount < 0:
            raise HTTPException(422, f"{value_name} must be non-negative")
        return status, amount
    return status, None


def _build_item(visit_id: str, row: dict) -> ServiceItem:
    if not isinstance(row, dict):
        raise HTTPException(422, "Each item must be an object")
    title = _required_text(row, "title")
    try:
        item_type = validate_item_type(str(row.get("item_type", "operation")))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    cost_status, cost_kopecks = _cost(row, "cost_status", "cost_rubles")
    return ServiceItem(
        visit_id=visit_id,
        item_type=item_type,
        title=title,
        description=_optional_text(row, "description") or "",
        brand=_optional_text(row, "brand"),
        part_number=_optional_text(row, "part_number"),
        quantity=str(row["quantity"]).strip() if row.get("quantity") not in (None, "") else None,
        unit=_optional_text(row, "unit"),
        cost_kopecks=cost_kopecks,
        cost_status=cost_status,
    )


@router.post("/api/documents/{document_id}/draft/confirm", status_code=201)
def confirm_document_draft(
    document_id: str,
    user: User = Depends(mutation_guard),
    session: Session = Depends(db),
):
    """Create one service visit from an explicitly reviewed owner draft."""

    document = session.get(DocumentInboxDocument, document_id)
    if document is None:
        raise HTTPException(404, "Document not found")
    if document.owner_id != user.id:
        raise HTTPException(403, "Forbidden")
    if document.status != "needs_review" or document.linked_visit_id is not None:
        raise HTTPException(409, "Document is not available for confirmation")

    draft = session.scalar(
        select(DocumentAIDraft).where(
            DocumentAIDraft.document_id == document.id,
            DocumentAIDraft.owner_id == user.id,
        )
    )
    if draft is None:
        raise HTTPException(404, "Draft not found")
    if draft.status != "needs_review":
        raise HTTPException(409, "Draft is not available for confirmation")

    vehicle = session.get(Vehicle, document.vehicle_id)
    if vehicle is None or vehicle.owner_id != user.id:
        raise HTTPException(409, "Document vehicle is unavailable")

    try:
        fields = json.loads(draft.proposed_fields_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(409, "Draft fields are invalid") from exc
    if not isinstance(fields, dict):
        raise HTTPException(409, "Draft fields are invalid")

    try:
        kind = validate_visit_kind(str(fields.get("kind", "repair_visit")))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    mileage = _optional_mileage(fields)
    total_cost_status, total_cost_kopecks = _cost(
        fields, "total_cost_status", "total_cost_rubles"
    )
    items = fields.get("items", [])
    if not isinstance(items, list):
        raise HTTPException(422, "items must be an array")

    visit = ServiceVisit(
        vehicle_id=vehicle.id,
        kind=kind,
        visit_date=_visit_date(fields),
        mileage=mileage,
        title=_required_text(fields, "title"),
        location=_optional_text(fields, "service_name") or _optional_text(fields, "location"),
        description=_optional_text(fields, "description") or draft.extracted_text.strip(),
        total_cost_kopecks=total_cost_kopecks,
        total_cost_status=total_cost_status,
        total_cost_visible_to_public=False,
        trust_level="verified",
        revision=1,
    )

    timestamp = datetime.now(timezone.utc)
    try:
        session.add(visit)
        session.flush()
        created_items = [_build_item(visit.id, row) for row in items]
        session.add_all(created_items)
        session.flush()
        if mileage is not None and mileage > vehicle.current_mileage:
            vehicle.current_mileage = mileage
        document.linked_visit_id = visit.id
        document.status = "confirmed"
        document.updated_at = timestamp
        draft.status = "confirmed"
        draft.updated_at = timestamp
        visit_audit(
            session,
            visit,
            user.id,
            "created_from_confirmed_document",
            after=visit_snapshot(visit, created_items),
        )
        session.commit()
        session.refresh(visit)
    except HTTPException:
        session.rollback()
        raise
    except Exception:
        session.rollback()
        raise

    return {
        "document_id": document.id,
        "draft_id": draft.id,
        "visit_id": visit.id,
        "document_status": document.status,
        "draft_status": draft.status,
        "current_mileage": vehicle.current_mileage,
    }
