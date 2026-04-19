<<<<<<< HEAD
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
=======
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, select, func
from sqlalchemy.orm import joinedload
from typing import Optional, List, Dict, Any
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)

from app.db.models import User, Request, Message
from app.schemas.user import UserCreate
from app.core.security import hash_password
from app.core.roles import Role


<<<<<<< HEAD
def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, user_data: UserCreate):
=======
async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    user = User(
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=Role.CITIZEN,
    )

    db.add(user)
<<<<<<< HEAD
    db.commit()
    db.refresh(user)
=======
    await db.commit()
    await db.refresh(user)
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)

    return user


<<<<<<< HEAD
def get_users(
    db: Session,
=======
async def get_users(
    db: AsyncSession,
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    skip: int = 0,
    limit: int = 20,
    role: Optional[Role] = None,
    roles: Optional[List[Role]] = None,
    search: Optional[str] = None,
<<<<<<< HEAD
):
=======
) -> Dict[str, Any]:
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    """
    Получить список пользователей с фильтрацией и пагинацией
    
    Параметры:
    - skip, limit: пагинация
    - role: фильтр по одной роли
    - roles: фильтр по нескольким ролям
    - search: поиск по имени, фамилии, email
    """
<<<<<<< HEAD
    query = db.query(User)
    
    if role:
        query = query.filter(User.role == role)
    
    if roles:
        query = query.filter(User.role.in_(roles))
    
    if search:
        query = query.filter(
=======
    query = select(User)
    
    if role:
        query = query.where(User.role == role)
    
    if roles:
        query = query.where(User.role.in_(roles))
    
    if search:
        query = query.where(
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
            or_(
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )
    
<<<<<<< HEAD
    total = query.count()

    # Текущая сортировка по роли (citizen → deputy → admin → superuser):
    users = query.order_by(User.role.asc()).offset(skip).limit(limit).all()
=======
    # Для count нужно выполнить отдельный запрос
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Текущая сортировка по роли (citizen → deputy → admin → superuser):
    query = query.order_by(User.role.asc()).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)

    """  АЛЬТЕРНАТИВНЫЕ ВАРИАНТЫ СОРТИРОВКИ:
     
     По дате регистрации (новые сверху):
<<<<<<< HEAD
     users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    
     По дате регистрации (старые сверху):
     users = query.order_by(User.created_at.asc()).offset(skip).limit(limit).all()
    
     По фамилии (А-Я):
     users = query.order_by(User.last_name.asc(), User.first_name.asc()).offset(skip).limit(limit).all()
    
     По фамилии (Я-А):
     users = query.order_by(User.last_name.desc()).offset(skip).limit(limit).all()
    
     По роли (citizen → deputy → admin → superuser):
     users = query.order_by(User.role.asc()).offset(skip).limit(limit).all()
    
     По роли + дате (сначала по роли, потом новые сверху):
     users = query.order_by(User.role.asc(), User.created_at.desc()).offset(skip).limit(limit).all()
    
     По email (А-Я):
     users = query.order_by(User.email.asc()).offset(skip).limit(limit).all()
=======
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
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    """

    return {
        "items": users,
        "total": total,
        "skip": skip,
        "limit": limit
    }


<<<<<<< HEAD
def update_user(db: Session, user_id: int, update_data: dict) -> Optional[User]:
    """Обновить данные пользователя"""
    user = db.query(User).filter(User.id == user_id).first()
=======
async def update_user(db: AsyncSession, user_id: int, update_data: dict) -> Optional[User]:
    """Обновить данные пользователя"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    if not user:
        return None
    
    for field, value in update_data.items():
        if hasattr(user, field) and value is not None:
            setattr(user, field, value)
    
<<<<<<< HEAD
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> bool:
    """
    Удалить пользователя полностью (вместе со всеми связанными данными)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    db.delete(user)
    db.commit()
=======
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
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    return True