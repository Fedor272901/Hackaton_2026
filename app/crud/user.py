from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List

from app.db.models import User, Request, Message
from app.schemas.user import UserCreate
from app.core.security import hash_password
from app.core.roles import Role


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, user_data: UserCreate):
    user = User(
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=Role.CITIZEN,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def get_users(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    role: Optional[Role] = None,
    roles: Optional[List[Role]] = None,
    search: Optional[str] = None,
):
    """
    Получить список пользователей с фильтрацией и пагинацией
    
    Параметры:
    - skip, limit: пагинация
    - role: фильтр по одной роли
    - roles: фильтр по нескольким ролям
    - search: поиск по имени, фамилии, email
    """
    query = db.query(User)
    
    if role:
        query = query.filter(User.role == role)
    
    if roles:
        query = query.filter(User.role.in_(roles))
    
    if search:
        query = query.filter(
            or_(
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )
    
    total = query.count()

    # Текущая сортировка по роли (citizen → deputy → admin → superuser):
    users = query.order_by(User.role.asc()).offset(skip).limit(limit).all()

    """  АЛЬТЕРНАТИВНЫЕ ВАРИАНТЫ СОРТИРОВКИ:
     
     По дате регистрации (новые сверху):
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
    """

    return {
        "items": users,
        "total": total,
        "skip": skip,
        "limit": limit
    }


def update_user(db: Session, user_id: int, update_data: dict) -> Optional[User]:
    """Обновить данные пользователя"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    
    for field, value in update_data.items():
        if hasattr(user, field) and value is not None:
            setattr(user, field, value)
    
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
    return True