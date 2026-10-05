"""Validation and balance rules shared by one-off and recurring transactions."""

import uuid
from collections import defaultdict
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Account, Category, CategoryKind, Transaction, TxnType, User


def _bad(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail)


def get_household_account(db: Session, user: User, account_id: uuid.UUID) -> Account:
    account = db.get(Account, account_id)
    if account is None or account.household_id != user.household_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")
    return account


def validate_entry(
    db: Session,
    user: User,
    type: TxnType,
    account_id: uuid.UUID,
    to_account_id: uuid.UUID | None,
    category_id: uuid.UUID | None,
) -> None:
    """Members log against their own accounts. Transfers may go to any household account
    (e.g. paying a spouse's credit card bill)."""
    account = get_household_account(db, user, account_id)
    if account.owner_id != user.id:
        raise _bad("You can only record transactions on your own accounts")

    if type is TxnType.TRANSFER:
        if to_account_id is None:
            raise _bad("Transfers need a destination account")
        if to_account_id == account_id:
            raise _bad("Cannot transfer to the same account")
        get_household_account(db, user, to_account_id)
        if category_id is not None:
            raise _bad("Transfers do not take a category")
        return

    if to_account_id is not None:
        raise _bad("Only transfers have a destination account")
    if category_id is None:
        raise _bad("Income and expenses need a category")
    category = db.get(Category, category_id)
    if category is None or category.household_id != user.household_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")
    if category.kind != CategoryKind(type.value):
        raise _bad(f"Category '{category.name}' is not an {type.value} category")


def balances(db: Session, accounts: list[Account]) -> dict[uuid.UUID, Decimal]:
    """Current balance = opening balance + income - expenses - transfers out + transfers in."""
    ids = [a.id for a in accounts]
    result: dict[uuid.UUID, Decimal] = defaultdict(Decimal)
    for a in accounts:
        result[a.id] += a.opening_balance
    if not ids:
        return result

    sign = {TxnType.INCOME: 1, TxnType.EXPENSE: -1, TxnType.TRANSFER: -1}
    rows = db.execute(
        select(Transaction.account_id, Transaction.type, func.sum(Transaction.amount))
        .where(Transaction.account_id.in_(ids))
        .group_by(Transaction.account_id, Transaction.type)
    )
    for account_id, type_, total in rows:
        result[account_id] += sign[type_] * Decimal(total)

    rows = db.execute(
        select(Transaction.to_account_id, func.sum(Transaction.amount))
        .where(Transaction.to_account_id.in_(ids))
        .group_by(Transaction.to_account_id)
    )
    for account_id, total in rows:
        result[account_id] += Decimal(total)
    return result
