"""AI verification, scoring and notifications.

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_verifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "job_id",
            sa.Integer(),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0"),
        sa.Column("role_match", sa.Boolean()),
        sa.Column("entry_level", sa.Boolean()),
        sa.Column("experience_match", sa.Boolean()),
        sa.Column("degree_match", sa.Boolean()),
        sa.Column("graduation_match", sa.Boolean()),
        sa.Column("location_match", sa.Boolean()),
        sa.Column("employment_match", sa.Boolean()),
        sa.Column("citizenship_required", sa.Boolean()),
        sa.Column("security_clearance_required", sa.Boolean()),
        sa.Column("experience_required", sa.Integer()),
        sa.Column("experience_type", sa.String(24)),
        sa.Column("education_required", sa.Text()),
        sa.Column("work_authorization_status", sa.String(32), server_default="UNKNOWN"),
        sa.Column("sponsorship_status", sa.String(32), server_default="NOT_SPECIFIED"),
        sa.Column("matched_skills", postgresql.JSONB(), server_default="[]"),
        sa.Column("missing_skills", postgresql.JSONB(), server_default="[]"),
        sa.Column("rejection_reasons", postgresql.JSONB(), server_default="[]"),
        sa.Column("ai_summary", sa.Text()),
        sa.Column("model", sa.String(128)),
        sa.Column("content_fingerprint", sa.String(64)),
        sa.Column("profile_fingerprint", sa.String(64)),
        sa.Column("verified_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_job_verifications_decision", "job_verifications", ["decision"])

    op.create_table(
        "job_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "job_id",
            sa.Integer(),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("role_score", sa.Float(), server_default="0"),
        sa.Column("experience_score", sa.Float(), server_default="0"),
        sa.Column("skill_score", sa.Float(), server_default="0"),
        sa.Column("degree_score", sa.Float(), server_default="0"),
        sa.Column("graduation_score", sa.Float(), server_default="0"),
        sa.Column("work_auth_score", sa.Float(), server_default="0"),
        sa.Column("location_score", sa.Float(), server_default="0"),
        sa.Column("salary_score", sa.Float(), server_default="0"),
        sa.Column("company_score", sa.Float(), server_default="0"),
        sa.Column("overall_score", sa.Float(), server_default="0"),
        sa.Column("classification", sa.String(24), server_default="BELOW_THRESHOLD"),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_job_scores_overall_score", "job_scores", ["overall_score"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "job_id", sa.Integer(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_notifications_job_channel", "notifications", ["job_id", "channel"])


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_index("ix_job_scores_overall_score", table_name="job_scores")
    op.drop_table("job_scores")
    op.drop_index("ix_job_verifications_decision", table_name="job_verifications")
    op.drop_table("job_verifications")
