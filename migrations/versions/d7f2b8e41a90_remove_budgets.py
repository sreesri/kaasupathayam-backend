"""remove budgets

The budgets feature is gone; its table holds no data anything else references.

Revision ID: d7f2b8e41a90
Revises: c4e1a9d27f30
Create Date: 2026-10-09 15:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d7f2b8e41a90"
down_revision: str | Sequence[str] | None = "c4e1a9d27f30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index(op.f("ix_budgets_household_id"), table_name="budgets")
    op.drop_table("budgets")


def downgrade() -> None:
    """Restores the schema only; deleted budgets can't be recovered."""
    op.create_table(
        "budgets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_budgets_household_id"), "budgets", ["household_id"], unique=False)
