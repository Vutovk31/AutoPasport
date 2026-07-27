from datetime import date, datetime
from uuid import uuid4
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

def uid(): return str(uuid4())

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)

class SessionToken(Base):
    __tablename__ = "session_tokens"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class Vehicle(Base):
    __tablename__ = "vehicles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    vin: Mapped[str] = mapped_column(String(17), unique=True, index=True)
    registration_number: Mapped[str | None] = mapped_column(String(16), nullable=True)
    make: Mapped[str] = mapped_column(String(80))
    model: Mapped[str] = mapped_column(String(80))
    trim: Mapped[str | None] = mapped_column(String(120), nullable=True)
    year: Mapped[int] = mapped_column(Integer)
    current_mileage: Mapped[int] = mapped_column(Integer)
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    purchase_mileage: Mapped[int | None] = mapped_column(Integer, nullable=True)

class HistoryEvent(Base):
    __tablename__ = "history_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    event_date: Mapped[date] = mapped_column(Date)
    mileage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    cost_kopecks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_visible_to_public: Mapped[bool] = mapped_column(Boolean, default=False)
    trust_level: Mapped[str] = mapped_column(String(32), default="declared")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class ServiceVisit(Base):
    __tablename__ = "service_visits"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(32), default="repair_visit")
    visit_date: Mapped[date] = mapped_column(Date)
    mileage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    total_cost_kopecks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_cost_status: Mapped[str] = mapped_column(String(32), default="unknown")
    total_cost_visible_to_public: Mapped[bool] = mapped_column(Boolean, default=False)
    trust_level: Mapped[str] = mapped_column(String(32), default="declared")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class ServiceItem(Base):
    __tablename__ = "service_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    visit_id: Mapped[str] = mapped_column(ForeignKey("service_visits.id", ondelete="CASCADE"), index=True)
    item_type: Mapped[str] = mapped_column(String(32), default="operation")
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    brand: Mapped[str | None] = mapped_column(String(120), nullable=True)
    part_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    quantity: Mapped[str | None] = mapped_column(String(64), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cost_kopecks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_status: Mapped[str] = mapped_column(String(32), default="unknown")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Attachment(Base):
    __tablename__ = "attachments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_id: Mapped[str | None] = mapped_column(ForeignKey("history_events.id", ondelete="CASCADE"), index=True, nullable=True)
    visit_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    original_name: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(255), unique=True)
    media_type: Mapped[str] = mapped_column(String(100))
    evidence_type: Mapped[str] = mapped_column(String(32))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class EventAudit(Base):
    __tablename__ = "event_audits"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_id: Mapped[str] = mapped_column(String(36), index=True)
    actor_user_id: Mapped[str] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(32))
    revision: Mapped[int] = mapped_column(Integer)
    before_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class VisitAudit(Base):
    __tablename__ = "visit_audits"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    visit_id: Mapped[str] = mapped_column(String(36), index=True)
    actor_user_id: Mapped[str] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(32))
    revision: Mapped[int] = mapped_column(Integer)
    before_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class ShareLink(Base):
    __tablename__ = "share_links"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
