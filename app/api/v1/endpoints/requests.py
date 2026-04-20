<<<<<<< HEAD
=======
<<<<<<< HEAD
# app/api/v1/endpoints/requests.py

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.config import SECRET_KEY, ALGORITHM
=======
>>>>>>> front/dev
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
from app.db.database import get_db
from app.db.models import User, Request, Deputy
from app.core.roles import Role
from app.schemas.requests import (
    RequestCreate,
    RequestUpdate,
    RequestResponse,
    RequestListResponse,
    RequestStatusResponse,
    RequestCategoryResponse,
    MessageCreate,
    MessageResponse,
    StatusHistoryResponse,
    StatisticsResponse
)
<<<<<<< HEAD
# Refactored: direct CRUD call replaced by Service Layer for transactional safety
from app.services import RequestService
=======
<<<<<<< HEAD
from app.crud import request as request_crud
=======
# Refactored: direct CRUD call replaced by Service Layer for transactional safety
from app.services import RequestService
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
from app.core.dependencies import get_current_active_user
# ИСПОЛЬЗУЕМ ГОТОВЫЕ ПРОВЕРКИ ИЗ permissions.py
from app.core.permissions import require_admin, require_admin_or_deputy
from app.core.access import can_view_request

# ЗАЩИТА ОТ СПАМА
from app.core.rate_limit import rate_limiter
from app.core.spam_filter import spam_filter

<<<<<<< HEAD
# Настройки пагинации из config
from app.core.config import settings
=======
<<<<<<< HEAD
=======
# Настройки пагинации из config
from app.core.config import settings
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev


router = APIRouter()


<<<<<<< HEAD
=======
<<<<<<< HEAD
def get_request_or_404(db: Session, request_id: int) -> Request:
      request = request_crud.get_request_by_id(db, request_id)
      if not request:
          raise HTTPException(404, f"Обращение с ID {request_id} не найдено")
      return request
=======
>>>>>>> front/dev
# ========================
# Dependency Injection for Services
# ========================

async def get_request_service(session: AsyncSession = Depends(get_db)) -> RequestService:
    """
    Get RequestService instance with database session.
    
    This dependency is used to inject the service into endpoint handlers.
    The service manages its own transactions for write operations.
    
    Args:
        session: Database session from get_db dependency
    
    Returns:
        RequestService instance initialized with the session
    """
    return RequestService(session)


async def get_request_or_404(service: RequestService, request_id: int) -> Request:
    """Helper to get request or raise 404."""
    request = await service.get_request_by_id(request_id)
    if not request:
        raise HTTPException(404, f"Обращение с ID {request_id} не найдено")
    return request
<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev

# ---------------------------
# Справочные эндпоинты (всем авторизованным)
# ---------------------------
@router.get("/statuses", response_model=List[RequestStatusResponse])
<<<<<<< HEAD
=======
<<<<<<< HEAD
def get_statuses(db: Session = Depends(get_db)):
    """Получить список всех возможных статусов обращений"""
    return request_crud.get_request_statuses(db)


@router.get("/categories", response_model=List[RequestCategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    """Получить список всех категорий обращений"""
    return request_crud.get_request_categories(db)
=======
>>>>>>> front/dev
async def get_statuses(service: RequestService = Depends(get_request_service)):
    """Получить список всех возможных статусов обращений"""
    # Refactored: direct CRUD call replaced by Service Layer for transactional safety
    return await service.get_request_statuses()


@router.get("/categories", response_model=List[RequestCategoryResponse])
async def get_categories(service: RequestService = Depends(get_request_service)):
    """Получить список всех категорий обращений"""
    # Refactored: direct CRUD call replaced by Service Layer for transactional safety
    return await service.get_request_categories()
<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev


# ---------------------------
# Основные эндпоинты обращений
# ---------------------------
@router.post("/", response_model=RequestResponse, status_code=201)
<<<<<<< HEAD
async def create_request(
    request_data: RequestCreate,
    service: RequestService = Depends(get_request_service),
=======
<<<<<<< HEAD
def create_request(
    request_data: RequestCreate,
    db: Session = Depends(get_db),
=======
async def create_request(
    request_data: RequestCreate,
    service: RequestService = Depends(get_request_service),
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
    current_user: User = Depends(get_current_active_user)
):
    """
    Создать новое обращение

    Доступно для всех авторизованных пользователей.
    """
    # ЗАЩИТА 1: Rate Limit (5 обращений в час)
    if not rate_limiter.check(current_user.id):
        raise HTTPException(
            status_code=429,
            detail="Лимит исчерпан: максимум 5 обращений в сутки"
        )

    # ЗАЩИТА 2: Спам-фильтр
    full_text = f"{request_data.title} {request_data.description}"
    is_spam, reason = spam_filter.check(full_text)
    if is_spam:
        raise HTTPException(
            status_code=400,
            detail=f"Обращение отклонено: {reason}"
        )

    # ЗАЩИТА 3: Проверка дубликатов
<<<<<<< HEAD
    # Refactored: direct CRUD call replaced by Service Layer for transactional safety
    if await service.check_duplicate_request(current_user.id, request_data.title):
=======
<<<<<<< HEAD
    if request_crud.check_duplicate_request(db, current_user.id, request_data.title):
=======
    # Refactored: direct CRUD call replaced by Service Layer for transactional safety
    if await service.check_duplicate_request(current_user.id, request_data.title):
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
        raise HTTPException(
            status_code=400,
            detail="Похожее обращение уже было отправлено недавно"
        )

    try:
<<<<<<< HEAD
        # Refactored: direct CRUD call replaced by Service Layer for transactional safety
        return await service.create_request(request_data, current_user.id)
=======
<<<<<<< HEAD
        return request_crud.create_request(db, request_data, current_user.id)
=======
        # Refactored: direct CRUD call replaced by Service Layer for transactional safety
        return await service.create_request(request_data, current_user.id)
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
    except Exception as e:
        raise HTTPException(400, f"Ошибка при создании обращения: {str(e)}")


@router.get("/", response_model=RequestListResponse)
<<<<<<< HEAD
=======
<<<<<<< HEAD
def get_requests_list(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
=======
>>>>>>> front/dev
async def get_requests_list(
    skip: int = Query(0, ge=0),
    # Magic number extracted to config for environment flexibility
    limit: int = Query(settings.DEFAULT_LIMIT, ge=1, le=settings.MAX_LIMIT),
<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
    district_id: Optional[int] = None,
    category_id: Optional[int] = None,
    status_id: Optional[int] = None,
    my_requests: bool = False,
    include_closed: bool = True,
<<<<<<< HEAD
    service: RequestService = Depends(get_request_service),
=======
<<<<<<< HEAD
    db: Session = Depends(get_db),
=======
    service: RequestService = Depends(get_request_service),
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список обращений с фильтрацией и пагинацией

    Права доступа:
    - Гражданин: только свои
    - Депутат: только своего района
    - Админ: все
    """

<<<<<<< HEAD
=======
<<<<<<< HEAD


=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
    # ФИЛЬТРАЦИЯ ПО РОЛИ
    if current_user.role == Role.CITIZEN:
        my_requests = True  # гражданин видит только свои

    user_id = current_user.id if my_requests else None

    if current_user.role == Role.DEPUTY and not my_requests:
<<<<<<< HEAD
=======
<<<<<<< HEAD
        deputy = db.query(Deputy).filter(Deputy.user_id == current_user.id).first()
        if deputy:
            district_id = deputy.district_id  # депутат видит только свой район

    return request_crud.get_requests(
        db=db,
=======
>>>>>>> front/dev
        # Используем DeputyService для получения данных депутата
        from app.services import DeputyService
        deputy_service = DeputyService(service.session)
        deputy = await deputy_service.get_deputy_by_user_id(current_user.id)
        if deputy:
            district_id = deputy.district_id  # депутат видит только свой район

    # Refactored: direct CRUD call replaced by Service Layer for transactional safety
    return await service.get_requests(
<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
        skip=skip,
        limit=limit,
        user_id=user_id,
        district_id=district_id,
        category_id=category_id,
        status_id=status_id,
        include_closed=include_closed
    )


@router.get("/my", response_model=List[RequestResponse])
<<<<<<< HEAD
=======
<<<<<<< HEAD
def get_my_requests(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    include_closed: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Получить список обращений текущего пользователя"""
    result = request_crud.get_requests(
        db=db,
=======
>>>>>>> front/dev
async def get_my_requests(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    include_closed: bool = Query(True),
    service: RequestService = Depends(get_request_service),
    current_user: User = Depends(get_current_active_user)
):
    """Получить список обращений текущего пользователя"""
    # Refactored: direct CRUD call replaced by Service Layer for transactional safety
    result = await service.get_requests(
<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
        skip=skip,
        limit=limit,
        user_id=current_user.id,
        include_closed=include_closed
    )
    return result["items"]


@router.get("/{request_id}", response_model=RequestResponse)
<<<<<<< HEAD
async def get_request_details(
    request_id: int = Path(..., ge=1),
    service: RequestService = Depends(get_request_service),
=======
<<<<<<< HEAD
def get_request_details(
    request_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
=======
async def get_request_details(
    request_id: int = Path(..., ge=1),
    service: RequestService = Depends(get_request_service),
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить детальную информацию об обращении по ID

    Права доступа:
    - Гражданин: только свои
    - Депутат: только своего района
    - Админ: все
    """

<<<<<<< HEAD
=======
<<<<<<< HEAD

    request = get_request_or_404(db, request_id)

    # ИСПОЛЬЗУЕМ ГОТОВУЮ ПРОВЕРКУ ИЗ permissions.py
    if not can_view_request(current_user, request.user_id, request.district_id, db):
=======
>>>>>>> front/dev
    request = await get_request_or_404(service, request_id)

    # ИСПОЛЬЗУЕМ ГОТОВУЮ ПРОВЕРКУ ИЗ permissions.py
    if not can_view_request(current_user, request.user_id, request.district_id, service.session):
<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
        raise HTTPException(403, "У вас нет прав для просмотра этого обращения")

    return request


@router.patch("/{request_id}", response_model=RequestResponse)
<<<<<<< HEAD
=======
<<<<<<< HEAD
def update_request(
    request_id: int,
    request_update: RequestUpdate,
    db: Session = Depends(get_db),
=======
>>>>>>> front/dev
async def update_request(
    request_id: int,
    request_update: RequestUpdate,
    service: RequestService = Depends(get_request_service),
<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить обращение

    Права доступа:
    - Гражданин: только свои + только "новые" + нельзя менять статус
    - Депутат: только своего района
    - Админ: все
    """

<<<<<<< HEAD
    request = await get_request_or_404(service, request_id)
=======
<<<<<<< HEAD
    request = get_request_or_404(db, request_id)
=======
    request = await get_request_or_404(service, request_id)
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev

    # ПРОВЕРКА ПРАВ
    if current_user.role == Role.CITIZEN:
        if request.user_id != current_user.id:
            raise HTTPException(403, "Вы можете редактировать только свои обращения")
        if request.status.code != "new":
            raise HTTPException(400, "Можно редактировать только новые обращения")
        if request_update.status_id is not None:
            raise HTTPException(403, "Вы не можете менять статус обращения")

    elif current_user.role == Role.DEPUTY:
<<<<<<< HEAD
=======
<<<<<<< HEAD
        deputy = db.query(Deputy).filter(Deputy.user_id == current_user.id).first()
=======
>>>>>>> front/dev
        # Используем DeputyService для получения данных депутата
        from app.services import DeputyService
        deputy_service = DeputyService(service.session)
        deputy = await deputy_service.get_deputy_by_user_id(current_user.id)
<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
        if not deputy or request.district_id != deputy.district_id:
            raise HTTPException(403, "Вы можете редактировать только обращения своего района")

    # Админ - без ограничений

    try:
<<<<<<< HEAD
        # Refactored: direct CRUD call replaced by Service Layer for transactional safety
        return await service.update_request(
            request_id, request_update, current_user.id
=======
<<<<<<< HEAD
        return request_crud.update_request(
            db, request_id, request_update, current_user.id
=======
        # Refactored: direct CRUD call replaced by Service Layer for transactional safety
        return await service.update_request(
            request_id, request_update, current_user.id
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{request_id}/assign/{deputy_id}", response_model=RequestResponse)
<<<<<<< HEAD
=======
<<<<<<< HEAD
def assign_deputy_to_request(
    request_id: int,
    deputy_id: int,
    db: Session = Depends(get_db),
=======
>>>>>>> front/dev
async def assign_deputy_to_request(
    request_id: int,
    deputy_id: int,
    service: RequestService = Depends(get_request_service),
<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
    current_user: User = Depends(require_admin)  # ТОЛЬКО АДМИН
):
    """
    Назначить депутата на обращение

    Доступно только для администраторов.
    """

<<<<<<< HEAD
=======
<<<<<<< HEAD
    request = get_request_or_404(db, request_id)

    try:
        return request_crud.assign_deputy(db, request_id, deputy_id, current_user.id)
=======
>>>>>>> front/dev
    request = await get_request_or_404(service, request_id)

    try:
        # Refactored: direct CRUD call replaced by Service Layer for transactional safety
        return await service.assign_deputy(request_id, deputy_id, current_user.id)
<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/{request_id}", status_code=204)
<<<<<<< HEAD
async def delete_request(
    request_id: int,
    service: RequestService = Depends(get_request_service),
=======
<<<<<<< HEAD
def delete_request(
    request_id: int,
    db: Session = Depends(get_db),
=======
async def delete_request(
    request_id: int,
    service: RequestService = Depends(get_request_service),
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
    current_user: User = Depends(require_admin)  # ТОЛЬКО АДМИН
):
    """
    Удалить обращение

    Доступно только для администраторов.
    """
<<<<<<< HEAD
    # Refactored: direct CRUD call replaced by Service Layer for transactional safety
    if not await service.delete_request(request_id):
=======
<<<<<<< HEAD
    if not request_crud.delete_request(db, request_id):
=======
    # Refactored: direct CRUD call replaced by Service Layer for transactional safety
    if not await service.delete_request(request_id):
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
        raise HTTPException(404, f"Обращение с ID {request_id} не найдено")


# ---------------------------
# Сообщения к обращениям
# ---------------------------
@router.get("/{request_id}/messages", response_model=List[MessageResponse])
<<<<<<< HEAD
=======
<<<<<<< HEAD
def get_request_messages(
    request_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
=======
>>>>>>> front/dev
async def get_request_messages(
    request_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    service: RequestService = Depends(get_request_service),
<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
    current_user: User = Depends(get_current_active_user)
):
    """Получить сообщения по обращению"""

<<<<<<< HEAD
=======
<<<<<<< HEAD
    request = get_request_or_404(db, request_id)

    # ГОТОВАЯ ПРОВЕРКА
    if not can_view_request(current_user, request.user_id, request.district_id, db):
        raise HTTPException(403, "У вас нет прав для просмотра сообщений")

    result = request_crud.get_request_messages(db, request_id, skip, limit)
=======
>>>>>>> front/dev
    request = await get_request_or_404(service, request_id)

    # ГОТОВАЯ ПРОВЕРКА
    if not can_view_request(current_user, request.user_id, request.district_id, service.session):
        raise HTTPException(403, "У вас нет прав для просмотра сообщений")

    # Refactored: direct CRUD call replaced by Service Layer for transactional safety
    result = await service.get_request_messages(request_id, skip, limit)
<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
    return result["items"]


@router.post("/{request_id}/messages", response_model=MessageResponse, status_code=201)
<<<<<<< HEAD
=======
<<<<<<< HEAD
def add_message_to_request(
    request_id: int,
    message_data: MessageCreate,
    db: Session = Depends(get_db),
=======
>>>>>>> front/dev
async def add_message_to_request(
    request_id: int,
    message_data: MessageCreate,
    service: RequestService = Depends(get_request_service),
<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
    current_user: User = Depends(get_current_active_user)
):
    """Добавить сообщение к обращению"""

<<<<<<< HEAD
=======
<<<<<<< HEAD
    request = get_request_or_404(db, request_id)

    # ГОТОВАЯ ПРОВЕРКА
    if not can_view_request(current_user, request.user_id, request.district_id, db):
        raise HTTPException(403, "Вы не можете комментировать это обращение")

    return request_crud.add_message_to_request(
        db, request_id, current_user.id, message_data.text
=======
>>>>>>> front/dev
    request = await get_request_or_404(service, request_id)

    # ГОТОВАЯ ПРОВЕРКА
    if not can_view_request(current_user, request.user_id, request.district_id, service.session):
        raise HTTPException(403, "Вы не можете комментировать это обращение")

    # Refactored: direct CRUD call replaced by Service Layer for transactional safety
    return await service.add_message_to_request(
        request_id, current_user.id, message_data.text
<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
    )


# ---------------------------
# История статусов
# ---------------------------
@router.get("/{request_id}/status-history", response_model=List[StatusHistoryResponse])
<<<<<<< HEAD
async def get_request_status_history(
    request_id: int,
    service: RequestService = Depends(get_request_service),
=======
<<<<<<< HEAD
def get_request_status_history(
    request_id: int,
    db: Session = Depends(get_db),
=======
async def get_request_status_history(
    request_id: int,
    service: RequestService = Depends(get_request_service),
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
    current_user: User = Depends(get_current_active_user)
):
    """Получить историю изменения статусов обращения"""
    
<<<<<<< HEAD
=======
<<<<<<< HEAD
    request = get_request_or_404(db, request_id)

    # ГОТОВАЯ ПРОВЕРКА
    if not can_view_request(current_user, request.user_id, request.district_id, db):
        raise HTTPException(403, "У вас нет прав для просмотра истории")

    return request_crud.get_request_status_history(db, request_id)
=======
>>>>>>> front/dev
    request = await get_request_or_404(service, request_id)

    # ГОТОВАЯ ПРОВЕРКА
    if not can_view_request(current_user, request.user_id, request.district_id, service.session):
        raise HTTPException(403, "У вас нет прав для просмотра истории")

    # Refactored: direct CRUD call replaced by Service Layer for transactional safety
    return await service.get_request_status_history(request_id)
<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev


# ---------------------------
# Статистика
# ---------------------------
@router.get("/statistics/summary", response_model=StatisticsResponse)
<<<<<<< HEAD
async def get_requests_statistics(
    district_id: Optional[int] = Query(None),
    service: RequestService = Depends(get_request_service),
=======
<<<<<<< HEAD
def get_requests_statistics(
    district_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
=======
async def get_requests_statistics(
    district_id: Optional[int] = Query(None),
    service: RequestService = Depends(get_request_service),
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
    current_user: User = Depends(require_admin_or_deputy)  # АДМИН ИЛИ ДЕПУТАТ
):
    """
    Получить статистику по обращениям

    Доступно для администраторов и депутатов.
    Депутаты видят статистику только по своему району.
    """
    if current_user.role == Role.DEPUTY:
<<<<<<< HEAD
=======
<<<<<<< HEAD
        deputy = db.query(Deputy).filter(Deputy.user_id == current_user.id).first()
=======
>>>>>>> front/dev
        # Используем DeputyService для получения данных депутата
        from app.services import DeputyService
        deputy_service = DeputyService(service.session)
        deputy = await deputy_service.get_deputy_by_user_id(current_user.id)
<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
        if not deputy:
            raise HTTPException(403, "Депутат не привязан ни к одному району")
        district_id = deputy.district_id

<<<<<<< HEAD
    # Refactored: direct CRUD call replaced by Service Layer for transactional safety
    return await service.get_statistics(district_id)
=======
<<<<<<< HEAD
    return request_crud.get_statistics(db, district_id)
=======
    # Refactored: direct CRUD call replaced by Service Layer for transactional safety
    return await service.get_statistics(district_id)
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
