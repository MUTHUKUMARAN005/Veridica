"""Add local authentication and immutable idea versions."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=256), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="owner"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "ideas",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("owner_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="Draft"),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_ideas_owner_id", "ideas", ["owner_id"])
    op.create_table(
        "idea_versions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("idea_id", sa.String(length=36), sa.ForeignKey("ideas.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("problem", sa.Text(), nullable=False),
        sa.Column("solution", sa.Text(), nullable=False),
        sa.Column("audience", sa.Text(), nullable=False),
        sa.Column("features", sa.Text(), nullable=False),
        sa.Column("constraints", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("idea_id", "version"),
    )
    op.create_index("ix_idea_versions_idea_id", "idea_versions", ["idea_id"])


def downgrade() -> None:
    op.drop_index("ix_idea_versions_idea_id", table_name="idea_versions")
    op.drop_table("idea_versions")
    op.drop_index("ix_ideas_owner_id", table_name="ideas")
    op.drop_table("ideas")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
