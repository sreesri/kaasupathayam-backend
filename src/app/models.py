import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

Money = Numeric(14, 2)


def _enum(cls: type[StrEnum]) -> SAEnum:
    # Stored as plain strings (no native PG enum) so adding values needs no type migration.
    return SAEnum(cls, native_enum=False, length=20, values_callable=lambda e: [m.value for m in e])


def _now() -> datetime:
    return datetime.now(UTC)


class Role(StrEnum):
    OWNER = "owner"
    MEMBER = "member"


class AccountType(StrEnum):
    BANK = "bank"
    CREDIT_CARD = "credit_card"
    CASH = "cash"
    WALLET = "wallet"


class CategoryKind(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"


class TxnType(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class Household(Base):
    __tablename__ = "households"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    invite_code: Mapped[str] = mapped_column(String(12), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    members: Mapped[list["User"]] = relationship(back_populates="household")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    # Google account id (the ID token's `sub`); stable even if the user's email changes.
    google_sub: Mapped[str] = mapped_column(String(255), unique=True)
    # A user belongs to at most one household; null until they create or join one.
    household_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("households.id"))
    role: Mapped[Role | None] = mapped_column(_enum(Role))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    household: Mapped[Household | None] = relationship(back_populates="members")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("households.id"), index=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(100))
    type: Mapped[AccountType] = mapped_column(_enum(AccountType))
    # Balance before the first tracked transaction. Negative for money owed (e.g. a card bill).
    opening_balance: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    credit_limit: Mapped[Decimal | None] = mapped_column(Money)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("household_id", "kind", "name"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("households.id"), index=True)
    name: Mapped[str] = mapped_column(String(50))
    kind: Mapped[CategoryKind] = mapped_column(_enum(CategoryKind))
    archived: Mapped[bool] = mapped_column(Boolean, default=False)


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (Index("ix_transactions_household_date", "household_id", "occurred_on"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("households.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"))
    # Destination for transfers (including credit card bill payments); null otherwise.
    to_account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("accounts.id"))
    category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("categories.id"))
    type: Mapped[TxnType] = mapped_column(_enum(TxnType))
    # Always positive; direction comes from `type`.
    amount: Mapped[Decimal] = mapped_column(Money)
    occurred_on: Mapped[date] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Budget(Base):
    """Monthly spending limit for an expense category.

    user_id set = personal budget (only that user's spending counts);
    user_id null = household budget (everyone's spending counts).
    """

    __tablename__ = "budgets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("households.id"), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categories.id"))
    amount: Mapped[Decimal] = mapped_column(Money)
