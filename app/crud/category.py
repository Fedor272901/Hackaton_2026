from sqlalchemy.orm import Session
from app.db import models


def create_category(db: Session, data):
    category = models.RequestCategory(
        name=data.name,
        description=data.description,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def get_category(db: Session, category_id: int):
    return db.query(models.RequestCategory).filter(
        models.RequestCategory.id == category_id
    ).first()


def get_categories(db: Session):
    return db.query(models.RequestCategory).order_by(
        models.RequestCategory.id
    ).all()


def update_category(db: Session, category_id: int, data):
    category = get_category(db, category_id)
    if category is None:
        return None

    if data.name is not None:
        category.name = data.name
    if data.description is not None:
        category.description = data.description

    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: int):
    category = get_category(db, category_id)
    if category is None:
        return False
    db.delete(category)
    db.commit()
    return True
