"""Add immutable idea lineage, lifecycle constraints, and private asset metadata."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    unsupported_statuses = connection.execute(
        sa.text(
            "SELECT DISTINCT status FROM ideas "
            "WHERE status NOT IN "
            "('Draft', 'Ready for review', 'Review open', 'Evolution ready', 'Archived')"
        )
    ).scalars().all()
    if unsupported_statuses:
        raise RuntimeError(
            "Cannot constrain idea lifecycle while unsupported statuses exist."
        )

    op.add_column(
        "idea_versions",
        sa.Column("created_by_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "idea_versions",
        sa.Column("source_version_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "idea_versions",
        sa.Column("change_summary", sa.Text(), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE idea_versions AS version SET created_by_id = idea.owner_id "
            "FROM ideas AS idea WHERE version.idea_id = idea.id"
        )
    )
    op.execute(
        sa.text(
            "UPDATE idea_versions AS version SET source_version_id = previous.id "
            "FROM idea_versions AS previous "
            "WHERE version.idea_id = previous.idea_id "
            "AND version.version = previous.version + 1"
        )
    )
    op.execute(
        sa.text(
            "UPDATE idea_versions SET change_summary = CASE WHEN version = 1 "
            "THEN 'Initial idea submission' "
            "ELSE 'Migrated existing version history' END"
        )
    )
    op.alter_column("idea_versions", "created_by_id", nullable=False)
    op.alter_column("idea_versions", "change_summary", nullable=False)
    op.create_foreign_key(
        "fk_idea_versions_created_by_id_users",
        "idea_versions",
        "users",
        ["created_by_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_idea_versions_source_version_id_idea_versions",
        "idea_versions",
        "idea_versions",
        ["source_version_id"],
        ["id"],
    )
    op.alter_column(
        "idea_versions",
        "features",
        existing_type=sa.Text(),
        type_=sa.JSON(),
        existing_nullable=False,
        postgresql_using="to_json(string_to_array(features, '|'))",
    )
    op.create_check_constraint(
        "ck_idea_versions_version_positive", "idea_versions", "version >= 1"
    )
    op.create_check_constraint(
        "ck_ideas_current_version_positive", "ideas", "current_version >= 1"
    )
    op.create_check_constraint(
        "ck_ideas_status",
        "ideas",
        "status IN ('Draft', 'Ready for review', 'Review open', 'Evolution ready', 'Archived')",
    )

    op.create_table(
        "idea_assets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("idea_version_id", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["idea_version_id"], ["idea_versions.id"]),
        sa.UniqueConstraint("storage_key", name="uq_idea_assets_storage_key"),
        sa.CheckConstraint(
            "size_bytes > 0 AND size_bytes <= 10485760", name="ck_idea_assets_size"
        ),
        sa.CheckConstraint(
            "content_type IN ('application/pdf', 'image/png', 'image/jpeg')",
            name="ck_idea_assets_content_type",
        ),
    )
    op.create_index("ix_idea_assets_idea_version_id", "idea_assets", ["idea_version_id"])
    op.execute(
        """
        CREATE FUNCTION reject_idea_version_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Idea versions are immutable; create a new version.';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_idea_versions_immutable
        BEFORE UPDATE OR DELETE ON idea_versions
        FOR EACH ROW EXECUTE FUNCTION reject_idea_version_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_idea_versions_immutable ON idea_versions")
    op.execute("DROP FUNCTION reject_idea_version_mutation()")
    op.drop_index("ix_idea_assets_idea_version_id", table_name="idea_assets")
    op.drop_table("idea_assets")
    op.drop_constraint("ck_ideas_status", "ideas", type_="check")
    op.drop_constraint("ck_ideas_current_version_positive", "ideas", type_="check")
    op.drop_constraint(
        "ck_idea_versions_version_positive", "idea_versions", type_="check"
    )
    op.add_column("idea_versions", sa.Column("features_text", sa.Text(), nullable=True))
    op.execute(
        """
        UPDATE idea_versions SET features_text = (
            SELECT string_agg(feature, '|')
            FROM json_array_elements_text(idea_versions.features) AS values(feature)
        )
        """
    )
    op.drop_column("idea_versions", "features")
    op.alter_column(
        "idea_versions",
        "features_text",
        nullable=False,
        new_column_name="features",
    )
    op.drop_constraint(
        "fk_idea_versions_source_version_id_idea_versions", "idea_versions", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_idea_versions_created_by_id_users", "idea_versions", type_="foreignkey"
    )
    op.drop_column("idea_versions", "change_summary")
    op.drop_column("idea_versions", "source_version_id")
    op.drop_column("idea_versions", "created_by_id")
