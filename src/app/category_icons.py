"""Icons for categories: Ionicons glyph names, rendered by the app."""

from app.models import CategoryKind

DEFAULT_ICON = "pricetag-outline"

# Seeded into every new household, in this order, with these icons.
DEFAULT_CATEGORIES: dict[CategoryKind, dict[str, str]] = {
    CategoryKind.EXPENSE: {
        "Groceries": "cart-outline",
        "Dining": "restaurant-outline",
        "Rent": "home-outline",
        "Utilities": "flash-outline",
        "Fuel": "car-outline",
        "Shopping": "bag-handle-outline",
        "Health": "medkit-outline",
        "Entertainment": "film-outline",
    },
    CategoryKind.INCOME: {
        "Salary": "briefcase-outline",
        "Interest": "trending-up-outline",
        "Refunds": "arrow-undo-outline",
    },
}
