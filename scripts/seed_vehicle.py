import json
import sys
from pathlib import Path
from datetime import date
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from sqlalchemy import select
from app.database import SessionLocal
from app.domain import kopecks_from_rubles, validate_cost_status, validate_item_type, validate_visit_kind, visit_audit, visit_snapshot
from app.models import HistoryEvent, ServiceItem, ServiceVisit, User, Vehicle
from app.security import password_hash


def parse_date(value):
    return date.fromisoformat(value) if value else None


def main(path):
    data = json.load(open(path, encoding="utf-8"))
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == data["owner_email"]))
        if not user:
            user = User(email=data["owner_email"], password_hash=password_hash(data["owner_password"]))
            session.add(user)
            session.flush()

        vehicle_data = data["vehicle"]
        vehicle = Vehicle(
            owner_id=user.id,
            vin=vehicle_data["vin"].strip().upper(),
            registration_number=vehicle_data.get("registration_number"),
            make=vehicle_data["make"],
            model=vehicle_data["model"],
            trim=vehicle_data.get("trim"),
            year=vehicle_data["year"],
            current_mileage=vehicle_data["current_mileage"],
            purchase_date=parse_date(vehicle_data.get("purchase_date")),
            purchase_mileage=vehicle_data.get("purchase_mileage"),
        )
        session.add(vehicle)
        session.flush()

        for row in data.get("events", []):
            session.add(HistoryEvent(
                vehicle_id=vehicle.id,
                kind=row["kind"],
                event_date=parse_date(row["event_date"]),
                mileage=row.get("mileage"),
                title=row["title"],
                description=row.get("description", ""),
                cost_kopecks=row.get("cost_kopecks"),
                cost_visible_to_public=False,
                trust_level="declared",
                revision=1,
            ))

        for row in data.get("service_visits", []):
            cost_status = validate_cost_status(row.get("total_cost_status", "unknown"))
            visit = ServiceVisit(
                vehicle_id=vehicle.id,
                kind=validate_visit_kind(row.get("kind", "repair_visit")),
                visit_date=parse_date(row["visit_date"]),
                mileage=row.get("mileage"),
                title=row["title"],
                location=row.get("location"),
                description=row.get("description", ""),
                total_cost_kopecks=kopecks_from_rubles(row.get("total_cost_rubles")) if cost_status == "known" else None,
                total_cost_status=cost_status,
                total_cost_visible_to_public=bool(row.get("total_cost_visible_to_public", False)),
                trust_level="declared",
                revision=1,
            )
            session.add(visit)
            session.flush()
            for item_row in row.get("items", []):
                item_cost_status = validate_cost_status(item_row.get("cost_status", "unknown"))
                session.add(ServiceItem(
                    visit_id=visit.id,
                    item_type=validate_item_type(item_row.get("item_type", "operation")),
                    title=item_row["title"],
                    description=item_row.get("description", ""),
                    brand=item_row.get("brand"),
                    part_number=item_row.get("part_number"),
                    quantity=str(item_row.get("quantity")) if item_row.get("quantity") not in (None, "") else None,
                    unit=item_row.get("unit"),
                    cost_kopecks=kopecks_from_rubles(item_row.get("cost_rubles")) if item_cost_status == "known" else None,
                    cost_status=item_cost_status,
                ))
            session.flush()
            visit_audit(session, visit, user.id, "seeded", after=visit_snapshot(visit))

        session.commit()
        print(vehicle.id)


if __name__ == "__main__":
    main(sys.argv[1])
