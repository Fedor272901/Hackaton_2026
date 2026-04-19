"""
API эндпоинты для управления округами (Districts)

Этот модуль предоставляет полный CRUD для работы с округами:
- GET /districts/ — список всех округов (публично)
- GET /districts/{id} — детали округа с депутатами (публично)
- POST /districts/ — создание нового округа (только ADMIN)
- PUT /districts/{id} — обновление округа (только ADMIN)
- DELETE /districts/{id} — удаление округа (только ADMIN)

ВАЖНО:
- Создание/обновление/удаление доступно ТОЛЬКО администраторам
- Депутаты и граждане могут только просматривать округа
- Проверка прав реализована через Depends(require_admin)
- Все ошибки возвращают корректные HTTP статусы (404, 403, 422)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.db.database import get_db
from app.db.models import User, District, Deputy

# Схемы Pydantic для валидации входных/выходных данных
from app.schemas.district import District, DistrictCreate, DistrictUpdate, DistrictWithDeputies
from app.schemas.deputy import Deputy as DeputySchema

# Refactored: direct CRUD call replaced by Service Layer for transactional safety
from app.services import DistrictService

# Механизм проверки ролей — возвращает 403 если пользователь не ADMIN
from app.core.permissions import require_admin

# Для получения текущего пользователя (JWT токен декодируется автоматически)
from app.core.dependencies import get_current_active_user


router = APIRouter()


# ========================
# Dependency Injection for Services
# ========================

async def get_district_service(session: AsyncSession = Depends(get_db)) -> DistrictService:
    """
    Get DistrictService instance with database session.
    
    This dependency is used to inject the service into endpoint handlers.
    The service manages its own transactions for write operations.
    
    Args:
        session: Database session from get_db dependency
    
    Returns:
        DistrictService instance initialized with the session
    """
    return DistrictService(session)


# ========================
# PUBLIC ENDPOINTS (доступны всем)
# ========================

@router.get("/", response_model=List[District])
async def read_districts(
    skip: int = 0,
    limit: int = 100,
    service: DistrictService = Depends(get_district_service)
):
    """
    Получить список всех округов с пагинацией

    Этот эндпоинт доступен БЕЗ аутентификации.
    Используется для отображения списка округов на публичных страницах.

    Параметры:
    - skip: количество записей для пропуска (пагинация)
    - limit: максимальное количество записей (защита от перегрузки)

    Возвращает:
    - Список объектов District с полями: id, name, description
    """
    # Refactored: direct CRUD call replaced by Service Layer for transactional safety
    districts = await service.get_districts(skip=skip, limit=limit)
    return districts


@router.get("/{district_id}", response_model=DistrictWithDeputies)
async def read_district(
    district_id: int,
    service: DistrictService = Depends(get_district_service)
):
    """
    Получить данные округа по ID вместе со списком депутатов

    Доступно БЕЗ аутентификации. Используется на страницах округов.

    Параметры:
    - district_id: уникальный идентификатор округа

    Возвращает:
    - Объект DistrictWithDeputies содержащий:
      * Данные округа (id, name, description)
      * Список депутатов (deputies)

    Ошибки:
    - 404: Если округ с таким ID не найден
    """
    # Refactored: direct CRUD call replaced by Service Layer for transactional safety
    district = await service.get_district_with_deputies(district_id)

    if not district:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Округ с ID {district_id} не найден"
        )

    return district


@router.get("/{district_id}/deputies", response_model=List[DeputySchema])
async def read_deputies_by_district(
    district_id: int,
    service: DistrictService = Depends(get_district_service),
):
    """
    Получить список депутатов конкретного округа

    Вспомогательный эндпоинт для получения только депутатов без данных округа.
    Может использоваться для AJAX-запросов при фильтрации.

    Параметры:
    - district_id: ID округа

    Возвращает:
    - Список объектов Deputy с данными депутатов

    Ошибки:
    - 404: Если округ не найден
    """
    # Сначала проверяем существование округа
    district = await service.get_district(district_id)

    if not district:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Округ с ID {district_id} не найден"
        )

    # Refactored: direct CRUD call replaced by Service Layer for transactional safety
    deputies = await service.get_deputies_by_district(district_id)
    return deputies


# ========================
# ADMIN ONLY ENDPOINTS (CRUD операции)
# ========================

@router.post("/", response_model=District, status_code=status.HTTP_201_CREATED)
async def create_district(
    district_data: DistrictCreate,
    service: DistrictService = Depends(get_district_service),
    current_user: User = Depends(require_admin)
):
    """
    Создать новый округ

    ДОСТУП: Только ADMIN (проверка через require_admin)

    Этот эндпоинт позволяет администратору создать новый избирательный округ.
    Данные валидируются через схему DistrictCreate (Pydantic).

    Параметры тела запроса:
    - name: название округа (обязательно, строка)
    - description: описание округа (опционально, текст)

    Возвращает:
    - Созданный объект District с присвоенным ID

    Ошибки:
    - 403: Если пользователь не администратор
    - 422: Если данные не прошли валидацию Pydantic

    Пример запроса:
    POST /api/v1/districts/
    {
        "name": "Центральный округ",
        "description": "Включает центр города"
    }
    """
    # Refactored: direct CRUD call replaced by Service Layer for transactional safety
    # Service handles validation and creation atomically
    new_district = await service.create_district(district_data)

    return new_district


@router.put("/{district_id}", response_model=District)
async def update_district(
    district_id: int,
    district_data: DistrictUpdate,
    service: DistrictService = Depends(get_district_service),
    current_user: User = Depends(require_admin)
):
    """
    Обновить данные существующего округа

    ДОСТУП: Только ADMIN

    Позволяет изменить название или описание округа.
    Использется частичное обновление — меняются только переданные поля.

    Параметры пути:
    - district_id: ID обновляемого округа

    Параметры тела запроса (все опциональны):
    - name: новое название округа
    - description: новое описание

    Возвращает:
    - Обновлённый объект District

    Ошибки:
    - 403: Если пользователь не администратор
    - 404: Если округ не найден
    - 400: Если новое название занято другим округом
    - 422: Если данные не прошли валидацию
    """
    try:
        # Refactored: direct CRUD call replaced by Service Layer for transactional safety
        updated_district = await service.update_district(district_id, district_data)

        if not updated_district:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Округ с ID {district_id} не найден"
            )

        return updated_district

    except HTTPException:
        # Re-raise HTTP exceptions from service
        raise
    except Exception as e:
        # Handle any other errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{district_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_district(
    district_id: int,
    service: DistrictService = Depends(get_district_service),
    current_user: User = Depends(require_admin)
):
    """
    Удалить округ

    ДОСТУП: Только ADMIN

    ВНИМАНИЕ: Перед удалением необходимо:
    1. Переназначить всех депутатов этого округа в другие округа ИЛИ удалить их записи
    2. Решить судьбу обращений жителей этого округа

    Если в округе есть депутаты, удаление будет заблокировано (защита от случайного удаления).

    Параметры пути:
    - district_id: ID удаляемого округа

    Возвращает:
    - 204 No Content при успешном удалении

    Ошибки:
    - 403: Если пользователь не администратор
    - 404: Если округ не найден
    - 400: Если в округе есть депутаты (требуется ручное вмешательство)
    """
    try:
        # Refactored: direct CRUD call replaced by Service Layer for transactional safety
        success = await service.delete_district(district_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Округ с ID {district_id} не найден"
            )

        # Return 204 No Content (empty body)
        return None

    except HTTPException:
        # Re-raise HTTP exceptions from service
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
