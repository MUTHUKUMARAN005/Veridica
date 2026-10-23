"""Persist an append-only audit trail for operator-managed role changes."""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "role_change_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("target_user_id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=False),
        sa.Column("previous_role", sa.String(length=20), nullable=False),
        sa.Column("new_role", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "previous_role IN ('owner', 'reviewer', 'admin')",
            name="ck_role_change_events_previous_role",
        ),
        sa.CheckConstraint(
            "new_role IN ('owner', 'reviewer', 'admin')",
            name="ck_role_change_events_new_role",
        ),
        sa.CheckConstraint(
            "previous_role <> new_role",
            name="ck_role_change_events_role_changed",
        ),
        sa.CheckConstraint(
            "length(trim(reason)) > 0",
            name="ck_role_change_events_reason_nonempty",
        ),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
    )
    op.create_index(
        "ix_role_change_events_target_user_id",
        "role_change_events",
        ["target_user_id"],
    )
    op.create_index(
        "ix_role_change_events_actor_user_id",
        "role_change_events",
        ["actor_user_id"],
    )
    op.execute(
        """
        CREATE FUNCTION reject_role_change_event_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Role change audit history is append-only.';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_role_change_events_immutable
        BEFORE UPDATE OR DELETE ON role_change_events
        FOR EACH ROW EXECUTE FUNCTION reject_role_change_event_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_role_change_events_immutable ON role_change_events")
    op.execute("DROP FUNCTION reject_role_change_event_mutation()")
    op.drop_index("ix_role_change_events_actor_user_id", table_name="role_change_events")
    op.drop_index("ix_role_change_events_target_user_id", table_name="role_change_events")
    op.drop_table("role_change_events")
