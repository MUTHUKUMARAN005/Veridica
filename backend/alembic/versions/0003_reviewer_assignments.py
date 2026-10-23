"""Add role constraints, reviewer assignments, and version-bound reviews."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    invalid_roles = connection.scalar(
        sa.text("SELECT count(*) FROM users WHERE role NOT IN ('owner', 'reviewer', 'admin')")
    )
    if invalid_roles:
        raise RuntimeError("Cannot constrain user roles while unsupported roles exist.")

    op.create_check_constraint(
        "ck_users_role", "users", "role IN ('owner', 'reviewer', 'admin')"
    )
    op.create_table(
        "reviewer_assignments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "idea_version_id",
            sa.String(length=36),
            sa.ForeignKey("idea_versions.id"),
            nullable=False,
        ),
        sa.Column("reviewer_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "assigned_by_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_id", sa.String(length=36), sa.ForeignKey("users.id")),
        sa.UniqueConstraint(
            "idea_version_id", "reviewer_id", name="uq_reviewer_assignments_version_reviewer"
        ),
    )
    op.create_index(
        "ix_reviewer_assignments_reviewer_active",
        "reviewer_assignments",
        ["reviewer_id", "active"],
    )
    op.create_table(
        "idea_reviews",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "assignment_id",
            sa.String(length=36),
            sa.ForeignKey("reviewer_assignments.id"),
            nullable=False,
        ),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_idea_reviews_rating"),
        sa.UniqueConstraint("assignment_id", name="uq_idea_reviews_assignment"),
    )


def downgrade() -> None:
    op.drop_table("idea_reviews")
    op.drop_index(
        "ix_reviewer_assignments_reviewer_active", table_name="reviewer_assignments"
    )
    op.drop_table("reviewer_assignments")
    op.drop_constraint("ck_users_role", "users", type_="check")
