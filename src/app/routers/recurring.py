import uuid
from datetime import date

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.deps import DB, Member
from app.models import RecurringTransaction
from app.schemas import RecurringCreate, RecurringOut, RecurringUpdate, Scope
from app.services.ledger import validate_entry
from app.services.recurring import materialize_due, refresh_next_date

router = APIRouter(prefix="/recurring", tags=["recurring"])


def _own_rule(db: DB, user: Member, rule_id: uuid.UUID) -> RecurringTransaction:
    rule = db.get(RecurringTransaction, rule_id)
    if rule is None or rule.household_id != user.household_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurring transaction not found")
    if rule.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your recurring transaction")
    return rule


@router.get("", response_model=list[RecurringOut])
def list_recurring(user: Member, db: DB, scope: Scope = Scope.ME) -> list[RecurringTransaction]:
    stmt = select(RecurringTransaction).where(
        RecurringTransaction.household_id == user.household_id
    )
    if scope is Scope.ME:
        stmt = stmt.where(RecurringTransaction.user_id == user.id)
    return list(db.scalars(stmt.order_by(RecurringTransaction.next_date)))


@router.post("", response_model=RecurringOut, status_code=status.HTTP_201_CREATED)
def create_recurring(body: RecurringCreate, user: Member, db: DB) -> RecurringTransaction:
    if body.end_date and body.end_date < body.start_date:
        raise HTTPException(422, "end_date is before start_date")
    validate_entry(db, user, body.type, body.account_id, body.to_account_id, body.category_id)
    rule = RecurringTransaction(
        household_id=user.household_id, user_id=user.id, occurrences=0, **body.model_dump()
    )
    refresh_next_date(rule)
    db.add(rule)
    db.flush()
    # Back-fill occurrences already due (e.g. a salary rule that started last month).
    materialize_due(db, user.household_id, date.today())
    db.commit()
    return rule


@router.patch("/{rule_id}", response_model=RecurringOut)
def update_recurring(
    rule_id: uuid.UUID, body: RecurringUpdate, user: Member, db: DB
) -> RecurringTransaction:
    rule = _own_rule(db, user, rule_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    validate_entry(db, user, rule.type, rule.account_id, rule.to_account_id, rule.category_id)
    refresh_next_date(rule)
    db.commit()
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recurring(rule_id: uuid.UUID, user: Member, db: DB) -> Response:
    """Stops future occurrences; transactions already created are kept."""
    db.delete(_own_rule(db, user, rule_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
