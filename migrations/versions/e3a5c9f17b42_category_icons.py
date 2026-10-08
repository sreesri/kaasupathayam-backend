"""category icons

Adds categories.icon (an Ionicons glyph name) and gives existing categories with the default
names their icons. The mapping is copied here so later edits to the defaults can't change
what this migration did.

Revision ID: e3a5c9f17b42
Revises: d7f2b8e41a90
Create Date: 2026-10-09 18:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e3a5c9f17b42"
down_revision: str | Sequence[str] | None = "d7f2b8e41a90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ICONS = {
    ("expense", "Groceries"): "cart-outline",
    ("expense", "Dining"): "restaurant-outline",
    ("expense", "Rent"): "home-outline",
    ("expense", "Utilities"): "flash-outline",
    ("expense", "Transport"): "bus-outline",
    ("expense", "Fuel"): "car-outline",
    ("expense", "Shopping"): "bag-handle-outline",
    ("expense", "Health"): "medkit-outline",
    ("expense", "Education"): "school-outline",
    ("expense", "Entertainment"): "film-outline",
    ("expense", "Travel"): "airplane-outline",
    ("expense", "Subscriptions"): "repeat-outline",
    ("expense", "Insurance"): "shield-checkmark-outline",
    ("expense", "Gifts"): "gift-outline",
    ("expense", "Other"): "ellipsis-horizontal-circle-outline",
    ("income", "Salary"): "briefcase-outline",
    ("income", "Business"): "storefront-outline",
    ("income", "Interest"): "trending-up-outline",
    ("income", "Gifts"): "gift-outline",
    ("income", "Refunds"): "arrow-undo-outline",
    ("income", "Other"): "ellipsis-horizontal-circle-outline",
}


def upgrade() -> None:
    with op.batch_alter_table("categories") as batch:
        batch.add_column(
            sa.Column(
                "icon", sa.String(length=40), nullable=False, server_default="pricetag-outline"
            )
        )
    categories = sa.table(
        "categories",
        sa.column("kind", sa.String),
        sa.column("name", sa.String),
        sa.column("icon", sa.String),
    )
    for (kind, name), icon in ICONS.items():
        op.execute(
            categories.update()
            .where(categories.c.kind == kind, categories.c.name == name)
            .values(icon=icon)
        )


def downgrade() -> None:
    with op.batch_alter_table("categories") as batch:
        batch.drop_column("icon")
