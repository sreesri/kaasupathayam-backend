import pytest

from app.google import GoogleAuthError, GoogleIdentity, identity_from_claims
from tests.conftest import register


def test_google_login_creates_then_reuses_user(client):
    first = client.post("/auth/google", json={"id_token": "a@example.com|Asha"}).json()
    headers = {"Authorization": f"Bearer {first['access_token']}"}
    me = client.get("/auth/me", headers=headers).json()
    assert (me["email"], me["name"], me["household_id"]) == ("a@example.com", "Asha", None)

    # Same Google account again (name changed in Google): same user, profile updated.
    again = client.post("/auth/google", json={"id_token": "a@example.com|Asha R"}).json()
    assert again["user"]["id"] == first["user"]["id"]
    assert again["user"]["name"] == "Asha R"


def test_google_login_rejected(client):
    assert client.post("/auth/google", json={"id_token": ""}).status_code == 401
    assert client.get("/auth/me").status_code == 401


def test_claim_checks():
    claims = {"aud": "web-id", "sub": "1", "email": "A@x.com", "email_verified": True}
    assert identity_from_claims(claims, ["web-id"]) == GoogleIdentity("1", "a@x.com", "a@x.com")
    with pytest.raises(GoogleAuthError):
        identity_from_claims(claims, ["other-app"])
    with pytest.raises(GoogleAuthError):
        identity_from_claims({**claims, "email_verified": False}, ["web-id"])


def test_household_required(client):
    headers = register(client, "a@example.com")
    assert client.get("/accounts", headers=headers).status_code == 409


def test_household_create_join(client, household):
    owner, member = household
    h = client.get("/households/current", headers=member).json()
    assert {m["role"] for m in h["members"]} == {"owner", "member"}
    assert len(client.get("/categories", headers=member).json()) > 10
    assert client.post("/households/current/invite-code", headers=member).status_code == 403
    assert client.post("/households/current/invite-code", headers=owner).status_code == 200
