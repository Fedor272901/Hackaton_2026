# app/api/v1/endpoints/requests.py

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import Optional, List

from app.db.database import get_db
from app.db.models import User, Request, Deputy
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
from app.crud import request as request_crud
from app.core.dependencies import get_current_active_user
# ИСПОЛЬЗУЕМ ГОТОВЫЕ ПРОВЕРКИ ИЗ permissions.py
from app.core.permissions import require_admin, require_admin_or_deputy, check_resource_access

#ЗАЩИТА ОТ СПАМА
from app.core.rate_limit import rate_limiter
from app.core.spam_filter import spam_filter

router = APIRouter()


# ---------------------------
# Справочные эндпоинты (всем авторизованным)
# ---------------------------
@router.get("/statuses", response_model=List[RequestStatusResponse])
def get_statuses(db: Session = Depends(get_db)):
    """Получить список всех возможных статусов обращений"""
    return request_crud.get_request_statuses(db)


@router.get("/categories", response_model=List[RequestCategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    """Получить список всех категорий обращений"""
    return request_crud.get_request_categories(db)


# ---------------------------
# Основные эндпоинты обращений
# ---------------------------
@router.post("/", response_model=RequestResponse, status_code=201)
def create_request(
    request_data: RequestCreate,
    db: Session = Depends(get_db),
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
    if request_crud.check_duplicate_request(db, current_user.id, request_data.title):
        raise HTTPException(
            status_code=400,
            detail="Похожее обращение уже было отправлено недавно"
        )

    try:
        return request_crud.create_request(db, request_data, current_user.id)
    except Exception as e:
        raise HTTPException(400, f"Ошибка при создании обращения: {str(e)}")


@router.get("/", response_model=RequestListResponse)
def get_requests_list(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    district_id: Optional[int] = None,
    category_id: Optional[int] = None,
    status_id: Optional[int] = None,
    my_requests: bool = False,
    include_closed: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список обращений с фильтрацией и пагинацией
    
    Права доступа:
    - Гражданин: только свои
    - Депутат: только своего района
    - Админ: все
    """
    # ФИЛЬТРАЦИЯ ПО РОЛИ
    if current_user.role == "citizen":
        my_requests = True  # гражданин видит только свои
    
    user_id = current_user.id if my_requests else None
    
    if current_user.role == "deputy" and not my_requests:
        deputy = db.query(Deputy).filter(Deputy.user_id == current_user.id).first()
        if deputy:
            district_id = deputy.district_id  # депутат видит только свой район
    
    return request_crud.get_requests(
        db=db,
        skip=skip,
        limit=limit,
        user_id=user_id,
        district_id=district_id,
        category_id=category_id,
        status_id=status_id,
        include_closed=include_closed
    )


@router.get("/my", response_model=List[RequestResponse])
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
        skip=skip,
        limit=limit,
        user_id=current_user.id,
        include_closed=include_closed
    )
    return result["items"]


@router.get("/{request_id}", response_model=RequestResponse)
def get_request_details(
    request_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить детальную информацию об обращении по ID
    
    Права доступа:
    - Гражданин: только свои
    - Депутат: только своего района
    - Админ: все
    """
    request = request_crud.get_request_by_id(db, request_id)
    
    if not request:
        raise HTTPException(404, f"Обращение с ID {request_id} не найдено")
    
    # ИСПОЛЬЗУЕМ ГОТОВУЮ ПРОВЕРКУ ИЗ permissions.py
    if not check_resource_access(current_user, request.user_id, request.district_id, db):
        raise HTTPException(403, "У вас нет прав для просмотра этого обращения")
    
    return request


@router.patch("/{request_id}", response_model=RequestResponse)
def update_request(
    request_id: int,
    request_update: RequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить обращение
    
    Права доступа:
    - Гражданин: только свои + только "новые" + нельзя менять статус
    - Депутат: только своего района
    - Админ: все
    """
    request = request_crud.get_request_by_id(db, request_id)
    
    if not request:
        raise HTTPException(404, f"Обращение с ID {request_id} не найдено")
    
    # ПРОВЕРКА ПРАВ
    if current_user.role == "citizen":
        if request.user_id != current_user.id:
            raise HTTPException(403, "Вы можете редактировать только свои обращения")
        if request.status.code != "new":
            raise HTTPException(400, "Можно редактировать только новые обращения")
        if request_update.status_id is not None:
            raise HTTPException(403, "Вы не можете менять статус обращения")
    
    elif current_user.role == "deputy":
        deputy = db.query(Deputy).filter(Deputy.user_id == current_user.id).first()
        if not deputy or request.district_id != deputy.district_id:
            raise HTTPException(403, "Вы можете редактировать только обращения своего района")
    
    # Админ - без ограничений
    
    try:
        return request_crud.update_request(
            db, request_id, request_update, current_user.id
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{request_id}/assign/{deputy_id}", response_model=RequestResponse)
def assign_deputy_to_request(
    request_id: int,
    deputy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)  # ТОЛЬКО АДМИН
):
    """
    Назначить депутата на обращение
    
    Доступно только для администраторов.
    """
    request = request_crud.get_request_by_id(db, request_id)
    
    if not request:
        raise HTTPException(404, f"Обращение с ID {request_id} не найдено")
    
    try:
        return request_crud.assign_deputy(db, request_id, deputy_id, current_user.id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/{request_id}", status_code=204)
def delete_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)  # ТОЛЬКО АДМИН
):
    """
    Удалить обращение
    
    Доступно только для администраторов.
    """
    if not request_crud.delete_request(db, request_id):
        raise HTTPException(404, f"Обращение с ID {request_id} не найдено")


# ---------------------------
# Сообщения к обращениям
# ---------------------------
@router.get("/{request_id}/messages", response_model=List[MessageResponse])
def get_request_messages(
    request_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Получить сообщения по обращению"""
    request = request_crud.get_request_by_id(db, request_id)
    
    if not request:
        raise HTTPException(404, f"Обращение с ID {request_id} не найдено")
    
    # ГОТОВАЯ ПРОВЕРКА
    if not check_resource_access(current_user, request.user_id, request.district_id, db):
        raise HTTPException(403, "У вас нет прав для просмотра сообщений")
    
    result = request_crud.get_request_messages(db, request_id, skip, limit)
    return result["items"]


@router.post("/{request_id}/messages", response_model=MessageResponse, status_code=201)
def add_message_to_request(
    request_id: int,
    message_data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Добавить сообщение к обращению"""
    request = request_crud.get_request_by_id(db, request_id)
    
    if not request:
        raise HTTPException(404, f"Обращение с ID {request_id} не найдено")
    
    # ГОТОВАЯ ПРОВЕРКА
    if not check_resource_access(current_user, request.user_id, request.district_id, db):
        raise HTTPException(403, "Вы не можете комментировать это обращение")
    
    return request_crud.add_message_to_request(
        db, request_id, current_user.id, message_data.text
    )


# ---------------------------
# История статусов
# ---------------------------
@router.get("/{request_id}/status-history", response_model=List[StatusHistoryResponse])
def get_request_status_history(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Получить историю изменения статусов обращения"""
    request = request_crud.get_request_by_id(db, request_id)
    
    if not request:
        raise HTTPException(404, f"Обращение с ID {request_id} не найдено")
    
    # ГОТОВАЯ ПРОВЕРКА
    if not check_resource_access(current_user, request.user_id, request.district_id, db):
        raise HTTPException(403, "У вас нет прав для просмотра истории")
    
    return request_crud.get_request_status_history(db, request_id)


# ---------------------------
# Статистика
# ---------------------------
@router.get("/statistics/summary", response_model=StatisticsResponse)
def get_requests_statistics(
    district_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_deputy)  # АДМИН ИЛИ ДЕПУТАТ
):
    """
    Получить статистику по обращениям
    
    Доступно для администраторов и депутатов.
    Депутаты видят статистику только по своему району.
    """
    if current_user.role == "deputy":
        deputy = db.query(Deputy).filter(Deputy.user_id == current_user.id).first()
        if not deputy:
            raise HTTPException(403, "Депутат не привязан ни к одному району")
        district_id = deputy.district_id
    
    return request_crud.get_statistics(db, district_id)