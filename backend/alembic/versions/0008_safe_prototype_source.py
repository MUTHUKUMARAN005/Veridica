"""Persist safe generated prototype source and blocked build state."""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prototype_builds",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("idea_id", sa.String(length=36), nullable=False),
        sa.Column("idea_version_id", sa.String(length=36), nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=False),
        sa.Column("requirement_analysis_run_id", sa.String(length=36), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=36), nullable=False),
        sa.Column("template_id", sa.String(length=80), nullable=True),
        sa.Column("template_version", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("validation_status", sa.String(length=20), nullable=False),
        sa.Column(
            "build_status",
            sa.String(length=30),
            nullable=False,
            server_default="blocked_isolation",
        ),
        sa.Column(
            "publish_status",
            sa.String(length=20),
            nullable=False,
            server_default="unpublished",
        ),
        sa.Column("plan", sa.JSON(), nullable=True),
        sa.Column("manifest", sa.JSON(), nullable=True),
        sa.Column("validation_results", sa.JSON(), nullable=False),
        sa.Column("source_files", sa.JSON(), nullable=False),
        sa.Column("artifact_metadata", sa.JSON(), nullable=True),
        sa.Column("source_storage_key", sa.String(length=36), nullable=True),
        sa.Column("preview_url", sa.String(length=2048), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"]),
        sa.ForeignKeyConstraint(["idea_version_id"], ["idea_versions.id"]),
        sa.ForeignKeyConstraint(
            ["requirement_analysis_run_id"], ["requirement_analysis_runs.id"]
        ),
        sa.UniqueConstraint(
            "requirement_analysis_run_id",
            name="uq_prototype_builds_requirement_analysis_run",
        ),
        sa.UniqueConstraint("workflow_run_id", name="uq_prototype_builds_workflow_run"),
        sa.CheckConstraint("source_version >= 1", name="ck_prototype_builds_source_version"),
        sa.CheckConstraint(
            "status IN ('source_generated', 'validation_failed', "
            "'unsupported_category', 'generation_failed', 'source_missing')",
            name="ck_prototype_builds_status",
        ),
        sa.CheckConstraint(
            "validation_status IN ('passed', 'failed', 'not_run')",
            name="ck_prototype_builds_validation_status",
        ),
        sa.CheckConstraint(
            "build_status = 'blocked_isolation'",
            name="ck_prototype_builds_build_status",
        ),
        sa.CheckConstraint(
            "publish_status = 'unpublished'",
            name="ck_prototype_builds_publish_status",
        ),
    )
    op.create_index("ix_prototype_builds_idea_id", "prototype_builds", ["idea_id"])
    op.create_index(
        "ix_prototype_builds_idea_version_id",
        "prototype_builds",
        ["idea_version_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_prototype_builds_idea_version_id", table_name="prototype_builds")
    op.drop_index("ix_prototype_builds_idea_id", table_name="prototype_builds")
    op.drop_table("prototype_builds")
