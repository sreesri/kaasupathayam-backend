from dataclasses import dataclass

from google.auth.exceptions import TransportError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.config import settings

_transport = google_requests.Request()


class GoogleAuthError(Exception):
    pass


@dataclass(frozen=True)
class GoogleIdentity:
    sub: str
    email: str
    name: str


def identity_from_claims(claims: dict, allowed_client_ids: list[str]) -> GoogleIdentity:
    """Checks the claims Google's signature check doesn't: audience and verified email."""
    if claims.get("aud") not in allowed_client_ids:
        raise GoogleAuthError("Token was issued for a different app")
    if not claims.get("email_verified"):
        raise GoogleAuthError("Google account email is not verified")
    email = claims["email"].lower()
    return GoogleIdentity(sub=claims["sub"], email=email, name=claims.get("name") or email)


def verify_google_token(token: str) -> GoogleIdentity:
    """Verify a Google ID token (signature, expiry, issuer) and return who it belongs to.
    Google's public keys are fetched over the network and cached by google-auth."""
    if not settings.google_client_ids:
        raise GoogleAuthError("Google sign-in is not configured (KAASU_GOOGLE_CLIENT_IDS)")
    try:
        claims = id_token.verify_oauth2_token(token, _transport)
    except ValueError as e:
        raise GoogleAuthError(f"Invalid Google token: {e}") from None
    except TransportError:
        raise GoogleAuthError("Could not reach Google to verify sign-in; try again") from None
    return identity_from_claims(claims, settings.google_client_ids)
