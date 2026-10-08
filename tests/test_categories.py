from tests.conftest import category_id, make_account


def test_default_categories_have_icons(client, household):
    owner, _ = household
    cats = {
        c["name"]: c["icon"]
        for c in client.get("/categories", params={"kind": "expense"}, headers=owner).json()
    }
    assert cats["Groceries"] == "cart-outline" and cats["Dining"] == "restaurant-outline"


def test_create_remove_and_recreate(client, household):
    owner, member = household
    r = client.post(
        "/categories",
        json={"name": "Pets", "kind": "expense", "icon": "paw-outline"},
        headers=member,
    )
    assert r.status_code == 201 and r.json()["icon"] == "paw-outline"
    pets = r.json()["id"]
    # Same name again (any case) while it exists is a conflict.
    assert (
        client.post(
            "/categories", json={"name": "pets", "kind": "expense"}, headers=owner
        ).status_code
        == 409
    )
    # Bad icon names are rejected.
    assert (
        client.post(
            "/categories", json={"name": "X", "kind": "expense", "icon": "<b>"}, headers=owner
        ).status_code
        == 422
    )

    # Removing hides it from the list but keeps the row.
    assert (
        client.patch(f"/categories/{pets}", json={"archived": True}, headers=owner).status_code
        == 200
    )
    names = [c["name"] for c in client.get("/categories", headers=owner).json()]
    assert "Pets" not in names
    archived = client.get("/categories", params={"include_archived": True}, headers=owner).json()
    assert any(c["id"] == pets and c["archived"] for c in archived)

    # Re-adding it restores the same category (with the new icon).
    r = client.post(
        "/categories",
        json={"name": "Pets", "kind": "expense", "icon": "heart-outline"},
        headers=owner,
    )
    assert (r.status_code, r.json()["id"], r.json()["icon"], r.json()["archived"]) == (
        201,
        pets,
        "heart-outline",
        False,
    )


def test_removed_category_only_affects_new_transactions(client, household):
    owner, _ = household
    bank = make_account(client, owner)
    dining = category_id(client, owner, "Dining")
    groceries = category_id(client, owner, "Groceries")
    txn = client.post(
        "/transactions",
        json={
            "type": "expense",
            "amount": "50",
            "account_id": bank,
            "category_id": dining,
            "occurred_on": "2026-01-01",
        },
        headers=owner,
    ).json()
    client.patch(f"/categories/{dining}", json={"archived": True}, headers=owner)

    # Old transaction keeps its category, and can still be edited.
    r = client.patch(f"/transactions/{txn['id']}", json={"amount": "60"}, headers=owner)
    assert (r.status_code, r.json()["category_id"]) == (200, dining)
    # New transactions can't use it, and an old one can't be moved onto it either.
    r = client.post(
        "/transactions",
        json={
            "type": "expense",
            "amount": "5",
            "account_id": bank,
            "category_id": dining,
            "occurred_on": "2026-01-02",
        },
        headers=owner,
    )
    assert r.status_code == 422 and "removed" in r.json()["detail"]
    other = client.post(
        "/transactions",
        json={
            "type": "expense",
            "amount": "5",
            "account_id": bank,
            "category_id": groceries,
            "occurred_on": "2026-01-02",
        },
        headers=owner,
    ).json()
    assert (
        client.patch(
            f"/transactions/{other['id']}", json={"category_id": dining}, headers=owner
        ).status_code
        == 422
    )
