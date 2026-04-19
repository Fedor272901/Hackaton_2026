from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, select, func
from sqlalchemy.orm import joinedload
from typing import Optional, List, Dict, Any

from app.db.models import User, Request, Message
from app.schemas.user import UserCreate
from app.core.security import hash_password
from app.core.roles import Role


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
    user = User(
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=Role.CITIZEN,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


async def get_users(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    role: Optional[Role] = None,
    roles: Optional[List[Role]] = None,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Получить список пользователей с фильтрацией и пагинацией
    
    Параметры:
    - skip, limit: пагинация
    - role: фильтр по одной роли
    - roles: фильтр по нескольким ролям
    - search: поиск по имени, фамилии, email
    """
    query = select(User)
    
    if role:
        query = query.where(User.role == role)
    
    if roles:
        query = query.where(User.role.in_(roles))
    
    if search:
        query = query.where(
            or_(
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )
    
    # Для count нужно выполнить отдельный запрос
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Текущая сортировка по роли (citizen → deputy → admin → superuser):
    query = query.order_by(User.role.asc()).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    """  АЛЬТЕРНАТИВНЫЕ ВАРИАНТЫ СОРТИРОВКИ:
     
     По дате регистрации (новые сверху):
     query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    
     По дате регистрации (старые сверху):
     query = query.order_by(User.created_at.asc()).offset(skip).limit(limit)
    
     По фамилии (А-Я):
     query = query.order_by(User.last_name.asc(), User.first_name.asc()).offset(skip).limit(limit)
    
     По фамилии (Я-А):
     query = query.order_by(User.last_name.desc()).offset(skip).limit(limit)
    
     По роли (citizen → deputy → admin → superuser):
     query = query.order_by(User.role.asc()).offset(skip).limit(limit)
    
     По роли + дате (сначала по роли, потом новые сверху):
     query = query.order_by(User.role.asc(), User.created_at.desc()).offset(skip).limit(limit)
    
     По email (А-Я):
     query = query.order_by(User.email.asc()).offset(skip).limit(limit)
    """

    return {
        "items": users,
        "total": total,
        "skip": skip,
        "limit": limit
    }


async def update_user(db: AsyncSession, user_id: int, update_data: dict) -> Optional[User]:
    """Обновить данные пользователя"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        return None
    
    for field, value in update_data.items():
        if hasattr(user, field) and value is not None:
            setattr(user, field, value)
    
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user_id: int) -> bool:
    """
    Удалить пользователя полностью (вместе со всеми связанными данными)
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        return False
    
    await db.delete(user)
    await db.commit()
    return True