"""Record AI provider provenance: duration, token usage, failure category.

Adds additive, nullable columns to the requirement and feedback analysis run
tables so live provider calls can record duration, token-usage metadata, and a
sanitized failure category without overwriting existing records.
"""

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

def _provenance_columns() -> list[sa.Column]:
    return [
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("token_usage", sa.JSON(), nullable=True),
        sa.Column("failure_category", sa.String(length=80), nullable=True),
    ]


def upgrade() -> None:
    for table in ("requirement_analysis_runs", "feedback_analysis_runs"):
        for column in _provenance_columns():
            op.add_column(table, column)


def downgrade() -> None:
    for table in ("feedback_analysis_runs", "requirement_analysis_runs"):
        for column in ("failure_category", "token_usage", "duration_ms"):
            op.drop_column(table, column)
