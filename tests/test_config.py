import pytest

from app.config import Settings

CLIENT = "12345678901-abc.apps.googleusercontent.com"


@pytest.mark.parametrize(
    "raw, expected",
    [
        (CLIENT, [CLIENT]),  # bare value, as often pasted into a hosting dashboard
        (f'["{CLIENT}"]', [CLIENT]),
        (f"{CLIENT}, other-id ", [CLIENT, "other-id"]),
        ("", []),
    ],
)
def test_google_client_ids_from_env(monkeypatch, raw, expected):
    monkeypatch.setenv("KAASU_GOOGLE_CLIENT_IDS", raw)
    assert Settings().google_client_ids == expected


def test_cors_origins_drop_trailing_slash(monkeypatch):
    monkeypatch.setenv("KAASU_CORS_ORIGINS", "https://kaasupathayam-web.onrender.com/")
    assert Settings().cors_origins == ["https://kaasupathayam-web.onrender.com"]
