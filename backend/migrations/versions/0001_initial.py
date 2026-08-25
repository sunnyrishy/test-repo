"""Initial schema: jobs, job_sources, discovery_runs, candidate_profile.

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("company", sa.String(255), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("location", sa.String(512)),
        sa.Column("country", sa.String(8)),
        sa.Column("workplace_type", sa.String(32)),
        sa.Column("employment_type", sa.String(32)),
        sa.Column("description", sa.Text()),
        sa.Column("application_url", sa.Text()),
        sa.Column("source_url", sa.Text()),
        sa.Column("posted_at", sa.DateTime(timezone=True)),
        sa.Column("source_updated_at", sa.DateTime(timezone=True)),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_verified_at", sa.DateTime(timezone=True)),
        sa.Column("freshness_status", sa.String(16), server_default="UNKNOWN"),
        sa.Column("salary_min", sa.BigInteger()),
        sa.Column("salary_max", sa.BigInteger()),
        sa.Column("currency", sa.String(8)),
        sa.Column("fingerprint", sa.String(128)),
        sa.Column("canonical_job_id", sa.Integer(), sa.ForeignKey("jobs.id", ondelete="SET NULL")),
        sa.Column("filter_status", sa.String(16), server_default="PENDING"),
        sa.Column("filter_rejection_reason", sa.String(64)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("status", sa.String(16), server_default="NEW"),
        sa.Column("status_changed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("source", "external_id", name="uq_jobs_source_external_id"),
    )
    op.create_index("ix_jobs_fingerprint", "jobs", ["fingerprint"])
    op.create_index("ix_jobs_posted_at", "jobs", ["posted_at"])

    op.create_table(
        "job_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_job_id", sa.String(255), nullable=False),
        sa.Column("source_url", sa.Text()),
        sa.Column("application_url", sa.Text()),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("source", "source_job_id", name="uq_job_sources_source_job"),
    )

    op.create_table(
        "discovery_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("discovered", sa.Integer(), server_default="0"),
        sa.Column("duplicates", sa.Integer(), server_default="0"),
        sa.Column("stored", sa.Integer(), server_default="0"),
        sa.Column("hard_filter_failures", sa.Integer(), server_default="0"),
        sa.Column("passed_filters", sa.Integer(), server_default="0"),
        sa.Column("per_source", sa.Text()),
        sa.Column("errors", sa.Text()),
    )

    op.create_table(
        "candidate_profile",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("profile_json", postgresql.JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("candidate_profile")
    op.drop_table("discovery_runs")
    op.drop_table("job_sources")
    op.drop_index("ix_jobs_posted_at", table_name="jobs")
    op.drop_index("ix_jobs_fingerprint", table_name="jobs")
    op.drop_table("jobs")
