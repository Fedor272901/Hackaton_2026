from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.schemas.user import (
    UserCreate, 
    UserUpdate,
    UserResponse,
    UserListResponse
)
from app.crud import user as user_crud
from app.db.database import get_db
from app.db.models import User
from app.core.dependencies import get_current_active_user
from app.core.permissions import require_admin
from app.core.roles import Role


router = APIRouter()


@router.post("/")
def create_user_endpoint(user: UserCreate, db: Session = Depends(get_db)):

    existing_user = user_crud.get_user_by_email(db, user.email)

    if existing_user:
        raise HTTPException(
            status_code=400, detail="User with this email already exists"
        )

    return user_crud.create_user(db, user)


@router.get("/me")
def get_me(current_user=Depends(get_current_active_user)):

    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
    }


@router.get("/", response_model=UserListResponse)
def get_users_list(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    role: Optional[Role] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Получить список всех пользователей с фильтрацией и пагинацией.
    Доступно только администраторам.

    Параметры запроса (Query Parameters):
    - **skip** (int, по умолчанию 0): сколько записей пропустить от начала.
    - **limit** (int, по умолчанию 20, максимум 100): количество записей на странице.
    - **role** (str, опционально): фильтр по роли пользователя.
        Возможные значения: "citizen", "deputy", "admin", "superuser".
    - **search** (str, опционально): поиск по имени, фамилии или email (регистронезависимый).

    Примеры запросов:
    - Базовый список (первая страница):
      GET /users?skip=0&limit=20

    - Только администраторы:
      GET /users?role=admin

    - Поиск по строке "ivan":
      GET /users?search=ivan

    - Комбинированный запрос (депутаты, содержащие "petr", вторая страница):
      GET /users?role=deputy&search=petr&skip=20&limit=20

    Ответ (UserListResponse):
    {
      "items": [
        {
          "id": 1,
          "first_name": "Иван",
          "last_name": "Петров",
          "email": "ivan@mail.ru",
          "role": "citizen",
          "created_at": "2026-01-15T10:30:00"
        }
      ],
      "total": 42,
      "skip": 0,
      "limit": 20
    }
    """
    return user_crud.get_users(
        db=db,
        skip=skip,
        limit=limit,
        role=role,
        search=search
    )


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Обновить данные пользователя
    
    Доступно только администраторам.
    """
    target_user = user_crud.get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(404, "Пользователь не найден")
    
    if target_user.role == Role.SUPERUSER:
        raise HTTPException(403, "Нельзя изменить SUPERUSER через API")
    
    if target_user.role == Role.ADMIN and user_update.role != Role.ADMIN:
        admins_count = db.query(User).filter(User.role == Role.ADMIN).count()
        if admins_count <= 1:
            raise HTTPException(400, "Нельзя снять роль у последнего администратора")
    
    update_data = user_update.model_dump(exclude_unset=True)
    updated_user = user_crud.update_user(db, user_id, update_data)
    
    return updated_user


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Удалить пользователя
    
    Доступно только администраторам.
    Удаление полное, без возможности восстановления.
    """
    target_user = user_crud.get_user_by_id(db, user_id)
    
    if not target_user:
        raise HTTPException(404, "Пользователь не найден")
    
    if target_user.id == current_user.id:
        raise HTTPException(400, "Нельзя удалить самого себя")
    
    if target_user.role == Role.SUPERUSER:
        raise HTTPException(403, "Нельзя удалить SUPERUSER через API")
    
    user_crud.delete_user(db, user_id)
    
    return None