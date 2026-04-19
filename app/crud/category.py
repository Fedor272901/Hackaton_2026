<<<<<<< HEAD
from sqlalchemy.orm import Session
from app.db import models


def create_category(db: Session, data):
=======
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db import models


async def create_category(db: AsyncSession, data):
    # Проверка на дубликат имени
    result = await db.execute(
        select(models.RequestCategory).where(models.RequestCategory.name == data.name)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise ValueError(f"Категория с именем '{data.name}' уже существует")
    
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    category = models.RequestCategory(
        name=data.name,
        description=data.description,
    )
    db.add(category)
<<<<<<< HEAD
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
=======
    await db.commit()
    await db.refresh(category)
    return category


async def get_category(db: AsyncSession, category_id: int):
    result = await db.execute(
        select(models.RequestCategory).where(models.RequestCategory.id == category_id)
    )
    return result.scalar_one_or_none()


async def get_categories(db: AsyncSession):
    result = await db.execute(
        select(models.RequestCategory).order_by(models.RequestCategory.id)
    )
    return result.scalars().all()


async def update_category(db: AsyncSession, category_id: int, data):
    category = await get_category(db, category_id)
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    if category is None:
        return None

    if data.name is not None:
<<<<<<< HEAD
=======
        # Проверка на дубликат имени (если имя меняется)
        if data.name != category.name:
            result = await db.execute(
                select(models.RequestCategory).where(
                    models.RequestCategory.name == data.name,
                    models.RequestCategory.id != category_id
                )
            )
            if result.scalar_one_or_none():
                raise ValueError(f"Категория с именем '{data.name}' уже существует")
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
        category.name = data.name
    if data.description is not None:
        category.description = data.description

<<<<<<< HEAD
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: int):
    category = get_category(db, category_id)
    if category is None:
        return False
    db.delete(category)
    db.commit()
=======
    await db.commit()
    await db.refresh(category)
    return category


async def delete_category(db: AsyncSession, category_id: int):
    category = await get_category(db, category_id)
    if category is None:
        return False
    await db.delete(category)
    await db.commit()
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    return True
