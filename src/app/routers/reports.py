from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Annotated

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.deps import DB, Member
from app.models import Transaction, TxnType
from app.schemas import CategoryTotal, MemberTotal, Scope, SummaryOut, TrendPoint

router = APIRouter(prefix="/reports", tags=["reports"])

ZERO = Decimal("0")


def _scoped(stmt, user: Member, scope: Scope):
    stmt = stmt.where(
        Transaction.household_id == user.household_id, Transaction.type != TxnType.TRANSFER
    )
    return stmt.where(Transaction.user_id == user.id) if scope is Scope.ME else stmt


@router.get("/summary", response_model=SummaryOut)
def summary(
    user: Member,
    db: DB,
    scope: Scope = Scope.ME,
    start: date | None = None,
    end: date | None = None,
) -> SummaryOut:
    """Income/expense totals for a date range (defaults to the current month).
    Transfers are excluded: they move money, they don't earn or spend it."""
    start = start or date.today().replace(day=1)
    end = end or start + relativedelta(months=1, days=-1)
    if end < start:
        raise HTTPException(422, "end is before start")
    in_range = Transaction.occurred_on.between(start, end)

    by_category = [
        CategoryTotal(category_id=cid, type=t, total=Decimal(total))
        for cid, t, total in db.execute(
            _scoped(
                select(Transaction.category_id, Transaction.type, func.sum(Transaction.amount)),
                user,
                scope,
            )
            .where(in_range)
            .group_by(Transaction.category_id, Transaction.type)
        )
    ]
    income = sum((c.total for c in by_category if c.type is TxnType.INCOME), ZERO)
    expense = sum((c.total for c in by_category if c.type is TxnType.EXPENSE), ZERO)

    members: dict = defaultdict(lambda: {"income": ZERO, "expense": ZERO})
    for uid, t, total in db.execute(
        _scoped(
            select(Transaction.user_id, Transaction.type, func.sum(Transaction.amount)), user, scope
        )
        .where(in_range)
        .group_by(Transaction.user_id, Transaction.type)
    ):
        members[uid][t.value] += Decimal(total)

    return SummaryOut(
        start=start,
        end=end,
        income=income,
        expense=expense,
        net=income - expense,
        by_category=sorted(by_category, key=lambda c: c.total, reverse=True),
        by_member=[MemberTotal(user_id=uid, **v) for uid, v in members.items()],
    )


@router.get("/trend", response_model=list[TrendPoint])
def trend(
    user: Member, db: DB, scope: Scope = Scope.ME, months: Annotated[int, Query(ge=1, le=24)] = 6
) -> list[TrendPoint]:
    """Monthly income and expense for the last `months` months, oldest first."""
    first = date.today().replace(day=1) - relativedelta(months=months - 1)
    keys = [(first + relativedelta(months=i)).strftime("%Y-%m") for i in range(months)]
    totals = {k: {"income": ZERO, "expense": ZERO} for k in keys}
    # Aggregated in Python because month truncation differs between Postgres and SQLite.
    rows = db.execute(
        _scoped(
            select(Transaction.occurred_on, Transaction.type, Transaction.amount), user, scope
        ).where(Transaction.occurred_on >= first)
    )
    for occurred_on, t, amount in rows:
        key = occurred_on.strftime("%Y-%m")
        if key in totals:
            totals[key][t.value] += amount
    return [TrendPoint(month=k, **v) for k, v in totals.items()]
