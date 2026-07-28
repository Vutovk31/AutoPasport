from alembic import op
import sqlalchemy as sa

revision = "0004_document_inbox"
down_revision = "0003_attachment_retention"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "document_inbox",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vehicle_id", sa.String(36), sa.ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("linked_visit_id", sa.String(36), sa.ForeignKey("service_visits.id", ondelete="SET NULL"), nullable=True),
        sa.Column("document_type", sa.String(32), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("stored_name", sa.String(255), nullable=False, unique=True),
        sa.Column("media_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="uploaded"),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_document_inbox_owner_id", "document_inbox", ["owner_id"])
    op.create_index("ix_document_inbox_vehicle_id", "document_inbox", ["vehicle_id"])
    op.create_index("ix_document_inbox_linked_visit_id", "document_inbox", ["linked_visit_id"])
    op.create_index("ix_document_inbox_sha256", "document_inbox", ["sha256"])
    op.create_index("ix_document_inbox_status", "document_inbox", ["status"])


def downgrade():
    op.drop_index("ix_document_inbox_status", table_name="document_inbox")
    op.drop_index("ix_document_inbox_sha256", table_name="document_inbox")
    op.drop_index("ix_document_inbox_linked_visit_id", table_name="document_inbox")
    op.drop_index("ix_document_inbox_vehicle_id", table_name="document_inbox")
    op.drop_index("ix_document_inbox_owner_id", table_name="document_inbox")
    op.drop_table("document_inbox")
