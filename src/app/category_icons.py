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
        "Transport": "bus-outline",
        "Fuel": "car-outline",
        "Shopping": "bag-handle-outline",
        "Health": "medkit-outline",
        "Education": "school-outline",
        "Entertainment": "film-outline",
        "Travel": "airplane-outline",
        "Subscriptions": "repeat-outline",
        "Insurance": "shield-checkmark-outline",
        "Gifts": "gift-outline",
        "Other": "ellipsis-horizontal-circle-outline",
    },
    CategoryKind.INCOME: {
        "Salary": "briefcase-outline",
        "Business": "storefront-outline",
        "Interest": "trending-up-outline",
        "Gifts": "gift-outline",
        "Refunds": "arrow-undo-outline",
        "Other": "ellipsis-horizontal-circle-outline",
    },
}
