"""prune default categories

Removes (archives) the default categories the household no longer wants, in every household:
expense Transport, Education, Travel, Subscriptions, Insurance, Gifts, Other; income Business,
Gifts, Other. Archiving, not deleting, so past transactions keep their category; adding one
back with the same name in the app restores it.

Revision ID: f1b6d2a83c57
Revises: e3a5c9f17b42
Create Date: 2026-10-11 10:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f1b6d2a83c57"
down_revision: str | Sequence[str] | None = "e3a5c9f17b42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REMOVED = {
    "expense": ["Transport", "Education", "Travel", "Subscriptions", "Insurance", "Gifts", "Other"],
    "income": ["Business", "Gifts", "Other"],
}

categories = sa.table(
    "categories",
    sa.column("kind", sa.String),
    sa.column("name", sa.String),
    sa.column("archived", sa.Boolean),
)


def _set_archived(value: bool) -> None:
    for kind, names in REMOVED.items():
        op.execute(
            categories.update()
            .where(categories.c.kind == kind, categories.c.name.in_(names))
            .values(archived=value)
        )


def upgrade() -> None:
    _set_archived(True)


def downgrade() -> None:
    """Best effort: brings these names back everywhere, even any removed by hand before."""
    _set_archived(False)
