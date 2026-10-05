import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func, select

from app.deps import DB, Member
from app.models import Budget, Category, CategoryKind, Transaction, TxnType
from app.schemas import BudgetCreate, BudgetOut, BudgetStatusOut, BudgetUpdate, Scope

router = APIRouter(prefix="/budgets", tags=["budgets"])

Month = Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}$", description="YYYY-MM")]


def _visible(user: Member, scope: Scope):
    """`me` = the caller's personal budgets; `household` = shared household budgets."""
    owner = Budget.user_id == user.id if scope is Scope.ME else Budget.user_id.is_(None)
    return select(Budget).where(Budget.household_id == user.household_id, owner)


def _editable_budget(db: DB, user: Member, budget_id: uuid.UUID) -> Budget:
    budget = db.get(Budget, budget_id)
    if budget is None or budget.household_id != user.household_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Budget not found")
    if budget.user_id not in (None, user.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your budget")
    return budget


@router.get("", response_model=list[BudgetOut])
def list_budgets(user: Member, db: DB, scope: Scope = Scope.ME) -> list[Budget]:
    return list(db.scalars(_visible(user, scope)))


@router.get("/status", response_model=list[BudgetStatusOut])
def budget_status(
    user: Member, db: DB, scope: Scope = Scope.ME, month: Month = None
) -> list[BudgetStatusOut]:
    start = date.fromisoformat(f"{month}-01") if month else date.today().replace(day=1)
    end = start + relativedelta(months=1, days=-1)
    budgets = db.scalars(_visible(user, scope)).all()

    spent_stmt = (
        select(Transaction.category_id, func.sum(Transaction.amount))
        .where(
            Transaction.household_id == user.household_id,
            Transaction.type == TxnType.EXPENSE,
            Transaction.occurred_on.between(start, end),
        )
        .group_by(Transaction.category_id)
    )
    if scope is Scope.ME:
        spent_stmt = spent_stmt.where(Transaction.user_id == user.id)
    spent = {cid: Decimal(total) for cid, total in db.execute(spent_stmt)}

    out = []
    for b in budgets:
        s = spent.get(b.category_id, Decimal("0"))
        out.append(
            BudgetStatusOut(
                id=b.id,
                category_id=b.category_id,
                user_id=b.user_id,
                amount=b.amount,
                spent=s,
                remaining=b.amount - s,
            )
        )
    return out


@router.post("", response_model=BudgetOut, status_code=status.HTTP_201_CREATED)
def create_budget(body: BudgetCreate, user: Member, db: DB) -> Budget:
    category = db.get(Category, body.category_id)
    if category is None or category.household_id != user.household_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")
    if category.kind is not CategoryKind.EXPENSE:
        raise HTTPException(422, "Budgets apply to expense categories only")
    scope = Scope.HOUSEHOLD if body.shared else Scope.ME
    if db.scalar(_visible(user, scope).where(Budget.category_id == body.category_id)):
        raise HTTPException(status.HTTP_409_CONFLICT, "A budget for this category already exists")
    budget = Budget(
        household_id=user.household_id,
        user_id=None if body.shared else user.id,
        category_id=body.category_id,
        amount=body.amount,
    )
    db.add(budget)
    db.commit()
    return budget


@router.patch("/{budget_id}", response_model=BudgetOut)
def update_budget(budget_id: uuid.UUID, body: BudgetUpdate, user: Member, db: DB) -> Budget:
    budget = _editable_budget(db, user, budget_id)
    budget.amount = body.amount
    db.commit()
    return budget


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(budget_id: uuid.UUID, user: Member, db: DB) -> Response:
    db.delete(_editable_budget(db, user, budget_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
