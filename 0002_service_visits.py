from alembic import op
import sqlalchemy as sa

revision = "0002_service_visits"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "service_visits",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("vehicle_id", sa.String(36), sa.ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False, server_default="repair_visit"),
        sa.Column("visit_date", sa.Date(), nullable=False),
        sa.Column("mileage", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("total_cost_kopecks", sa.Integer(), nullable=True),
        sa.Column("total_cost_status", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("total_cost_visible_to_public", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("trust_level", sa.String(32), nullable=False, server_default="declared"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "service_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("visit_id", sa.String(36), sa.ForeignKey("service_visits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_type", sa.String(32), nullable=False, server_default="operation"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("brand", sa.String(120), nullable=True),
        sa.Column("part_number", sa.String(120), nullable=True),
        sa.Column("quantity", sa.String(64), nullable=True),
        sa.Column("unit", sa.String(32), nullable=True),
        sa.Column("cost_kopecks", sa.Integer(), nullable=True),
        sa.Column("cost_status", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "visit_audits",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("visit_id", sa.String(36), nullable=False),
        sa.Column("actor_user_id", sa.String(36), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("before_json", sa.Text(), nullable=True),
        sa.Column("after_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    with op.batch_alter_table("attachments") as batch:
        batch.add_column(sa.Column("visit_id", sa.String(36), nullable=True))
        batch.alter_column("event_id", existing_type=sa.String(36), nullable=True)


def downgrade():
    with op.batch_alter_table("attachments") as batch:
        batch.alter_column("event_id", existing_type=sa.String(36), nullable=False)
        batch.drop_column("visit_id")
    op.drop_table("visit_audits")
    op.drop_table("service_items")
    op.drop_table("service_visits")
