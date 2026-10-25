"""Durable original storage and shared authentication throttling."""

import sqlalchemy as sa
from alembic import op

revision = "002"
down_revision = "001"


def upgrade() -> None:
    op.create_table(
        "originals",
        sa.Column("name", sa.String(), primary_key=True),
        sa.Column("content", sa.LargeBinary(), nullable=False),
    )
    op.create_table(
        "auth_throttle",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("attempts", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    raise RuntimeError("Destructive downgrade prohibited; restore a verified backup instead.")
