from datetime import date

from tests.conftest import category_id, make_account


def test_budget_status_personal_vs_household(client, household):
    owner, member = household
    food = category_id(client, owner, "Groceries")
    today = date.today().isoformat()
    for headers, amount in ((owner, "30"), (member, "50")):
        acct = make_account(client, headers)
        client.post(
            "/transactions",
            json={
                "type": "expense",
                "amount": amount,
                "account_id": acct,
                "category_id": food,
                "occurred_on": today,
            },
            headers=headers,
        )

    assert (
        client.post(
            "/budgets", json={"category_id": food, "amount": "100"}, headers=owner
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/budgets", json={"category_id": food, "amount": "200", "shared": True}, headers=member
        ).status_code
        == 201
    )

    mine = client.get("/budgets/status", headers=owner).json()
    assert [(b["spent"], b["remaining"]) for b in mine] == [("30.00", "70.00")]
    shared = client.get("/budgets/status", params={"scope": "household"}, headers=owner).json()
    assert [(b["spent"], b["remaining"]) for b in shared] == [("80.00", "120.00")]


def test_summary_and_trend(client, household):
    owner, member = household
    today = date.today().isoformat()
    for headers, kind, cat, amount in (
        (owner, "income", "Salary", "1000"),
        (member, "expense", "Dining", "40"),
    ):
        acct = make_account(client, headers)
        client.post(
            "/transactions",
            json={
                "type": kind,
                "amount": amount,
                "account_id": acct,
                "category_id": category_id(client, headers, cat, kind),
                "occurred_on": today,
            },
            headers=headers,
        )

    me = client.get("/reports/summary", headers=owner).json()
    assert (me["income"], me["expense"]) == ("1000.00", "0")
    house = client.get("/reports/summary", params={"scope": "household"}, headers=owner).json()
    assert (house["net"], len(house["by_member"])) == ("960.00", 2)

    trend = client.get(
        "/reports/trend", params={"scope": "household", "months": 3}, headers=owner
    ).json()
    assert len(trend) == 3 and trend[-1]["expense"] == "40.00"
