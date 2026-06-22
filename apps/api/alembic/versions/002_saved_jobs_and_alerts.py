"""002_saved_jobs_and_alerts

Add saved_jobs and job_alerts tables.
Add last_crawled_at column to jobs (required for E5 stale detection).

Revision ID: 002
Revises: 001
Create Date: 2025-06-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    #  jobs — add last_crawled_at                                          #
    # ------------------------------------------------------------------ #
    op.add_column(
        "jobs",
        sa.Column(
            "last_crawled_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp of the most recent successful crawl for this job. "
                    "Used by the stale-job lifecycle task.",
        ),
    )
    # Backfill: treat created_at as the initial value so stale detection
    # doesn't immediately expire every existing row.
    op.execute(
        "UPDATE jobs SET last_crawled_at = created_at WHERE last_crawled_at IS NULL"
    )
    # Index for the lifecycle query (WHERE status='active' AND last_crawled_at < ?)
    op.create_index(
        "idx_jobs_last_crawled_at",
        "jobs",
        ["last_crawled_at"],
        postgresql_where=sa.text("status IN ('active', 'stale')"),
    )

    # ------------------------------------------------------------------ #
    #  saved_jobs                                                          #
    # ------------------------------------------------------------------ #
    op.create_table(
        "saved_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="saved"),
        sa.Column(
            "saved_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("user_id", "job_id", name="uq_saved_jobs_user_job"),
    )
    op.create_index("idx_saved_jobs_user_date", "saved_jobs", ["user_id", "saved_at"])
    op.create_index("idx_saved_jobs_user_status", "saved_jobs", ["user_id", "status"])

    # ------------------------------------------------------------------ #
    #  job_alerts                                                          #
    # ------------------------------------------------------------------ #
    op.create_table(
        "job_alerts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("query_params", postgresql.JSONB(), nullable=False),
        sa.Column("frequency", sa.String(10), nullable=False, server_default="daily"),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_job_ids",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("idx_alerts_user", "job_alerts", ["user_id"])
    op.create_index(
        "idx_alerts_dispatch",
        "job_alerts",
        ["is_active", "frequency", "last_sent_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_alerts_dispatch", table_name="job_alerts")
    op.drop_index("idx_alerts_user", table_name="job_alerts")
    op.drop_table("job_alerts")

    op.drop_index("idx_saved_jobs_user_status", table_name="saved_jobs")
    op.drop_index("idx_saved_jobs_user_date", table_name="saved_jobs")
    op.drop_table("saved_jobs")

    op.drop_index("idx_jobs_last_crawled_at", table_name="jobs")
    op.drop_column("jobs", "last_crawled_at")
