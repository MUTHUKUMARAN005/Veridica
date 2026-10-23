"""Persist owner-approved evolution and immutable decision report snapshots."""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evolution_proposals",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("idea_id", sa.String(length=36), nullable=False),
        sa.Column("idea_version_id", sa.String(length=36), nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=False),
        sa.Column("requirement_analysis_run_id", sa.String(length=36), nullable=False),
        sa.Column("feedback_analysis_run_id", sa.String(length=36), nullable=False),
        sa.Column("source_feedback_ids", sa.JSON(), nullable=False),
        sa.Column("suggestions", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="proposed"),
        sa.Column("target_version_id", sa.String(length=36), nullable=True),
        sa.Column("prototype_build_id", sa.String(length=36), nullable=True),
        sa.Column("requested_by_id", sa.String(length=36), nullable=False),
        sa.Column("approved_by_id", sa.String(length=36), nullable=True),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model_version", sa.String(length=160), nullable=False),
        sa.Column("prompt_version", sa.String(length=80), nullable=False),
        sa.Column("validation_results", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('proposed', 'approved', 'rejected')",
            name="ck_evolution_proposals_status",
        ),
        sa.CheckConstraint("source_version >= 1", name="ck_evolution_proposals_source_version"),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"]),
        sa.ForeignKeyConstraint(["idea_version_id"], ["idea_versions.id"]),
        sa.ForeignKeyConstraint(
            ["requirement_analysis_run_id"], ["requirement_analysis_runs.id"]
        ),
        sa.ForeignKeyConstraint(["feedback_analysis_run_id"], ["feedback_analysis_runs.id"]),
        sa.ForeignKeyConstraint(["target_version_id"], ["idea_versions.id"]),
        sa.ForeignKeyConstraint(["prototype_build_id"], ["prototype_builds.id"]),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["approved_by_id"], ["users.id"]),
        sa.UniqueConstraint(
            "idea_version_id",
            "feedback_analysis_run_id",
            name="uq_evolution_proposals_version_analysis",
        ),
    )
    op.create_index("ix_evolution_proposals_idea_id", "evolution_proposals", ["idea_id"])
    op.create_index(
        "ix_evolution_proposals_idea_version_id", "evolution_proposals", ["idea_version_id"]
    )

    op.create_table(
        "decision_reports",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("idea_id", sa.String(length=36), nullable=False),
        sa.Column("idea_version_id", sa.String(length=36), nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=False),
        sa.Column("requirement_analysis_run_id", sa.String(length=36), nullable=True),
        sa.Column("feedback_analysis_run_id", sa.String(length=36), nullable=True),
        sa.Column("evolution_proposal_id", sa.String(length=36), nullable=True),
        sa.Column("source_feedback_ids", sa.JSON(), nullable=False),
        sa.Column("report_version", sa.String(length=80), nullable=False),
        sa.Column("report", sa.JSON(), nullable=False),
        sa.Column("created_by_id", sa.String(length=36), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("source_version >= 1", name="ck_decision_reports_source_version"),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"]),
        sa.ForeignKeyConstraint(["idea_version_id"], ["idea_versions.id"]),
        sa.ForeignKeyConstraint(
            ["requirement_analysis_run_id"], ["requirement_analysis_runs.id"]
        ),
        sa.ForeignKeyConstraint(["feedback_analysis_run_id"], ["feedback_analysis_runs.id"]),
        sa.ForeignKeyConstraint(["evolution_proposal_id"], ["evolution_proposals.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
    )
    op.create_index("ix_decision_reports_idea_id", "decision_reports", ["idea_id"])
    op.create_index(
        "ix_decision_reports_idea_version_id", "decision_reports", ["idea_version_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_decision_reports_idea_version_id", table_name="decision_reports")
    op.drop_index("ix_decision_reports_idea_id", table_name="decision_reports")
    op.drop_table("decision_reports")
    op.drop_index("ix_evolution_proposals_idea_version_id", table_name="evolution_proposals")
    op.drop_index("ix_evolution_proposals_idea_id", table_name="evolution_proposals")
    op.drop_table("evolution_proposals")
