from __future__ import annotations

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect


def test_document_ai_draft_model_is_registered_with_review_boundary():
    from app.database import Base
    from app.models import DocumentAIDraft

    table = Base.metadata.tables["document_ai_drafts"]
    assert DocumentAIDraft.__tablename__ == "document_ai_drafts"
    assert set(table.columns) == {
        "id",
        "document_id",
        "owner_id",
        "vehicle_id",
        "extracted_text",
        "proposed_fields_json",
        "confidence_json",
        "parser_name",
        "parser_version",
        "status",
        "created_at",
        "updated_at",
    }
    assert table.c.document_id.unique is True
    assert table.c.status.default.arg == "needs_review"
    assert table.c.proposed_fields_json.default.arg == "{}"
    assert table.c.confidence_json.default.arg == "{}"


def test_document_ai_draft_foreign_keys_are_owner_scoped_and_document_bound():
    from app.database import Base

    table = Base.metadata.tables["document_ai_drafts"]
    targets = {
        foreign_key.parent.name: foreign_key.target_fullname
        for foreign_key in table.foreign_keys
    }
    assert targets == {
        "document_id": "document_inbox.id",
        "owner_id": "users.id",
        "vehicle_id": "vehicles.id",
    }


def test_document_ai_draft_migration_is_current_head():
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)
    assert script.get_current_head() == "0005_document_ai_drafts"


def test_document_ai_draft_migration_creates_expected_schema(tmp_path, monkeypatch):
    database_path = tmp_path / "draft-schema.db"
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)

    from alembic import command

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")

    from sqlalchemy import create_engine

    engine = create_engine(database_url)
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("document_ai_drafts")}
    assert columns == {
        "id",
        "document_id",
        "owner_id",
        "vehicle_id",
        "extracted_text",
        "proposed_fields_json",
        "confidence_json",
        "parser_name",
        "parser_version",
        "status",
        "created_at",
        "updated_at",
    }
    unique_constraints = inspector.get_unique_constraints("document_ai_drafts")
    indexes = inspector.get_indexes("document_ai_drafts")
    assert any("document_id" in constraint.get("column_names", []) for constraint in unique_constraints) or any(
        index.get("unique") and index.get("column_names") == ["document_id"] for index in indexes
    )
    engine.dispose()
