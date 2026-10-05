"""Tests run against in-memory SQLite by default, so no Postgres is needed locally. CI also
runs them against Postgres by setting KAASU_TEST_DATABASE_URL, so queries must stay portable."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import google
from app.db import Base, get_db
from app.main import app


def fake_verify(token: str) -> google.GoogleIdentity:
    """Test stand-in for Google: the "ID token" is just `email` or `email|name`."""
    email, _, name = token.partition("|")
    if not email:
        raise google.GoogleAuthError("Invalid Google token")
    return google.GoogleIdentity(sub=f"sub-{email}", email=email, name=name or email)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(google, "verify_google_token", fake_verify)
    if url := os.environ.get("KAASU_TEST_DATABASE_URL"):
        engine = create_engine(url)
        Base.metadata.drop_all(engine)
    else:
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(engine, expire_on_commit=False)

    def override_get_db():
        with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    engine.dispose()


def register(client, email: str, name: str = "User") -> dict:
    r = client.post("/auth/google", json={"id_token": f"{email}|{name}"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def household(client):
    """Two members of one household: returns (owner_headers, member_headers)."""
    owner = register(client, "owner@example.com", "Owner")
    r = client.post("/households", json={"name": "Home"}, headers=owner)
    assert r.status_code == 201, r.text
    member = register(client, "member@example.com", "Member")
    r = client.post(
        "/households/join", json={"invite_code": r.json()["invite_code"]}, headers=member
    )
    assert r.status_code == 200, r.text
    return owner, member


def category_id(client, headers, name: str, kind: str = "expense") -> str:
    cats = client.get("/categories", params={"kind": kind}, headers=headers).json()
    return next(c["id"] for c in cats if c["name"] == name)


def make_account(client, headers, name="Bank", type="bank", opening="0") -> str:
    r = client.post(
        "/accounts", json={"name": name, "type": type, "opening_balance": opening}, headers=headers
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]
