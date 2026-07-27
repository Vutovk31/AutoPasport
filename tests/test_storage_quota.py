from __future__ import annotations

from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Attachment, HistoryEvent, ServiceVisit, User, Vehicle
from app.storage_quota import owner_storage_usage


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def seed_owner(session):
    user = User(email="owner@example.test", password_hash="hash")
    session.add(user)
    session.flush()
    vehicle = Vehicle(
        owner_id=user.id,
        vin="TESTVIN0000000001",
        make="Mazda",
        model="3",
        year=2006,
        current_mileage=178000,
    )
    session.add(vehicle)
    session.flush()
    event = HistoryEvent(
        vehicle_id=vehicle.id,
        kind="repair",
        event_date=date(2026, 7, 1),
        title="Repair",
        description="",
    )
    visit = ServiceVisit(
        vehicle_id=vehicle.id,
        kind="repair_visit",
        visit_date=date(2026, 7, 2),
        title="Service visit",
        description="",
    )
    session.add_all([event, visit])
    session.commit()
    return user, vehicle, event, visit


def attachment(*, event_id=None, visit_id=None, name="doc.pdf", size=10, deleted=False):
    return Attachment(
        event_id=event_id,
        visit_id=visit_id,
        original_name=name,
        stored_name=f"stored-{name}",
        media_type="application/pdf",
        evidence_type="receipt",
        size_bytes=size,
        sha256="0" * 64,
        is_deleted=deleted,
    )


def test_owner_attachment_count_quota_covers_events_and_visits(monkeypatch):
    monkeypatch.setenv("MAX_OWNER_ATTACHMENTS", "2")
    monkeypatch.setenv("MAX_OWNER_STORAGE_BYTES", "1000")
    session = make_session()
    _, _, event, visit = seed_owner(session)

    session.add(attachment(event_id=event.id, name="one.pdf"))
    session.commit()
    session.add(attachment(visit_id=visit.id, name="two.pdf"))
    session.commit()

    session.add(attachment(event_id=event.id, name="three.pdf"))
    with pytest.raises(HTTPException) as exc:
        session.commit()

    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "owner_attachment_quota_exceeded"
    session.rollback()


def test_owner_storage_byte_quota_rejects_projected_usage(monkeypatch):
    monkeypatch.setenv("MAX_OWNER_ATTACHMENTS", "10")
    monkeypatch.setenv("MAX_OWNER_STORAGE_BYTES", "15")
    session = make_session()
    _, _, event, visit = seed_owner(session)

    session.add(attachment(event_id=event.id, name="one.pdf", size=10))
    session.commit()
    session.add(attachment(visit_id=visit.id, name="two.pdf", size=6))

    with pytest.raises(HTTPException) as exc:
        session.commit()

    assert exc.value.status_code == 413
    assert exc.value.detail["code"] == "owner_storage_quota_exceeded"
    assert exc.value.detail["projected_bytes"] == 16
    session.rollback()


def test_soft_deleted_attachments_do_not_consume_quota(monkeypatch):
    monkeypatch.setenv("MAX_OWNER_ATTACHMENTS", "1")
    monkeypatch.setenv("MAX_OWNER_STORAGE_BYTES", "10")
    session = make_session()
    _, _, event, _ = seed_owner(session)

    session.add(attachment(event_id=event.id, name="deleted.pdf", size=10, deleted=True))
    session.commit()
    session.add(attachment(event_id=event.id, name="active.pdf", size=10))
    session.commit()

    assert session.query(Attachment).count() == 2


def test_attachment_without_resolvable_owner_is_rejected(monkeypatch):
    monkeypatch.setenv("MAX_OWNER_ATTACHMENTS", "10")
    monkeypatch.setenv("MAX_OWNER_STORAGE_BYTES", "1000")
    session = make_session()
    session.add(attachment(name="detached.pdf"))

    with pytest.raises(HTTPException) as exc:
        session.commit()

    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "attachment_owner_unresolved"
    session.rollback()


def test_owner_storage_usage_returns_limits_remaining_and_percent(monkeypatch):
    monkeypatch.setenv("MAX_OWNER_ATTACHMENTS", "4")
    monkeypatch.setenv("MAX_OWNER_STORAGE_BYTES", "100")
    session = make_session()
    user, _, event, visit = seed_owner(session)

    session.add_all([
        attachment(event_id=event.id, name="one.pdf", size=10),
        attachment(visit_id=visit.id, name="two.pdf", size=15),
        attachment(event_id=event.id, name="deleted.pdf", size=90, deleted=True),
    ])
    session.commit()

    usage = owner_storage_usage(session, user.id)

    assert usage == {
        "attachments": 2,
        "bytes_used": 25,
        "max_attachments": 4,
        "max_bytes": 100,
        "attachments_remaining": 2,
        "bytes_remaining": 75,
        "attachments_percent": 50.0,
        "bytes_percent": 25.0,
    }


def test_owner_storage_usage_for_owner_without_vehicles_is_zero(monkeypatch):
    monkeypatch.setenv("MAX_OWNER_ATTACHMENTS", "10")
    monkeypatch.setenv("MAX_OWNER_STORAGE_BYTES", "1000")
    session = make_session()
    user = User(email="empty@example.test", password_hash="hash")
    session.add(user)
    session.commit()

    usage = owner_storage_usage(session, user.id)

    assert usage["attachments"] == 0
    assert usage["bytes_used"] == 0
    assert usage["attachments_remaining"] == 10
    assert usage["bytes_remaining"] == 1000
    assert usage["attachments_percent"] == 0.0
    assert usage["bytes_percent"] == 0.0
