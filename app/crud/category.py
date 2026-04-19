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
    
    category = models.RequestCategory(
        name=data.name,
        description=data.description,
    )
    db.add(category)
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
    if category is None:
        return None

    if data.name is not None:
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
        category.name = data.name
    if data.description is not None:
        category.description = data.description

    await db.commit()
    await db.refresh(category)
    return category


async def delete_category(db: AsyncSession, category_id: int):
    category = await get_category(db, category_id)
    if category is None:
        return False
    await db.delete(category)
    await db.commit()
    return True
