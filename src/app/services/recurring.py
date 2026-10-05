import uuid
from datetime import date

from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Frequency, RecurringTransaction, Transaction

# Guards against runaway loops, e.g. a daily rule started years in the past.
MAX_PER_RUN = 1000


def occurrence_date(rule: RecurringTransaction, n: int) -> date:
    """Date of the n-th occurrence (0-based). Computed from start_date rather than the
    previous occurrence so a rule starting on the 31st stays on month-end days."""
    step = n * rule.interval
    match rule.frequency:
        case Frequency.DAILY:
            delta = relativedelta(days=step)
        case Frequency.WEEKLY:
            delta = relativedelta(weeks=step)
        case Frequency.MONTHLY:
            delta = relativedelta(months=step)
        case Frequency.YEARLY:
            delta = relativedelta(years=step)
    return rule.start_date + delta


def refresh_next_date(rule: RecurringTransaction) -> None:
    nxt = occurrence_date(rule, rule.occurrences)
    rule.next_date = None if rule.end_date and nxt > rule.end_date else nxt


def materialize_due(db: Session, household_id: uuid.UUID, today: date) -> int:
    """Create transactions for every occurrence due on or before `today`. Returns the count."""
    rules = db.scalars(
        select(RecurringTransaction).where(
            RecurringTransaction.household_id == household_id,
            RecurringTransaction.active.is_(True),
            RecurringTransaction.next_date.is_not(None),
            RecurringTransaction.next_date <= today,
        )
    ).all()
    created = 0
    for rule in rules:
        while rule.next_date is not None and rule.next_date <= today and created < MAX_PER_RUN:
            db.add(
                Transaction(
                    household_id=rule.household_id,
                    user_id=rule.user_id,
                    account_id=rule.account_id,
                    to_account_id=rule.to_account_id,
                    category_id=rule.category_id,
                    type=rule.type,
                    amount=rule.amount,
                    occurred_on=rule.next_date,
                    note=rule.note,
                    recurring_id=rule.id,
                )
            )
            rule.occurrences += 1
            refresh_next_date(rule)
            created += 1
    return created
