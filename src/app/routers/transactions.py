import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import or_, select

from app.deps import DB, Member
from app.models import Transaction, TxnType
from app.schemas import Scope, TransactionCreate, TransactionOut, TransactionUpdate
from app.services.ledger import validate_entry

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _own_transaction(db: DB, user: Member, txn_id: uuid.UUID) -> Transaction:
    txn = db.get(Transaction, txn_id)
    if txn is None or txn.household_id != user.household_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transaction not found")
    if txn.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your transaction")
    return txn


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    user: Member,
    db: DB,
    scope: Scope = Scope.ME,
    start: date | None = None,
    end: date | None = None,
    type: TxnType | None = None,
    account_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    member_id: Annotated[uuid.UUID | None, Query(description="household scope only")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Transaction]:
    stmt = select(Transaction).where(Transaction.household_id == user.household_id)
    if scope is Scope.ME:
        stmt = stmt.where(Transaction.user_id == user.id)
    elif member_id:
        stmt = stmt.where(Transaction.user_id == member_id)
    if start:
        stmt = stmt.where(Transaction.occurred_on >= start)
    if end:
        stmt = stmt.where(Transaction.occurred_on <= end)
    if type:
        stmt = stmt.where(Transaction.type == type)
    if account_id:
        stmt = stmt.where(
            or_(Transaction.account_id == account_id, Transaction.to_account_id == account_id)
        )
    if category_id:
        stmt = stmt.where(Transaction.category_id == category_id)
    stmt = stmt.order_by(Transaction.occurred_on.desc(), Transaction.created_at.desc())
    return list(db.scalars(stmt.limit(limit).offset(offset)))


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(body: TransactionCreate, user: Member, db: DB) -> Transaction:
    validate_entry(db, user, body.type, body.account_id, body.to_account_id, body.category_id)
    txn = Transaction(household_id=user.household_id, user_id=user.id, **body.model_dump())
    db.add(txn)
    db.commit()
    return txn


@router.get("/{txn_id}", response_model=TransactionOut)
def get_transaction(txn_id: uuid.UUID, user: Member, db: DB) -> Transaction:
    txn = db.get(Transaction, txn_id)
    if txn is None or txn.household_id != user.household_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transaction not found")
    return txn


@router.patch("/{txn_id}", response_model=TransactionOut)
def update_transaction(
    txn_id: uuid.UUID, body: TransactionUpdate, user: Member, db: DB
) -> Transaction:
    txn = _own_transaction(db, user, txn_id)
    original_category = txn.category_id
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(txn, field, value)
    validate_entry(
        db,
        user,
        txn.type,
        txn.account_id,
        txn.to_account_id,
        txn.category_id,
        keep_category_id=original_category,
    )
    db.commit()
    return txn


@router.delete("/{txn_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(txn_id: uuid.UUID, user: Member, db: DB) -> Response:
    db.delete(_own_transaction(db, user, txn_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
