"""Persist Requirement Agent workflow runs and validated outputs."""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "requirement_analysis_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("idea_id", sa.String(length=36), nullable=False),
        sa.Column("idea_version_id", sa.String(length=36), nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=False),
        sa.Column("requested_by_id", sa.String(length=36), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model_version", sa.String(length=160), nullable=False),
        sa.Column("prompt_version", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column(
            "validation_status", sa.String(length=20), nullable=False, server_default="pending"
        ),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"]),
        sa.ForeignKeyConstraint(["idea_version_id"], ["idea_versions.id"]),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"]),
        sa.UniqueConstraint("workflow_run_id", name="uq_requirement_analysis_runs_workflow"),
        sa.CheckConstraint("source_version >= 1", name="ck_requirement_analysis_runs_version"),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed')",
            name="ck_requirement_analysis_runs_status",
        ),
        sa.CheckConstraint(
            "validation_status IN ('pending', 'valid', 'invalid', 'not_run')",
            name="ck_requirement_analysis_runs_validation_status",
        ),
        sa.CheckConstraint("attempt_count >= 0", name="ck_requirement_analysis_runs_attempts"),
    )
    op.create_index(
        "ix_requirement_analysis_runs_idea_id",
        "requirement_analysis_runs",
        ["idea_id"],
    )
    op.create_index(
        "ix_requirement_analysis_runs_idea_version_id",
        "requirement_analysis_runs",
        ["idea_version_id"],
    )
    op.create_index(
        "ix_requirement_analysis_runs_status_created",
        "requirement_analysis_runs",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_requirement_analysis_runs_status_created", table_name="requirement_analysis_runs"
    )
    op.drop_index(
        "ix_requirement_analysis_runs_idea_version_id", table_name="requirement_analysis_runs"
    )
    op.drop_index("ix_requirement_analysis_runs_idea_id", table_name="requirement_analysis_runs")
    op.drop_table("requirement_analysis_runs")
