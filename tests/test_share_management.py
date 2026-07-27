from datetime import datetime, timedelta, timezone
from pathlib import Path

DEMO_VIN = "DEMO-VIN-00000001"


def test_active_share_list_contract(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'shares.db'}")
    for name in ["app.main", "app.application", "app.models", "app.database", "app.share_limits"]:
        import sys
        sys.modules.pop(name, None)

    from app.database import Base, engine, SessionLocal
    from app.models import ShareLink, User, Vehicle
    from app.share_limits import active_share_links

    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        user = User(email="owner@example.test", password_hash="hash")
        session.add(user); session.flush()
        vehicle = Vehicle(owner_id=user.id, vin=DEMO_VIN, make="Mazda", model="3", year=2006, current_mileage=178000)
        session.add(vehicle); session.flush()
        active = ShareLink(vehicle_id=vehicle.id, token_hash="a" * 64, created_at=now, expires_at=now + timedelta(minutes=30))
        expired = ShareLink(vehicle_id=vehicle.id, token_hash="b" * 64, created_at=now - timedelta(hours=2), expires_at=now - timedelta(hours=1))
        session.add_all([active, expired]); session.commit()

        rows = active_share_links(session, user.id, now=now)
        assert len(rows) == 1
        assert rows[0]["id"] == active.id
        assert rows[0]["vehicle"]["make"] == "Mazda"
        assert 1790 <= rows[0]["seconds_remaining"] <= 1800


def test_share_management_routes_and_ui_exist():
    root = Path(__file__).resolve().parents[1]
    main = (root / "app/main.py").read_text(encoding="utf-8")
    application = (root / "app/application.py").read_text(encoding="utf-8")
    html = (root / "app/static/index.html").read_text(encoding="utf-8")
    js = (root / "app/static/main.js").read_text(encoding="utf-8")

    assert '@app.get("/api/me/shares/list"' in main
    assert '@app.delete("/api/share/{share_id}"' in application
    assert 'id="activeShareList"' in html
    assert "api('/api/me/shares/list')" in js
    assert "class=\"revoke-share secondary\"" in js
    assert "method: 'DELETE'" in js
    assert "await refreshShares()" in js
