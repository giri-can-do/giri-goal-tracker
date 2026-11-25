from alembic import op
import sqlalchemy as sa

revision = "b742a9d3e601"
down_revision = "82cbe2b13c37"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "activity_target_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("activity_id", sa.Integer(), sa.ForeignKey("activities.id"), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("frequency", sa.String(30), nullable=False),
        sa.Column("measurement_type", sa.String(30), nullable=False),
        sa.Column("target_value", sa.Float()),
        sa.Column("unit", sa.String(30)),
        sa.UniqueConstraint("activity_id", "effective_from", name="uq_activity_target_date"),
    )
    op.execute("""
        INSERT INTO activity_target_versions
            (activity_id, effective_from, frequency, measurement_type, target_value, unit)
        SELECT id, start_date, frequency, measurement_type, target_value, unit
        FROM activities
    """)


def downgrade():
    op.drop_table("activity_target_versions")
