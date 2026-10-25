"""Versioned single-store import/audit/auth foundation."""

import sqlalchemy as sa
from alembic import op

revision = "001"
down_revision = None


def upgrade() -> None:
    op.create_table(
        "batches",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("identity", sa.String(), nullable=False, unique=True),
        *[
            sa.Column(n, sa.String(), nullable=False)
            for n in ["filename", "checksum", "report_type", "scope", "start", "end", "status", "created_at"]
        ],
        *[
            sa.Column(n, sa.JSON(), nullable=False)
            for n in ["metadata_json", "rows", "issues", "reconciliation"]
        ],
    )
    op.create_table(
        "audit",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("batch_id", sa.String(), sa.ForeignKey("batches.id"), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("at", sa.String(), nullable=False),
    )
    op.create_table(
        "owner",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("password_hash", sa.String(), nullable=False),
    )
    op.create_table(
        "sessions",
        sa.Column("token_hash", sa.String(), primary_key=True),
        sa.Column("expires", sa.Integer(), nullable=False),
    )
    op.create_table(
        "settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("values", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    raise RuntimeError("Destructive downgrade prohibited; restore an approved consistent backup instead.")
