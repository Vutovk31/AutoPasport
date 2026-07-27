from alembic import op
import sqlalchemy as sa

revision = "0003_attachment_retention"
down_revision = "0002_service_visits"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("attachments") as batch:
        batch.add_column(sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("purge_reason", sa.String(64), nullable=True))


def downgrade():
    with op.batch_alter_table("attachments") as batch:
        batch.drop_column("purge_reason")
        batch.drop_column("purged_at")
