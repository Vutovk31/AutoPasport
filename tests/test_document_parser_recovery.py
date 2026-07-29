from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.document_parser_dispatch import ParserDispatchResult
from app.document_parser_recovery import recover_unqueued_documents
from app.models import DocumentInboxDocument, User, Vehicle


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _seed_document(session: Session, *, status: str, age_seconds: int) -> DocumentInboxDocument:
    user = User(email=f"owner-{status}-{age_seconds}@example.test", password_hash="hash")
    session.add(user)
    session.flush()
    vehicle = Vehicle(
        owner_id=user.id,
        vin=(f"TESTVIN{status}{age_seconds}".upper() + "0" * 17)[:17],
        make="Test",
        model="Vehicle",
        year=2020,
        current_mileage=1,
    )
    session.add(vehicle)
    session.flush()
    document = DocumentInboxDocument(
        owner_id=user.id,
        vehicle_id=vehicle.id,
        document_type="receipt",
        original_name="receipt.pdf",
        stored_name=f"{vehicle.id}.pdf",
        media_type="application/pdf",
        size_bytes=10,
        sha256="a" * 64,
        status=status,
        created_at=datetime.now(timezone.utc) - timedelta(seconds=age_seconds),
        updated_at=datetime.now(timezone.utc) - timedelta(seconds=age_seconds),
    )
    session.add(document)
    session.commit()
    return document


def test_recovery_dispatches_only_old_uploaded_documents_without_mutating_them():
    session = _session()
    old_uploaded = _seed_document(session, status="uploaded", age_seconds=120)
    _seed_document(session, status="uploaded", age_seconds=5)
    _seed_document(session, status="processing", age_seconds=120)
    dispatched: list[str] = []

    def dispatch(document_id: str) -> ParserDispatchResult:
        dispatched.append(document_id)
        return ParserDispatchResult(accepted=True, dispatcher="TestDispatcher")

    report = recover_unqueued_documents(
        session,
        limit=10,
        minimum_age_seconds=30,
        dispatch=dispatch,
    )

    assert dispatched == [old_uploaded.id]
    assert report.scanned == 1
    assert report.accepted == 1
    assert report.declined == 0
    assert session.get(DocumentInboxDocument, old_uploaded.id).status == "uploaded"


def test_recovery_is_bounded_and_reports_declined_dispatches():
    session = _session()
    first = _seed_document(session, status="uploaded", age_seconds=300)
    _seed_document(session, status="uploaded", age_seconds=200)

    report = recover_unqueued_documents(
        session,
        limit=1,
        minimum_age_seconds=0,
        dispatch=lambda document_id: ParserDispatchResult(
            accepted=False,
            dispatcher=f"Disabled:{document_id}",
        ),
    )

    assert report.scanned == 1
    assert report.accepted == 0
    assert report.declined == 1
    assert session.get(DocumentInboxDocument, first.id).status == "uploaded"


@pytest.mark.parametrize("limit", [0, 1001])
def test_recovery_rejects_unsafe_batch_limits(limit: int):
    session = _session()
    with pytest.raises(ValueError, match="limit"):
        recover_unqueued_documents(session, limit=limit)


def test_recovery_rejects_negative_safety_window():
    session = _session()
    with pytest.raises(ValueError, match="minimum_age_seconds"):
        recover_unqueued_documents(session, minimum_age_seconds=-1)
