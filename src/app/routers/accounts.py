import uuid

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import or_, select

from app.deps import DB, Member
from app.models import Account, AccountType, Transaction
from app.schemas import AccountCreate, AccountOut, AccountUpdate, Scope
from app.services.ledger import balances, get_household_account

router = APIRouter(prefix="/accounts", tags=["accounts"])


def _out(account: Account, balance) -> AccountOut:
    return AccountOut.model_validate({**account.__dict__, "balance": balance})


def _own_account(db: DB, user: Member, account_id: uuid.UUID) -> Account:
    account = get_household_account(db, user, account_id)
    if account.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your account")
    return account


@router.get("", response_model=list[AccountOut])
def list_accounts(
    user: Member, db: DB, scope: Scope = Scope.ME, include_archived: bool = False
) -> list[AccountOut]:
    stmt = select(Account).where(Account.household_id == user.household_id)
    if scope is Scope.ME:
        stmt = stmt.where(Account.owner_id == user.id)
    if not include_archived:
        stmt = stmt.where(Account.archived.is_(False))
    accounts = db.scalars(stmt.order_by(Account.created_at)).all()
    bal = balances(db, list(accounts))
    return [_out(a, bal[a.id]) for a in accounts]


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(body: AccountCreate, user: Member, db: DB) -> AccountOut:
    if body.credit_limit is not None and body.type is not AccountType.CREDIT_CARD:
        raise HTTPException(422, "Only credit cards have a credit limit")
    account = Account(household_id=user.household_id, owner_id=user.id, **body.model_dump())
    db.add(account)
    db.commit()
    return _out(account, account.opening_balance)


@router.patch("/{account_id}", response_model=AccountOut)
def update_account(account_id: uuid.UUID, body: AccountUpdate, user: Member, db: DB) -> AccountOut:
    account = _own_account(db, user, account_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(account, field, value)
    db.commit()
    return _out(account, balances(db, [account])[account.id])


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: uuid.UUID, user: Member, db: DB) -> Response:
    account = _own_account(db, user, account_id)
    used = db.scalar(
        select(Transaction.id)
        .where(or_(Transaction.account_id == account.id, Transaction.to_account_id == account.id))
        .limit(1)
    )
    if used:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Account has transactions; archive it instead"
        )
    db.delete(account)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
