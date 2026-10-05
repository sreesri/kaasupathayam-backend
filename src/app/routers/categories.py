import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.deps import DB, Member
from app.models import Category, CategoryKind
from app.schemas import CategoryCreate, CategoryOut, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])


def _commit_unique(db: DB) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "A category with that name exists") from None


@router.get("", response_model=list[CategoryOut])
def list_categories(
    user: Member, db: DB, kind: CategoryKind | None = None, include_archived: bool = False
) -> list[Category]:
    stmt = select(Category).where(Category.household_id == user.household_id)
    if kind:
        stmt = stmt.where(Category.kind == kind)
    if not include_archived:
        stmt = stmt.where(Category.archived.is_(False))
    return list(db.scalars(stmt.order_by(Category.kind, Category.name)))


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(body: CategoryCreate, user: Member, db: DB) -> Category:
    category = Category(household_id=user.household_id, **body.model_dump())
    db.add(category)
    _commit_unique(db)
    return category


@router.patch("/{category_id}", response_model=CategoryOut)
def update_category(category_id: uuid.UUID, body: CategoryUpdate, user: Member, db: DB) -> Category:
    category = db.get(Category, category_id)
    if category is None or category.household_id != user.household_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    _commit_unique(db)
    return category
