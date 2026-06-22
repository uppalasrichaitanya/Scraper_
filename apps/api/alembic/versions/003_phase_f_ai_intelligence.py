"""003_phase_f_ai_intelligence

Enable pgvector extension.
Extend user_profiles with resume/embedding fields (384-dim, all-MiniLM-L6-v2).
Create job_embeddings table for hybrid search.

Revision ID: 003
Revises: 002
Create Date: 2026-06-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# pgvector provides this type; for the migration we use raw SQL
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Enable pgvector extension ─────────────────────────────────────── #
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── Extend user_profiles with resume fields ───────────────────────── #
    # All columns nullable — existing rows won't have resume data.
    # Embedding is 384-dim (all-MiniLM-L6-v2). If switching to OpenAI
    # ada-002 (1536-dim), re-create the column + re-index.
    op.add_column("user_profiles", sa.Column("current_title", sa.String(200), nullable=True))
    op.add_column("user_profiles", sa.Column("years_experience", sa.Integer(), nullable=True))
    op.add_column("user_profiles", sa.Column("skills", postgresql.ARRAY(sa.Text()), nullable=True))
    op.add_column("user_profiles", sa.Column("education", postgresql.JSONB(), nullable=True))
    op.add_column("user_profiles", sa.Column("experience", postgresql.JSONB(), nullable=True))
    op.add_column("user_profiles", sa.Column("resume_s3_key", sa.String(500), nullable=True))
    op.add_column("user_profiles", sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("user_profiles", sa.Column(
        "parse_version", sa.Integer(), nullable=True, server_default="1"
    ))
    # Vector column — raw SQL because Alembic doesn't know about vector type natively
    op.execute("ALTER TABLE user_profiles ADD COLUMN embedding vector(384)")

    # ── Create job_embeddings table ───────────────────────────────────── #
    op.create_table(
        "job_embeddings",
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("model", sa.String(50), nullable=False, server_default="all-MiniLM-L6-v2"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # Add vector column via raw SQL
    op.execute("ALTER TABLE job_embeddings ADD COLUMN embedding vector(384) NOT NULL")

    # ── IVFFlat indexes for approximate nearest-neighbor search ──────── #
    # NOTE: IVFFlat requires existing data to build lists. For an empty table,
    # the index will be rebuilt on first VACUUM or when enough rows exist.
    # Using lists=100 as a sensible default for < 100k vectors.
    op.execute("""
        CREATE INDEX idx_job_embeddings_vector
        ON job_embeddings
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_job_embeddings_vector")
    op.drop_table("job_embeddings")

    op.execute("ALTER TABLE user_profiles DROP COLUMN IF EXISTS embedding")
    op.drop_column("user_profiles", "parse_version")
    op.drop_column("user_profiles", "parsed_at")
    op.drop_column("user_profiles", "resume_s3_key")
    op.drop_column("user_profiles", "experience")
    op.drop_column("user_profiles", "education")
    op.drop_column("user_profiles", "skills")
    op.drop_column("user_profiles", "years_experience")
    op.drop_column("user_profiles", "current_title")

    op.execute("DROP EXTENSION IF EXISTS vector")
