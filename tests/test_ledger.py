from tests.conftest import category_id, make_account


def test_balances_and_transfers(client, household):
    owner, _ = household
    bank = make_account(client, owner, "Bank", opening="1000")
    card = make_account(client, owner, "Card", type="credit_card")
    salary = category_id(client, owner, "Salary", "income")
    food = category_id(client, owner, "Dining")

    for body in [
        {"type": "income", "amount": "500", "account_id": bank, "category_id": salary},
        {"type": "expense", "amount": "200", "account_id": card, "category_id": food},
        {"type": "transfer", "amount": "150", "account_id": bank, "to_account_id": card},
    ]:
        r = client.post("/transactions", json={**body, "occurred_on": "2026-01-10"}, headers=owner)
        assert r.status_code == 201, r.text

    bal = {a["name"]: a["balance"] for a in client.get("/accounts", headers=owner).json()}
    assert bal == {"Bank": "1350.00", "Card": "-50.00"}


def test_validation(client, household):
    owner, member = household
    bank = make_account(client, owner)
    salary = category_id(client, owner, "Salary", "income")
    base = {"amount": "10", "account_id": bank, "occurred_on": "2026-01-01"}

    # Expense with an income category.
    r = client.post(
        "/transactions", json={**base, "type": "expense", "category_id": salary}, headers=owner
    )
    assert r.status_code == 422
    # Transfer without destination.
    assert (
        client.post("/transactions", json={**base, "type": "transfer"}, headers=owner).status_code
        == 422
    )
    # Logging against someone else's account.
    r = client.post(
        "/transactions", json={**base, "type": "income", "category_id": salary}, headers=member
    )
    assert r.status_code == 422


def test_scope_privacy(client, household):
    owner, member = household
    bank = make_account(client, owner)
    member_bank = make_account(client, member, "Member bank")
    food = category_id(client, owner, "Dining")
    client.post(
        "/transactions",
        json={
            "type": "expense",
            "amount": "10",
            "account_id": bank,
            "category_id": food,
            "occurred_on": "2026-01-01",
        },
        headers=owner,
    )
    client.post(
        "/transactions",
        json={
            "type": "expense",
            "amount": "20",
            "account_id": member_bank,
            "category_id": food,
            "occurred_on": "2026-01-01",
        },
        headers=member,
    )

    assert len(client.get("/transactions", headers=member).json()) == 1
    assert (
        len(client.get("/transactions", params={"scope": "household"}, headers=member).json()) == 2
    )
    assert len(client.get("/accounts", params={"scope": "household"}, headers=member).json()) == 2

    owners_txn = client.get("/transactions", headers=owner).json()[0]["id"]
    assert client.delete(f"/transactions/{owners_txn}", headers=member).status_code == 403


def test_account_edit_and_delete(client, household):
    owner, member = household
    bank = make_account(client, owner, "Bank", opening="100")
    card = make_account(client, owner, "Card", type="credit_card")
    unused = make_account(client, owner, "Old wallet", type="wallet")

    r = client.patch(
        f"/accounts/{card}",
        json={"name": "HDFC Card", "opening_balance": "-500", "credit_limit": "50000"},
        headers=owner,
    )
    assert r.status_code == 200, r.text
    assert (r.json()["name"], r.json()["balance"], r.json()["credit_limit"]) == (
        "HDFC Card",
        "-500.00",
        "50000.00",
    )
    # Only the owner can edit or delete.
    assert client.patch(f"/accounts/{card}", json={"name": "x"}, headers=member).status_code == 403
    assert client.delete(f"/accounts/{unused}", headers=member).status_code == 403

    # An account used by a transfer (either side) can't be deleted, only archived.
    client.post(
        "/transactions",
        json={
            "type": "transfer",
            "amount": "50",
            "account_id": bank,
            "to_account_id": card,
            "occurred_on": "2026-01-05",
        },
        headers=owner,
    )
    assert client.delete(f"/accounts/{card}", headers=owner).status_code == 409
    assert client.delete(f"/accounts/{bank}", headers=owner).status_code == 409

    assert client.delete(f"/accounts/{unused}", headers=owner).status_code == 204
    names = [a["name"] for a in client.get("/accounts", headers=owner).json()]
    assert names == ["Bank", "HDFC Card"]
