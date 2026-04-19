"""
API эндпоинты для управления депутатами (Deputies)

Этот модуль предоставляет полный CRUD для работы с депутатами:
- GET /deputies/ — список всех депутатов (публично)
- GET /deputies/{id} — детали депутата (публично)
- GET /deputies/district/{district_id} — депутаты конкретного округа (публично)
- POST /deputies/ — назначение нового депутата (только ADMIN)
- PUT /deputies/{id} — обновление данных депутата (только ADMIN)
- DELETE /deputies/{id} — снятие полномочий депутата (только ADMIN)

ВАЖНО:
- Назначение/обновление/снятие доступно ТОЛЬКО администраторам
- Депутаты и граждане могут только просматривать информацию о депутатах
- Проверка прав реализована через Depends(require_admin)
- При назначении депутата проверяется что пользователь имеет роль "deputy"
- При удалении депутата необходимо сначала переназначить его обращения

JWT Аутентификация:
- Все эндпоинты требуют валидный JWT токен в заголовке Authorization: Bearer <token>
- Токен декодируется автоматически через get_current_active_user
- Роль проверяется через require_admin для мутационных операций
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.db.database import get_db
from app.db.models import User, Deputy, District

# Схемы Pydantic для валидации входных/выходных данных
from app.schemas.deputy import Deputy, DeputyCreate, DeputyUpdate

# Refactored: direct CRUD call replaced by Service Layer for transactional safety
from app.services import DeputyService

# Механизм проверки ролей — возвращает 403 если пользователь не ADMIN
from app.core.permissions import require_admin

# Для получения текущего пользователя (JWT токен декодируется автоматически)
from app.core.dependencies import get_current_active_user
from app.core.config import settings

router = APIRouter()


# ========================
# Dependency Injection for Services
# ========================

async def get_deputy_service(session: AsyncSession = Depends(get_db)) -> DeputyService:
    """
    Get DeputyService instance with database session.
    
    This dependency is used to inject the service into endpoint handlers.
    The service manages its own transactions for write operations.
    
    Args:
        session: Database session from get_db dependency
    
    Returns:
        DeputyService instance initialized with the session
    """
    return DeputyService(session)


# ========================
# PUBLIC ENDPOINTS (доступны всем авторизованным)
# ========================

@router.get("/", response_model=List[Deputy])
async def read_deputies(
    skip: int = Query(0, ge=0, description="Количество записей для пропуска"),
    # Magic number extracted to config for environment flexibility
    limit: int = Query(settings.DEFAULT_LIMIT, ge=1, le=settings.MAX_LIMIT_DEPUTIES, description="Максимальное количество записей"),
    district_id: Optional[int] = Query(None, ge=1, description="Фильтр по ID округа"),
    service: DeputyService = Depends(get_deputy_service),
    current_user: User = Depends(get_current_active_user)  # Требуется авторизация
):
    """
    Получить список всех депутатов с пагинацией и фильтрацией

    ДОСТУП: Любой авторизованный пользователь

    Этот эндпоинт используется для отображения списка депутатов на страницах:
    - Публичный каталог депутатов
    - Фильтрация по округам
    - Поиск депутатов для назначения на обращения

    Параметры query string:
    - skip: количество записей для пропуска (пагинация, по умолчанию 0)
    - limit: максимальное количество записей (по умолчанию 100, макс 200)
    - district_id: опциональный фильтр по ID округа

    Возвращает:
    - Список объектов Deputy с полями:
      * id, user_id, district_id
      * office_phone, office_address
      * appointed_at
      * Вложенные объекты user и district

    Пример запроса:
    GET /api/v1/deputies/?skip=0&limit=20&district_id=5
    """
    # Refactored: direct CRUD call replaced by Service Layer for transactional safety
    deputies = await service.get_deputies(
        skip=skip,
        limit=limit,
        district_id=district_id
    )

    return deputies


@router.get("/{deputy_id}", response_model=Deputy)
async def read_deputy(
    deputy_id: int = Path(..., ge=1, description="ID депутата"),
    service: DeputyService = Depends(get_deputy_service),
    current_user: User = Depends(get_current_active_user)  # Требуется авторизация
):
    """
    Получить страницу депутата по ID

    ДОСТУП: Любой авторизованный пользователь

    Используется для отображения страницы профиля депутата с полной информацией:
    - Данные пользователя (ФИО, email)
    - Информация об округе
    - Контактные данные (телефон, адрес)
    - Дата назначения

    Параметры пути:
    - deputy_id: уникальный идентификатор записи депутата

    Возвращает:
    - Объект Deputy со всеми связями (user, district)

    Ошибки:
    - 404: Если депутат с таким ID не найден

    Пример запроса:
    GET /api/v1/deputies/42
    """
    # Refactored: direct CRUD call replaced by Service Layer for transactional safety
    deputy = await service.get_deputy(deputy_id)

    if not deputy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Депутат с ID {deputy_id} не найден"
        )

    return deputy


@router.get("/district/{district_id}", response_model=List[Deputy])
async def read_deputies_by_district(
    district_id: int = Path(..., ge=1, description="ID округа"),
    service: DeputyService = Depends(get_deputy_service),
    current_user: User = Depends(get_current_active_user)  # Требуется авторизация
):
    """
    Получить всех депутатов конкретного округа

    ДОСТУП: Любой авторизованный пользователь

    Специализированный эндпоинт для быстрого получения депутатов округа.
    Может использоваться на странице округа или при выборе депутата для назначения.

    Параметры пути:
    - district_id: ID округа

    Возвращает:
    - Список объектов Deputy принадлежащих этому округу
    - Пустой список если в округе нет депутатов

    Ошибки:
    - 404: Если округ с таким ID не найден

    Пример запроса:
    GET /api/v1/deputies/district/5
    """
    # Проверяем существование округа через сервис (будет добавлен в DistrictService)
    from app.services import DistrictService
    district_service = DistrictService(service.session)
    district = await district_service.get_district(district_id)

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

@router.post("/", response_model=Deputy, status_code=status.HTTP_201_CREATED)
async def create_deputy(
    deputy_data: DeputyCreate,
    service: DeputyService = Depends(get_deputy_service),
    current_user: User = Depends(require_admin)  # Только администраторы
):
    """
    Назначить нового депутата

    ДОСТУП: Только ADMIN (проверка через require_admin)

    Этот эндпоинт позволяет администратору назначить пользователя на должность депутата
    и прикрепить его к конкретному избирательному округу.

    ПРЕДУСЛОВИЯ (проверяются перед вызовом):
    1. Пользователь с user_id должен существовать
    2. Пользователь должен иметь роль "deputy" в таблице users
    3. Пользователь не должен быть уже действующим депутатом
    4. Округ с district_id должен существовать

    Параметры тела запроса:
    - user_id: ID пользователя которого назначают депутатом (обязательно)
    - district_id: ID округа закрепления (обязательно)
    - office_phone: служебный телефон (опционально)
    - office_address: служебный адрес (опционально)

    Возвращает:
    - Созданный объект Deputy с полями:
      * id, user_id, district_id
      * office_phone, office_address
      * appointed_at (автоматически устанавливается в текущее время)

    Ошибки:
    - 403: Если пользователь не администратор
    - 400: Если пользователь уже является депутатом
    - 400: Если пользователь не имеет роль "deputy"
    - 404: Если округ не найден
    - 422: Если данные не прошли валидацию Pydantic

    Пример запроса:
    POST /api/v1/deputies/
    {
        "user_id": 15,
        "district_id": 3,
        "office_phone": "+7 (495) 123-45-67",
        "office_address": "ул. Ленина, д. 1"
    }
    """
    # Создаём запись депутата через сервис (все проверки внутри)
    # Refactored: direct CRUD call replaced by Service Layer for transactional safety
    new_deputy = await service.create_deputy(
        deputy_data=deputy_data,
        appointed_by_user_id=current_user.id
    )

    return new_deputy


@router.put("/{deputy_id}", response_model=Deputy)
async def update_deputy(
    deputy_id: int,
    deputy_data: DeputyUpdate,
    service: DeputyService = Depends(get_deputy_service),
    current_user: User = Depends(require_admin)  # Только администраторы
):
    """
    Обновить данные депутата

    ДОСТУП: Только ADMIN

    Позволяет администратору изменить данные депутата:
    - Перевести в другой округ (change district_id)
    - Обновить служебный телефон
    - Обновить служебный адрес

    ВАЖНО:
    - При смене округа все обращения депутата остаются за ним
    - Новый округ должен существовать

    Параметры пути:
    - deputy_id: ID обновляемой записи депутата

    Параметры тела запроса (все опциональны):
    - user_id: новый ID пользователя (редко меняется)
    - district_id: новый ID округа для перевода
    - office_phone: новый служебный телефон
    - office_address: новый служебный адрес

    Возвращает:
    - Обновлённый объект Deputy

    Ошибки:
    - 403: Если пользователь не администратор
    - 404: Если депутат не найден
    - 400: Если новый округ не найден
    - 422: Если данные не прошли валидацию

    Пример запроса:
    PUT /api/v1/deputies/42
    {
        "district_id": 7,
        "office_phone": "+7 (495) 987-65-43"
    }
    """
    # Проверяем существование депутата
    # Refactored: direct CRUD call replaced by Service Layer for transactional safety
    existing_deputy = await service.get_deputy(deputy_id)

    if not existing_deputy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Депутат с ID {deputy_id} не найден"
        )

    try:
        # Выполняем обновление через сервис
        # Refactored: direct CRUD call replaced by Service Layer for transactional safety
        updated_deputy = await service.update_deputy(
            deputy_id=deputy_id,
            deputy_data=deputy_data
        )

        return updated_deputy

    except ValueError as e:
        # Ошибка из сервиса (например, округ не найден)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{deputy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deputy(
    deputy_id: int,
    service: DeputyService = Depends(get_deputy_service),
    current_user: User = Depends(require_admin)  # Только администраторы
):
    """
    Снять полномочия депутата (удалить запись)

    ДОСТУП: Только ADMIN

    КРИТИЧЕСКИ ВАЖНО:
    Перед удалением депутата необходимо:
    1. Переназначить все его обращения на других депутатов ИЛИ снять назначения
    2. Убедиться что нет активных процессов с участием депутата

    Если у депутата есть назначенные обращения, удаление будет заблокировано.
    Используйте эндпоинт переназначения обращений перед удалением.

    Параметры пути:
    - deputy_id: ID удаляемой записи депутата

    Возвращает:
    - 204 No Content при успешном удалении

    Ошибки:
    - 403: Если пользователь не администратор
    - 404: Если депутат не найден
    - 400: Если у депутата есть назначенные обращения (требуется ручное вмешательство)

    Пример запроса:
    DELETE /api/v1/deputies/42

    Последовательность действий для корректного удаления:
    1. GET /api/v1/requests/?assigned_deputy_id={deputy_id} — получить все обращения
    2. POST /api/v1/requests/{id}/assign/{new_deputy_id} — переназначить каждое
    3. DELETE /api/v1/deputies/{deputy_id} — удалить депутата
    """
    # Проверяем существование депутата
    # Refactored: direct CRUD call replaced by Service Layer for transactional safety
    deputy = await service.get_deputy(deputy_id)

    if not deputy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Депутат с ID {deputy_id} не найден"
        )

    # Проверяем есть ли назначенные обращения (защита от удаления с связями)
    from app.db.models import Request
    from sqlalchemy import select, func
    result = await service.session.execute(
        select(func.count()).select_from(Request).where(Request.assigned_deputy_id == deputy_id)
    )
    assigned_requests_count = result.scalar()

    if assigned_requests_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Невозможно снять депутата: у него есть назначенных обращений: {assigned_requests_count}. Сначала переназначьте обращения."
        )

    # Удаляем депутата через сервис
    # Refactored: direct CRUD call replaced by Service Layer for transactional safety
    success = await service.delete_deputy(deputy_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при удалении депутата"
        )

    # Возвращаем 204 No Content (пустое тело ответа)
    return None


@router.get("/me", response_model=Deputy)
async def read_my_deputy_profile(
    service: DeputyService = Depends(get_deputy_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить профиль текущего пользователя как депутата

    ДОСТУП: Любой авторизованный пользователь (но только депутаты получат данные)

    Удобный эндпоинт для депутата чтобы получить свой профиль без знания своего deputy_id.
    Использует ID текущего пользователя из JWT токена.

    Возвращает:
    - Объект Deputy если пользователь является депутатом

    Ошибки:
    - 404: Если пользователь не является депутатом (нет записи в таблице deputies)

    Пример запроса:
    GET /api/v1/deputies/me
    Authorization: Bearer <jwt_token>
    """
    # Refactored: direct CRUD call replaced by Service Layer for transactional safety
    deputy = await service.get_deputy_by_user_id(current_user.id)

    if not deputy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вы не являетесь депутатом"
        )

    return deputy