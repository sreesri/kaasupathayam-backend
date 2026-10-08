import uuid
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models import AccountType, CategoryKind, Role, TxnType

PositiveMoney = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]
Money = Annotated[Decimal, Field(max_digits=14, decimal_places=2)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]


class Scope(StrEnum):
    """`me` = only the caller's data; `household` = every member's data."""

    ME = "me"
    HOUSEHOLD = "household"


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- auth ---


class GoogleLoginIn(BaseModel):
    id_token: str


class UserOut(ORM):
    id: uuid.UUID
    email: str
    name: str
    household_id: uuid.UUID | None
    role: Role | None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# --- households ---


class HouseholdCreate(BaseModel):
    name: Name
    currency: Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")] = "INR"


class HouseholdJoin(BaseModel):
    invite_code: Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True)]


class MemberOut(ORM):
    id: uuid.UUID
    name: str
    email: str
    role: Role | None


class HouseholdOut(ORM):
    id: uuid.UUID
    name: str
    currency: str
    invite_code: str
    members: list[MemberOut]


# --- accounts ---


class AccountCreate(BaseModel):
    name: Name
    type: AccountType
    opening_balance: Money = Decimal("0")
    credit_limit: PositiveMoney | None = None


class AccountUpdate(BaseModel):
    name: Name | None = None
    opening_balance: Money | None = None
    credit_limit: PositiveMoney | None = None
    archived: bool | None = None


class AccountOut(ORM):
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    type: AccountType
    opening_balance: Decimal
    credit_limit: Decimal | None
    archived: bool
    balance: Decimal


# --- categories ---


class CategoryCreate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
    kind: CategoryKind


class CategoryUpdate(BaseModel):
    name: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)] | None
    ) = None
    archived: bool | None = None


class CategoryOut(ORM):
    id: uuid.UUID
    name: str
    kind: CategoryKind
    archived: bool


# --- transactions ---


class TransactionCreate(BaseModel):
    type: TxnType
    amount: PositiveMoney
    account_id: uuid.UUID
    to_account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    occurred_on: date
    note: Note | None = None


class TransactionUpdate(BaseModel):
    amount: PositiveMoney | None = None
    account_id: uuid.UUID | None = None
    to_account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    occurred_on: date | None = None
    note: Note | None = None


class TransactionOut(ORM):
    id: uuid.UUID
    user_id: uuid.UUID
    type: TxnType
    amount: Decimal
    account_id: uuid.UUID
    to_account_id: uuid.UUID | None
    category_id: uuid.UUID | None
    occurred_on: date
    note: str | None


# --- budgets ---


class BudgetCreate(BaseModel):
    category_id: uuid.UUID
    amount: PositiveMoney
    # True = household budget counting every member's spending.
    shared: bool = False


class BudgetUpdate(BaseModel):
    amount: PositiveMoney


class BudgetOut(ORM):
    id: uuid.UUID
    category_id: uuid.UUID
    user_id: uuid.UUID | None
    amount: Decimal


class BudgetStatusOut(BudgetOut):
    spent: Decimal
    remaining: Decimal


# --- reports ---


class CategoryTotal(BaseModel):
    category_id: uuid.UUID | None
    type: TxnType
    total: Decimal


class MemberTotal(BaseModel):
    user_id: uuid.UUID
    income: Decimal
    expense: Decimal


class SummaryOut(BaseModel):
    start: date
    end: date
    income: Decimal
    expense: Decimal
    net: Decimal
    by_category: list[CategoryTotal]
    by_member: list[MemberTotal]


class TrendPoint(BaseModel):
    month: str  # YYYY-MM
    income: Decimal
    expense: Decimal
