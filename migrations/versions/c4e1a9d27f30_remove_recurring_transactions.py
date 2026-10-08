"""remove recurring transactions

The recurring income/expense feature is gone. Transactions it created stay as ordinary
transactions; only their link to the rule (transactions.recurring_id) and the rules
themselves are dropped.

Revision ID: c4e1a9d27f30
Revises: b0796255de2f
Create Date: 2026-10-09 10:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c4e1a9d27f30"
down_revision: str | Sequence[str] | None = "b0796255de2f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Batch mode so SQLite (tests, local dev) can drop a column; on Postgres this is a plain
    # ALTER TABLE, which also drops the column's foreign key to recurring_transactions.
    with op.batch_alter_table("transactions") as batch:
        batch.drop_column("recurring_id")
    op.drop_index(
        op.f("ix_recurring_transactions_household_id"), table_name="recurring_transactions"
    )
    op.drop_table("recurring_transactions")


def downgrade() -> None:
    """Restores the schema only; deleted rules can't be recovered."""
    op.create_table(
        "recurring_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("to_account_id", sa.Uuid(), nullable=True),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column(
            "type",
            sa.Enum("income", "expense", "transfer", name="txntype", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column(
            "frequency",
            sa.Enum(
                "daily",
                "weekly",
                "monthly",
                "yearly",
                name="frequency",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("interval", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("occurrences", sa.Integer(), nullable=False),
        sa.Column("next_date", sa.Date(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.ForeignKeyConstraint(["to_account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_recurring_transactions_household_id"),
        "recurring_transactions",
        ["household_id"],
        unique=False,
    )
    with op.batch_alter_table("transactions") as batch:
        batch.add_column(sa.Column("recurring_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            "transactions_recurring_id_fkey",
            "recurring_transactions",
            ["recurring_id"],
            ["id"],
            ondelete="SET NULL",
        )
