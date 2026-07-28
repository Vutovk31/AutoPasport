from alembic import op
import sqlalchemy as sa

revision = "0005_document_ai_drafts"
down_revision = "0004_document_inbox"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "document_ai_drafts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(36),
            sa.ForeignKey("document_inbox.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "owner_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "vehicle_id",
            sa.String(36),
            sa.ForeignKey("vehicles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("extracted_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("proposed_fields_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("confidence_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("parser_name", sa.String(80), nullable=False),
        sa.Column("parser_version", sa.String(40), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="needs_review"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_document_ai_drafts_document_id", "document_ai_drafts", ["document_id"], unique=True)
    op.create_index("ix_document_ai_drafts_owner_id", "document_ai_drafts", ["owner_id"])
    op.create_index("ix_document_ai_drafts_vehicle_id", "document_ai_drafts", ["vehicle_id"])
    op.create_index("ix_document_ai_drafts_status", "document_ai_drafts", ["status"])


def downgrade():
    op.drop_index("ix_document_ai_drafts_status", table_name="document_ai_drafts")
    op.drop_index("ix_document_ai_drafts_vehicle_id", table_name="document_ai_drafts")
    op.drop_index("ix_document_ai_drafts_owner_id", table_name="document_ai_drafts")
    op.drop_index("ix_document_ai_drafts_document_id", table_name="document_ai_drafts")
    op.drop_table("document_ai_drafts")
