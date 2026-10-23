"""Add append-only audit history for idea lifecycle transitions."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "idea_status_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("idea_id", sa.String(length=36), nullable=False),
        sa.Column("changed_by_id", sa.String(length=36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=40), nullable=True),
        sa.Column("to_status", sa.String(length=40), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["idea_id"], ["ideas.id"]),
        sa.ForeignKeyConstraint(["changed_by_id"], ["users.id"]),
        sa.UniqueConstraint("idea_id", "sequence", name="uq_idea_status_events_idea_sequence"),
        sa.CheckConstraint("sequence >= 1", name="ck_idea_status_events_sequence_positive"),
        sa.CheckConstraint(
            "to_status IN ('Draft', 'Ready for review', 'Review open', "
            "'Evolution ready', 'Archived')",
            name="ck_idea_status_events_to_status",
        ),
        sa.CheckConstraint(
            "from_status IS NULL OR "
            "(from_status = 'Draft' AND to_status = 'Archived') OR "
            "(from_status = 'Archived' AND to_status = 'Draft')",
            name="ck_idea_status_events_transition",
        ),
    )
    op.create_index(
        "ix_idea_status_events_idea_id", "idea_status_events", ["idea_id"]
    )
    op.execute(
        """
        INSERT INTO idea_status_events
            (id, idea_id, changed_by_id, sequence, from_status, to_status, created_at)
        SELECT idea.id, idea.id, idea.owner_id, 1, NULL, idea.status, idea.created_at
        FROM ideas AS idea
        """
    )
    op.execute(
        """
        CREATE FUNCTION reject_idea_status_event_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Idea status history is append-only.';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_idea_status_events_immutable
        BEFORE UPDATE OR DELETE ON idea_status_events
        FOR EACH ROW EXECUTE FUNCTION reject_idea_status_event_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_idea_status_events_immutable ON idea_status_events")
    op.execute("DROP FUNCTION reject_idea_status_event_mutation()")
    op.drop_index("ix_idea_status_events_idea_id", table_name="idea_status_events")
    op.drop_table("idea_status_events")
