from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from fastapi.testclient import TestClient


DEMO_VIN = "DEMO-CONFIRM-0001"


def load_app(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    storage_path = tmp_path / "storage"
    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": database_url,
            "STORAGE_PATH": str(storage_path),
            "PUBLIC_BASE_URL": "http://testserver",
        }
    )
    migrated = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert migrated.returncode == 0, migrated.stderr
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("STORAGE_PATH", str(storage_path))
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://testserver")
    import app.main
    return app.main


def csrf(client):
    return {"X-CSRF-Token": client.cookies.get("autopassport_csrf")}


def register(client, email="owner@example.com"):
    response = client.post(
        "/api/auth/register",
        data={"email": email, "password": "StrongPassword123"},
    )
    assert response.status_code == 201, response.text


def create_vehicle(client):
    response = client.post(
        "/api/vehicles",
        headers=csrf(client),
        data={
            "vin": DEMO_VIN,
            "registration_number": "TEST",
            "make": "Mazda",
            "model": "3 BK",
            "trim": "",
            "year": 2006,
            "current_mileage": 178000,
            "purchase_date": "",
            "purchase_mileage": "",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_reviewable_document(client, vehicle_id):
    uploaded = client.post(
        f"/api/vehicles/{vehicle_id}/documents",
        headers=csrf(client),
        data={"document_type": "work_order"},
        files={"file": ("order.pdf", b"%PDF-1.4 confirmed order", "application/pdf")},
    )
    assert uploaded.status_code == 201, uploaded.text
    document_id = uploaded.json()["id"]
    draft = client.post(
        f"/api/documents/{document_id}/draft",
        headers=csrf(client),
        json={
            "extracted_text": "Заказ-наряд после проверки владельцем",
            "proposed_fields": {
                "kind": "repair_visit",
                "visit_date": "2026-07-14",
                "mileage": 178711,
                "title": "Замена датчика кислорода",
                "service_name": "Проверенный автосервис",
                "description": "Данные проверены владельцем",
                "total_cost_status": "known",
                "total_cost_rubles": 4800,
                "items": [
                    {
                        "item_type": "part",
                        "title": "Датчик кислорода",
                        "brand": "Example",
                        "cost_status": "known",
                        "cost_rubles": 3500,
                    },
                    {
                        "item_type": "labor",
                        "title": "Замена датчика",
                        "cost_status": "known",
                        "cost_rubles": 1300,
                    },
                ],
            },
            "confidence": {"mileage": 0.98, "total_cost_rubles": 0.91},
            "parser_name": "contract-test-parser",
            "parser_version": "1.0",
        },
    )
    assert draft.status_code == 201, draft.text
    return document_id


def test_owner_confirmation_creates_one_linked_service_visit(tmp_path, monkeypatch):
    main = load_app(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        register(client)
        vehicle_id = create_vehicle(client)
        document_id = create_reviewable_document(client, vehicle_id)

        confirmed = client.post(
            f"/api/documents/{document_id}/draft/confirm",
            headers=csrf(client),
        )
        assert confirmed.status_code == 201, confirmed.text
        result = confirmed.json()
        assert result["document_status"] == "confirmed"
        assert result["draft_status"] == "confirmed"
        assert result["current_mileage"] == 178711

        detail = client.get(f"/api/vehicles/{vehicle_id}").json()
        assert detail["events"] == []
        assert len(detail["visits"]) == 1
        visit = detail["visits"][0]
        assert visit["id"] == result["visit_id"]
        assert visit["title"] == "Замена датчика кислорода"
        assert visit["location"] == "Проверенный автосервис"
        assert visit["total_cost_rubles"] == 4800
        assert visit["trust_level"] == "verified"
        assert len(visit["items"]) == 2
        assert sum(item["cost_rubles"] for item in visit["items"]) == 4800

        inbox = client.get(f"/api/vehicles/{vehicle_id}/documents").json()["documents"]
        assert inbox[0]["status"] == "confirmed"
        assert inbox[0]["linked_visit_id"] == result["visit_id"]


def test_confirmation_is_idempotency_guarded(tmp_path, monkeypatch):
    main = load_app(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        register(client)
        vehicle_id = create_vehicle(client)
        document_id = create_reviewable_document(client, vehicle_id)
        first = client.post(
            f"/api/documents/{document_id}/draft/confirm",
            headers=csrf(client),
        )
        second = client.post(
            f"/api/documents/{document_id}/draft/confirm",
            headers=csrf(client),
        )
        assert first.status_code == 201
        assert second.status_code == 409
        assert len(client.get(f"/api/vehicles/{vehicle_id}/visits").json()) == 1


def test_invalid_reviewed_fields_do_not_create_partial_history(tmp_path, monkeypatch):
    main = load_app(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        register(client)
        vehicle_id = create_vehicle(client)
        uploaded = client.post(
            f"/api/vehicles/{vehicle_id}/documents",
            headers=csrf(client),
            data={"document_type": "receipt"},
            files={"file": ("receipt.pdf", b"%PDF-1.4 receipt", "application/pdf")},
        ).json()
        draft = client.post(
            f"/api/documents/{uploaded['id']}/draft",
            headers=csrf(client),
            json={
                "extracted_text": "Недостаточно данных",
                "proposed_fields": {"mileage": 178500},
                "confidence": {},
                "parser_name": "contract-test-parser",
                "parser_version": "1.0",
            },
        )
        assert draft.status_code == 201

        rejected = client.post(
            f"/api/documents/{uploaded['id']}/draft/confirm",
            headers=csrf(client),
        )
        assert rejected.status_code == 422
        detail = client.get(f"/api/vehicles/{vehicle_id}").json()
        assert detail["events"] == []
        assert detail["visits"] == []
        inbox = client.get(f"/api/vehicles/{vehicle_id}/documents").json()["documents"]
        assert inbox[0]["status"] == "needs_review"
        assert inbox[0]["linked_visit_id"] is None
