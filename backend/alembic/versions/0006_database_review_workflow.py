"""Add published review cycles, sessions, feedback provenance, and analysis outbox."""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_idea_status_events_transition", "idea_status_events", type_="check"
    )
    op.create_check_constraint(
        "ck_idea_status_events_transition",
        "idea_status_events",
        "from_status IS NULL OR "
        "(from_status = 'Draft' AND to_status = 'Archived') OR "
        "(from_status = 'Archived' AND to_status = 'Draft') OR "
        "(from_status = 'Draft' AND to_status = 'Review open') OR "
        "(from_status = 'Review open' AND to_status = 'Draft')",
    )

    op.create_table(
        "review_cycles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("idea_version_id", sa.String(length=36), nullable=False),
        sa.Column("opened_by_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column(
            "opened_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["idea_version_id"], ["idea_versions.id"]),
        sa.ForeignKeyConstraint(["opened_by_id"], ["users.id"]),
        sa.UniqueConstraint("idea_version_id", name="uq_review_cycles_idea_version"),
        sa.CheckConstraint("status IN ('open', 'closed')", name="ck_review_cycles_status"),
    )
    op.create_index("ix_review_cycles_idea_version_id", "review_cycles", ["idea_version_id"])

    op.add_column(
        "reviewer_assignments",
        sa.Column("review_cycle_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "reviewer_assignments",
        sa.Column("status", sa.String(length=20), nullable=False, server_default="assigned"),
    )
    op.add_column(
        "reviewer_assignments",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "reviewer_assignments",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        """
        INSERT INTO review_cycles
            (id, idea_version_id, opened_by_id, status, opened_at)
        SELECT assignment.id, assignment.idea_version_id, assignment.assigned_by_id,
               'open', assignment.assigned_at
        FROM reviewer_assignments AS assignment
        ON CONFLICT (idea_version_id) DO NOTHING
        """
    )
    op.execute(
        """
        UPDATE reviewer_assignments AS assignment
        SET review_cycle_id = cycle.id,
            status = CASE WHEN assignment.active THEN 'assigned' ELSE 'revoked' END
        FROM review_cycles AS cycle
        WHERE cycle.idea_version_id = assignment.idea_version_id
        """
    )
    op.create_foreign_key(
        "fk_reviewer_assignments_review_cycle_id_review_cycles",
        "reviewer_assignments",
        "review_cycles",
        ["review_cycle_id"],
        ["id"],
    )
    op.alter_column("reviewer_assignments", "review_cycle_id", nullable=False)
    op.create_check_constraint(
        "ck_reviewer_assignments_status",
        "reviewer_assignments",
        "status IN ('assigned', 'in_progress', 'submitted', 'revoked')",
    )
    op.create_check_constraint(
        "ck_reviewer_assignments_active_status",
        "reviewer_assignments",
        "(active AND status != 'revoked') OR (NOT active AND status = 'revoked')",
    )

    op.create_table(
        "review_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("assignment_id", sa.String(length=36), nullable=False),
        sa.Column("idea_id", sa.String(length=36), nullable=False),
        sa.Column("idea_version_id", sa.String(length=36), nullable=False),
        sa.Column("reviewer_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="in_progress"),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["assignment_id"], ["reviewer_assignments.id"]),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"]),
        sa.ForeignKeyConstraint(["idea_version_id"], ["idea_versions.id"]),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"]),
        sa.UniqueConstraint("assignment_id", name="uq_review_sessions_assignment"),
        sa.CheckConstraint(
            "status IN ('in_progress', 'submitted')", name="ck_review_sessions_status"
        ),
    )
    op.execute(
        """
        INSERT INTO review_sessions
            (id, assignment_id, idea_id, idea_version_id, reviewer_id, status,
             started_at, completed_at)
        SELECT review.assignment_id, assignment.id, version.idea_id, version.id,
               assignment.reviewer_id, 'submitted', review.created_at, review.created_at
        FROM idea_reviews AS review
        JOIN reviewer_assignments AS assignment ON assignment.id = review.assignment_id
        JOIN idea_versions AS version ON version.id = assignment.idea_version_id
        """
    )
    op.execute(
        """
        UPDATE reviewer_assignments AS assignment
        SET status = 'submitted',
            started_at = session.started_at,
            completed_at = session.completed_at
        FROM review_sessions AS session
        WHERE session.assignment_id = assignment.id
        """
    )

    op.add_column(
        "idea_reviews", sa.Column("idea_id", sa.String(length=36), nullable=True)
    )
    op.add_column(
        "idea_reviews", sa.Column("idea_version_id", sa.String(length=36), nullable=True)
    )
    op.add_column(
        "idea_reviews", sa.Column("reviewer_id", sa.String(length=36), nullable=True)
    )
    op.add_column(
        "idea_reviews", sa.Column("review_session_id", sa.String(length=36), nullable=True)
    )
    op.add_column(
        "idea_reviews", sa.Column("idempotency_key", sa.String(length=128), nullable=True)
    )
    for column in (
        "usability_score",
        "usefulness_score",
        "completeness_score",
        "feasibility_score",
    ):
        op.add_column("idea_reviews", sa.Column(column, sa.Integer(), nullable=True))
    op.add_column("idea_reviews", sa.Column("would_use", sa.Boolean(), nullable=True))
    for column in ("strengths", "concerns", "suggested_improvements", "usage_context"):
        op.add_column("idea_reviews", sa.Column(column, sa.Text(), nullable=True))

    op.execute(
        """
        UPDATE idea_reviews AS review
        SET idea_id = version.idea_id,
            idea_version_id = version.id,
            reviewer_id = assignment.reviewer_id,
            review_session_id = session.id,
            idempotency_key = 'legacy:' || review.assignment_id
        FROM reviewer_assignments AS assignment
        JOIN idea_versions AS version ON version.id = assignment.idea_version_id
        JOIN review_sessions AS session ON session.assignment_id = assignment.id
        WHERE review.assignment_id = assignment.id
        """
    )
    op.alter_column("idea_reviews", "idea_id", nullable=False)
    op.alter_column("idea_reviews", "idea_version_id", nullable=False)
    op.alter_column("idea_reviews", "reviewer_id", nullable=False)
    op.alter_column("idea_reviews", "review_session_id", nullable=False)
    op.alter_column("idea_reviews", "idempotency_key", nullable=False)
    op.create_foreign_key(
        "fk_idea_reviews_idea_id_ideas", "idea_reviews", "ideas", ["idea_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_idea_reviews_idea_version_id_idea_versions",
        "idea_reviews",
        "idea_versions",
        ["idea_version_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_idea_reviews_reviewer_id_users",
        "idea_reviews",
        "users",
        ["reviewer_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_idea_reviews_review_session_id_review_sessions",
        "idea_reviews",
        "review_sessions",
        ["review_session_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_idea_reviews_assignment_idempotency",
        "idea_reviews",
        ["assignment_id", "idempotency_key"],
    )
    op.create_check_constraint(
        "ck_idea_reviews_usability_score",
        "idea_reviews",
        "usability_score IS NULL OR usability_score BETWEEN 1 AND 5",
    )
    op.create_check_constraint(
        "ck_idea_reviews_usefulness_score",
        "idea_reviews",
        "usefulness_score IS NULL OR usefulness_score BETWEEN 1 AND 5",
    )
    op.create_check_constraint(
        "ck_idea_reviews_completeness_score",
        "idea_reviews",
        "completeness_score IS NULL OR completeness_score BETWEEN 1 AND 5",
    )
    op.create_check_constraint(
        "ck_idea_reviews_feasibility_score",
        "idea_reviews",
        "feasibility_score IS NULL OR feasibility_score BETWEEN 1 AND 5",
    )

    op.create_table(
        "feedback_analysis_outbox",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("feedback_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["feedback_id"], ["idea_reviews.id"]),
        sa.UniqueConstraint("feedback_id", name="uq_feedback_analysis_outbox_feedback"),
        sa.CheckConstraint(
            "status IN ('pending', 'queued', 'received')",
            name="ck_feedback_analysis_outbox_status",
        ),
    )


def downgrade() -> None:
    op.drop_table("feedback_analysis_outbox")
    for name in (
        "ck_idea_reviews_feasibility_score",
        "ck_idea_reviews_completeness_score",
        "ck_idea_reviews_usefulness_score",
        "ck_idea_reviews_usability_score",
    ):
        op.drop_constraint(name, "idea_reviews", type_="check")
    op.drop_constraint(
        "uq_idea_reviews_assignment_idempotency", "idea_reviews", type_="unique"
    )
    for name in (
        "fk_idea_reviews_review_session_id_review_sessions",
        "fk_idea_reviews_reviewer_id_users",
        "fk_idea_reviews_idea_version_id_idea_versions",
        "fk_idea_reviews_idea_id_ideas",
    ):
        op.drop_constraint(name, "idea_reviews", type_="foreignkey")
    for column in (
        "usage_context",
        "suggested_improvements",
        "concerns",
        "strengths",
        "would_use",
        "feasibility_score",
        "completeness_score",
        "usefulness_score",
        "usability_score",
        "idempotency_key",
        "review_session_id",
        "reviewer_id",
        "idea_version_id",
        "idea_id",
    ):
        op.drop_column("idea_reviews", column)
    op.drop_table("review_sessions")
    op.drop_constraint(
        "ck_reviewer_assignments_active_status", "reviewer_assignments", type_="check"
    )
    op.drop_constraint(
        "ck_reviewer_assignments_status", "reviewer_assignments", type_="check"
    )
    op.drop_constraint(
        "fk_reviewer_assignments_review_cycle_id_review_cycles",
        "reviewer_assignments",
        type_="foreignkey",
    )
    for column in ("completed_at", "started_at", "status", "review_cycle_id"):
        op.drop_column("reviewer_assignments", column)
    op.drop_index("ix_review_cycles_idea_version_id", table_name="review_cycles")
    op.drop_table("review_cycles")
    op.drop_constraint(
        "ck_idea_status_events_transition", "idea_status_events", type_="check"
    )
    op.create_check_constraint(
        "ck_idea_status_events_transition",
        "idea_status_events",
        "from_status IS NULL OR "
        "(from_status = 'Draft' AND to_status = 'Archived') OR "
        "(from_status = 'Archived' AND to_status = 'Draft')",
    )
