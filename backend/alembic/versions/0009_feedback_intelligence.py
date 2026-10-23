"""Persist version-scoped feedback analysis and pgvector embeddings."""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feedback_analysis_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("idea_id", sa.String(length=36), nullable=False),
        sa.Column("idea_version_id", sa.String(length=36), nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=False),
        sa.Column("requested_by_id", sa.String(length=36), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=36), nullable=False),
        sa.Column("input_digest", sa.String(length=64), nullable=False),
        sa.Column("source_feedback_ids", sa.JSON(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model_version", sa.String(length=160), nullable=False),
        sa.Column("embedding_model_version", sa.String(length=160), nullable=False),
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
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"]),
        sa.ForeignKeyConstraint(["idea_version_id"], ["idea_versions.id"]),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"]),
        sa.UniqueConstraint("workflow_run_id", name="uq_feedback_analysis_runs_workflow_run"),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed')",
            name="ck_feedback_analysis_runs_status",
        ),
        sa.CheckConstraint(
            "validation_status IN ('pending', 'valid', 'invalid', 'not_run')",
            name="ck_feedback_analysis_runs_validation_status",
        ),
        sa.CheckConstraint("attempt_count >= 0", name="ck_feedback_analysis_runs_attempts"),
        sa.CheckConstraint("source_version >= 1", name="ck_feedback_analysis_runs_source_version"),
    )
    op.create_index("ix_feedback_analysis_runs_idea_id", "feedback_analysis_runs", ["idea_id"])
    op.create_index(
        "ix_feedback_analysis_runs_idea_version_id",
        "feedback_analysis_runs",
        ["idea_version_id"],
    )
    op.create_table(
        "feedback_embeddings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("feedback_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model_version", sa.String(length=160), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("embedding", Vector(768), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["feedback_id"], ["idea_reviews.id"]),
        sa.UniqueConstraint(
            "feedback_id", "model_version", name="uq_feedback_embeddings_feedback_model"
        ),
        sa.CheckConstraint("dimension = 768", name="ck_feedback_embeddings_dimension"),
    )
    op.create_index("ix_feedback_embeddings_feedback_id", "feedback_embeddings", ["feedback_id"])


def downgrade() -> None:
    op.drop_index("ix_feedback_embeddings_feedback_id", table_name="feedback_embeddings")
    op.drop_table("feedback_embeddings")
    op.drop_index(
        "ix_feedback_analysis_runs_idea_version_id",
        table_name="feedback_analysis_runs",
    )
    op.drop_index("ix_feedback_analysis_runs_idea_id", table_name="feedback_analysis_runs")
    op.drop_table("feedback_analysis_runs")
