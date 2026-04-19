from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.schemas.user import (
    UserCreate, 
    UserUpdate,
    UserResponse,
    UserListResponse
)
# Refactored: direct CRUD call replaced by Service Layer for transactional safety
from app.services.user_service import UserService
from app.db.database import get_db
from app.db.models import User
from app.core.dependencies import get_current_active_user
from app.core.permissions import require_admin
from app.core.roles import Role
from app.core.config import settings


router = APIRouter()


# ========================
# Dependency Injection for Services
# ========================

async def get_user_service(session: AsyncSession = Depends(get_db)) -> UserService:
    """
    Get UserService instance with database session.
    
    This dependency is used to inject the service into endpoint handlers.
    The service manages its own transactions for write operations.
    
    Args:
        session: Database session from get_db dependency
    
    Returns:
        UserService instance initialized with the session
    """
    return UserService(session)


@router.post("/")
async def create_user_endpoint(user: UserCreate, service: UserService = Depends(get_user_service)):
    # Refactored: direct CRUD call replaced by Service Layer for transactional safety
    try:
        return await service.create_user(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me")
async def get_me(current_user=Depends(get_current_active_user)):

    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role.name if hasattr(current_user.role, 'name') else current_user.role,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
    }


@router.get("/", response_model=UserListResponse)
async def get_users_list(
    skip: int = Query(0, ge=0),
    # Magic number extracted to config for environment flexibility
    limit: int = Query(settings.DEFAULT_LIMIT, ge=1, le=settings.MAX_LIMIT),
    role: Optional[Role] = Query(None),
    search: Optional[str] = Query(None),
    service: UserService = Depends(get_user_service),
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
    # Refactored: direct CRUD call replaced by Service Layer for transactional safety
    return await service.get_users(
        skip=skip,
        limit=limit,
        role=role,
        search=search
    )


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    service: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Обновить данные пользователя
    
    Доступно только администраторам.
    """
    # Refactored: direct CRUD call replaced by Service Layer for transactional safety
    target_user = await service.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(404, "Пользователь не найден")
    
    if target_user.role == Role.SUPERUSER:
        raise HTTPException(403, "Нельзя изменить SUPERUSER через API")
    
    if target_user.role == Role.ADMIN and user_update.role != Role.ADMIN:
        # Count admins using async query
        from sqlalchemy import select, func
        result = await db.execute(
            select(func.count()).select_from(User).where(User.role == Role.ADMIN)
        )
        admins_count = result.scalar()
        if admins_count <= 1:
            raise HTTPException(400, "Нельзя снять роль у последнего администратора")
    
    update_data = user_update.model_dump(exclude_unset=True)
    try:
        updated_user = await service.update_user(user_id, update_data)
        return updated_user
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_admin)
):
    """
    Удалить пользователя
    
    Доступно только администраторам.
    Удаление полное, без возможности восстановления.
    """
    # Refactored: direct CRUD call replaced by Service Layer for transactional safety
    target_user = await service.get_user_by_id(user_id)
    
    if not target_user:
        raise HTTPException(404, "Пользователь не найден")
    
    if target_user.id == current_user.id:
        raise HTTPException(400, "Нельзя удалить самого себя")
    
    if target_user.role == Role.SUPERUSER:
        raise HTTPException(403, "Нельзя удалить SUPERUSER через API")
    
    try:
        success = await service.delete_user(user_id)
        if not success:
            raise HTTPException(404, "Пользователь не найден")
    except ValueError as e:
        raise HTTPException(400, str(e))
    
    return None