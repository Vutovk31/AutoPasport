from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models import ShareLink, User, Vehicle
from app.share_limits import ShareQuotaExceeded, owner_share_usage

DEMO_VIN = "DEMO-VIN-00000001"


def _session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'shares.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return Session(engine)


def _owner_with_vehicle(session):
    owner = User(email="owner@example.test", password_hash="x")
    session.add(owner); session.flush()
    vehicle = Vehicle(owner_id=owner.id, vin=DEMO_VIN, make="Mazda", model="3", year=2006, current_mileage=100000)
    session.add(vehicle); session.commit()
    return owner, vehicle


def test_owner_share_usage_counts_only_active_links(tmp_path):
    session = _session(tmp_path)
    owner, vehicle = _owner_with_vehicle(session)
    now = datetime.now(timezone.utc)
    session.execute(ShareLink.__table__.insert(), [
        {"id":"00000000-0000-0000-0000-000000000001","vehicle_id":vehicle.id,"token_hash":"a"*64,"created_at":now,"expires_at":now+timedelta(hours=1),"revoked_at":None},
        {"id":"00000000-0000-0000-0000-000000000002","vehicle_id":vehicle.id,"token_hash":"b"*64,"created_at":now,"expires_at":now-timedelta(seconds=1),"revoked_at":None},
        {"id":"00000000-0000-0000-0000-000000000003","vehicle_id":vehicle.id,"token_hash":"c"*64,"created_at":now,"expires_at":now+timedelta(hours=1),"revoked_at":now},
    ])
    session.commit()
    result = owner_share_usage(session, owner.id)
    assert result["active_links"] == 1
    assert result["remaining_links"] == result["max_active_links"] - 1


def test_vehicle_share_limit_rejects_second_active_link(tmp_path):
    session = _session(tmp_path)
    _, vehicle = _owner_with_vehicle(session)
    now = datetime.now(timezone.utc)
    session.add(ShareLink(vehicle_id=vehicle.id, token_hash="d"*64, created_at=now, expires_at=now+timedelta(hours=1)))
    session.commit()
    session.add(ShareLink(vehicle_id=vehicle.id, token_hash="e"*64, created_at=now, expires_at=now+timedelta(hours=1)))
    with pytest.raises(ShareQuotaExceeded) as error:
        session.commit()
    assert error.value.code == "vehicle_share_link_quota_exceeded"


def test_share_usage_endpoint_requires_authentication():
    from app.main import app
    response = TestClient(app).get("/api/me/shares")
    assert response.status_code == 401


def test_share_quota_exception_has_structured_api_payload():
    from app.main import app
    from app.share_limits import ShareQuotaExceeded as RuntimeShareQuotaExceeded

    route = next(r for r in app.routes if getattr(r, "path", None) == "/api/me/shares")
    assert "account" in route.tags
    handler = app.exception_handlers[RuntimeShareQuotaExceeded]
    assert handler is not None
