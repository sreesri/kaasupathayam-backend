import secrets
import string

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.category_icons import DEFAULT_CATEGORIES
from app.deps import DB, CurrentUser, Member
from app.models import Category, Household, Role, User
from app.schemas import HouseholdCreate, HouseholdJoin, HouseholdOut

router = APIRouter(prefix="/households", tags=["households"])


def _invite_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(8))


def _require_no_household(user: User) -> None:
    if user.household_id is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "You already belong to a household")


@router.post("", response_model=HouseholdOut, status_code=status.HTTP_201_CREATED)
def create_household(body: HouseholdCreate, user: CurrentUser, db: DB) -> Household:
    _require_no_household(user)
    household = Household(name=body.name, currency=body.currency, invite_code=_invite_code())
    db.add(household)
    db.flush()
    for kind, icons in DEFAULT_CATEGORIES.items():
        db.add_all(
            Category(household_id=household.id, name=name, kind=kind, icon=icon)
            for name, icon in icons.items()
        )
    user.household_id, user.role = household.id, Role.OWNER
    db.commit()
    db.refresh(household)
    return household


@router.post("/join", response_model=HouseholdOut)
def join_household(body: HouseholdJoin, user: CurrentUser, db: DB) -> Household:
    _require_no_household(user)
    household = db.scalar(select(Household).where(Household.invite_code == body.invite_code))
    if household is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invalid invite code")
    user.household_id, user.role = household.id, Role.MEMBER
    db.commit()
    db.refresh(household)
    return household


@router.get("/current", response_model=HouseholdOut)
def current_household(user: Member, db: DB) -> Household:
    return db.get(Household, user.household_id)


@router.post("/current/invite-code", response_model=HouseholdOut)
def regenerate_invite_code(user: Member, db: DB) -> Household:
    if user.role is not Role.OWNER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the household owner can do this")
    household = db.get(Household, user.household_id)
    household.invite_code = _invite_code()
    db.commit()
    return household
