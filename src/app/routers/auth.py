from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app import google
from app.deps import DB, CurrentUser
from app.models import User
from app.schemas import GoogleLoginIn, TokenOut, UserOut
from app.security import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/google", response_model=TokenOut)
def google_login(body: GoogleLoginIn, db: DB) -> TokenOut:
    """Exchange a Google ID token for an API access token, creating the user on first login."""
    try:
        identity = google.verify_google_token(body.id_token)
    except google.GoogleAuthError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e)) from None

    user = db.scalar(select(User).where(User.google_sub == identity.sub))
    if user is None:
        user = User(google_sub=identity.sub, email=identity.email, name=identity.name)
        db.add(user)
    else:
        # Keep profile details in sync with the Google account.
        user.email, user.name = identity.email, identity.name
    db.commit()
    return TokenOut(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user
