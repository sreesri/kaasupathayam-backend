from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.security import decode_access_token

_bearer = HTTPBearer(auto_error=False)

DB = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DB, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]
) -> User:
    user_id = decode_access_token(creds.credentials) if creds else None
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_member(user: CurrentUser) -> User:
    """A user who belongs to a household."""
    if user.household_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Create or join a household first")
    return user


Member = Annotated[User, Depends(get_member)]
