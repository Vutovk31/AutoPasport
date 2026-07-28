from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect

from app.database import Base
from app.models import DocumentInboxDocument


def test_document_inbox_model_is_registered_with_required_columns():
    table = DocumentInboxDocument.__table__
    assert table.name == "document_inbox"
    assert set(table.columns) >= {
        "id",
        "owner_id",
        "vehicle_id",
        "linked_visit_id",
        "document_type",
        "original_name",
        "stored_name",
        "media_type",
        "size_bytes",
        "sha256",
        "status",
        "failure_reason",
        "created_at",
        "updated_at",
    }
    assert table.metadata is Base.metadata
    assert table.c.status.default.arg == "uploaded"
    assert table.c.linked_visit_id.nullable is True


def test_document_inbox_foreign_keys_are_explicit():
    table = DocumentInboxDocument.__table__
    targets = {
        fk.target_fullname
        for column in table.columns
        for fk in column.foreign_keys
    }
    assert targets == {"users.id", "vehicles.id", "service_visits.id"}


def test_document_inbox_migration_is_current_head():
    config = Config(str(Path("alembic.ini")))
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_current_head() == "0004_document_inbox"
