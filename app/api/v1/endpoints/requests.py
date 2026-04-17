from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

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
from app.core.dependencies import get_current_user, get_current_active_user
from app.core.permissions import require_role
from app.core.rate_limit import RateLimiter
from app.core.spam_filter import SpamFilter

router = APIRouter()




# ---------------------------
# Справочные эндпоинты
# ---------------------------
@router.get("/statuses", response_model=List[RequestStatusResponse])
def get_statuses(db: Session = Depends(get_db)):
    """
    Получить список всех возможных статусов обращений
    """
    statuses = request_crud.get_request_statuses(db)
    return statuses


@router.get("/categories", response_model=List[RequestCategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    """
    Получить список всех категорий обращений
    """
    categories = request_crud.get_request_categories(db)
    return categories


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
    
    - **title**: заголовок обращения
    - **description**: подробное описание проблемы
    - **district_id**: ID района, к которому относится обращение
    - **category_id**: ID категории обращения
    - **address**: физический адрес (опционально)
    - **latitude**: широта для карты (опционально)
    - **longitude**: долгота для карты (опционально)
    - **photo_urls**: список URL загруженных фотографий (опционально)
    """

     # ЗАЩИТА 1: Rate Limit (5 обращений в час)
    if not RateLimiter.check(current_user.id):
        raise HTTPException(
            status_code=429, 
            detail="Лимит исчерпан: максимум 5 обращений в сутки"
        )
    
    # ЗАЩИТА 2: Спам-фильтр
    full_text = f"{request_data.title} {request_data.description}"
    is_spam, reason = SpamFilter.check(full_text)
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
        new_request = request_crud.create_request(
            db=db,
            request_data=request_data,
            user_id=current_user.id
        )
        return new_request
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Ошибка при создании обращения: {str(e)}"
        )


@router.get("/", response_model=RequestListResponse)
def get_requests_list(
    skip: int = Query(0, ge=0, description="Сколько записей пропустить"),
    limit: int = Query(20, ge=1, le=100, description="Максимальное количество записей"),
    district_id: Optional[int] = Query(None, description="Фильтр по ID района"),
    category_id: Optional[int] = Query(None, description="Фильтр по ID категории"),
    status_id: Optional[int] = Query(None, description="Фильтр по ID статуса"),
    my_requests: bool = Query(False, description="Показать только мои обращения"),
    include_closed: bool = Query(True, description="Включать закрытые обращения"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список обращений с фильтрацией и пагинацией
    
    Доступно для всех авторизованных пользователей.
    
    Фильтры:
    - **district_id**: показать обращения только из указанного района
    - **category_id**: показать обращения только указанной категории
    - **status_id**: показать обращения только с указанным статусом
    - **my_requests**: если true, показывает только обращения текущего пользователя
    - **include_closed**: если false, исключает закрытые обращения
    """
    user_id = current_user.id if my_requests else None
    
    # Если пользователь - депутат, он может видеть обращения своего района
    if current_user.role == "deputy" and not my_requests:
        deputy = db.query(Deputy).filter(Deputy.user_id == current_user.id).first()
        if deputy and not district_id:
            district_id = deputy.district_id
    
    result = request_crud.get_requests(
        db=db,
        skip=skip,
        limit=limit,
        user_id=user_id,
        district_id=district_id,
        category_id=category_id,
        status_id=status_id,
        include_closed=include_closed
    )
    
    return result


@router.get("/my", response_model=List[RequestResponse])
def get_my_requests(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    include_closed: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить список обращений текущего пользователя
    
    Упрощенный эндпоинт для получения своих обращений.
    """
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
    request_id: int = Path(..., ge=1, description="ID обращения"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить детальную информацию об обращении по ID
    
    Доступно для всех авторизованных пользователей.
    
    Включает:
    - Основную информацию об обращении
    - Данные автора
    - Данные района и категории
    - Текущий статус
    - Назначенного депутата (если есть)
    - Прикрепленные фотографии
    """
    request = request_crud.get_request_by_id(db, request_id)
    
    if not request:
        raise HTTPException(
            status_code=404,
            detail=f"Обращение с ID {request_id} не найдено"
        )
    
    # Проверка прав доступа
    # Гражданин может видеть только свои обращения
    if current_user.role == "citizen" and request.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="У вас нет прав для просмотра этого обращения"
        )
    
    # Депутат может видеть только обращения своего района
    if current_user.role == "deputy":
        deputy = db.query(Deputy).filter(Deputy.user_id == current_user.id).first()
        if deputy and request.district_id != deputy.district_id:
            raise HTTPException(
                status_code=403,
                detail="Вы можете просматривать только обращения своего района"
            )
    
    return request


@router.patch("/{request_id}", response_model=RequestResponse)
def update_request(
    request_id: int,
    request_update: RequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновить обращение (статус, назначенного депутата и т.д.)
    
    Доступно для:
    - Администраторов: полный доступ
    - Депутатов: могут менять статус обращений в своем районе
    - Граждан: могут обновлять описание только своих обращений в статусе "новое"
    
    Поля для обновления:
    - **status_id**: новый статус обращения
    - **title**: новый заголовок
    - **description**: новое описание
    - **category_id**: новая категория
    - **address**: новый адрес
    """
    request = request_crud.get_request_by_id(db, request_id)
    
    if not request:
        raise HTTPException(
            status_code=404,
            detail=f"Обращение с ID {request_id} не найдено"
        )
    
    # Проверка прав на обновление
    if current_user.role == "citizen":
        # Граждане могут обновлять только свои обращения
        if request.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Вы можете редактировать только свои обращения"
            )
        
        # И только если обращение в статусе "новое"
        if request.status.code != "new":
            raise HTTPException(
                status_code=400,
                detail="Можно редактировать только новые обращения"
            )
        
        # Граждане не могут менять статус
        if request_update.status_id is not None:
            raise HTTPException(
                status_code=403,
                detail="У вас нет прав для изменения статуса обращения"
            )
    
    elif current_user.role == "deputy":
        # Депутаты могут обновлять только обращения своего района
        deputy = db.query(Deputy).filter(Deputy.user_id == current_user.id).first()
        if not deputy or request.district_id != deputy.district_id:
            raise HTTPException(
                status_code=403,
                detail="Вы можете редактировать только обращения своего района"
            )
    
    # Администраторы могут всё
    
    try:
        updated_request = request_crud.update_request(
            db=db,
            request_id=request_id,
            request_update=request_update,
            changed_by_user_id=current_user.id
        )
        return updated_request
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обновлении обращения: {str(e)}"
        )


@router.post("/{request_id}/assign/{deputy_id}", response_model=RequestResponse)
def assign_deputy_to_request(
    request_id: int,
    deputy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Назначить депутата на обращение
    
    Доступно только для администраторов.
    
    - **request_id**: ID обращения
    - **deputy_id**: ID депутата (должен быть привязан к тому же району)
    """
    request = request_crud.get_request_by_id(db, request_id)
    
    if not request:
        raise HTTPException(
            status_code=404,
            detail=f"Обращение с ID {request_id} не найдено"
        )
    
    try:
        updated_request = request_crud.assign_deputy(
            db=db,
            request_id=request_id,
            deputy_id=deputy_id,
            assigned_by_user_id=current_user.id
        )
        return updated_request
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{request_id}", status_code=204)
def delete_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Удалить обращение
    
    Доступно только для администраторов.
    ВНИМАНИЕ: Удаление безвозвратно удаляет обращение и все связанные данные!
    """
    success = request_crud.delete_request(db, request_id)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Обращение с ID {request_id} не найдено"
        )
    
    return None


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
    """
    Получить сообщения по обращению
    
    Доступно для всех, у кого есть доступ к обращению.
    """
    request = request_crud.get_request_by_id(db, request_id)
    
    if not request:
        raise HTTPException(
            status_code=404,
            detail=f"Обращение с ID {request_id} не найдено"
        )
    
    # Проверка прав доступа (аналогично просмотру обращения)
    if current_user.role == "citizen" and request.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="У вас нет прав для просмотра сообщений этого обращения"
        )
    
    result = request_crud.get_request_messages(db, request_id, skip, limit)
    return result["items"]


@router.post("/{request_id}/messages", response_model=MessageResponse, status_code=201)
def add_message_to_request(
    request_id: int,
    message_data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Добавить сообщение к обращению
    
    Доступно для всех, у кого есть доступ к обращению.
    """
    request = request_crud.get_request_by_id(db, request_id)
    
    if not request:
        raise HTTPException(
            status_code=404,
            detail=f"Обращение с ID {request_id} не найдено"
        )
    
    # Проверка прав доступа
    if current_user.role == "citizen" and request.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Вы можете комментировать только свои обращения"
        )
    
    elif current_user.role == "deputy":
        deputy = db.query(Deputy).filter(Deputy.user_id == current_user.id).first()
        if not deputy or request.district_id != deputy.district_id:
            raise HTTPException(
                status_code=403,
                detail="Вы можете комментировать только обращения своего района"
            )
    
    message = request_crud.add_message_to_request(
        db=db,
        request_id=request_id,
        user_id=current_user.id,
        text=message_data.text,
        is_system=False
    )
    
    return message


# ---------------------------
# История статусов
# ---------------------------
@router.get("/{request_id}/status-history", response_model=List[StatusHistoryResponse])
def get_request_status_history(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить историю изменения статусов обращения
    
    Доступно для всех, у кого есть доступ к обращению.
    """
    request = request_crud.get_request_by_id(db, request_id)
    
    if not request:
        raise HTTPException(
            status_code=404,
            detail=f"Обращение с ID {request_id} не найдено"
        )
    
    # Проверка прав доступа
    if current_user.role == "citizen" and request.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="У вас нет прав для просмотра истории этого обращения"
        )
    
    history = request_crud.get_request_status_history(db, request_id)
    return history


# ---------------------------
# Статистика
# ---------------------------
@router.get("/statistics/summary", response_model=StatisticsResponse)
def get_requests_statistics(
    district_id: Optional[int] = Query(None, description="Фильтр по ID района"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получить статистику по обращениям
    
    Доступно для администраторов и депутатов.
    Депутаты видят статистику только по своему району.
    """
    # Депутаты видят статистику только своего района
    if current_user.role == "deputy":
        deputy = db.query(Deputy).filter(Deputy.user_id == current_user.id).first()
        if deputy:
            district_id = deputy.district_id
        else:
            raise HTTPException(
                status_code=403,
                detail="Депутат не привязан ни к одному району"
            )
    
    elif current_user.role == "citizen":
        raise HTTPException(
            status_code=403,
            detail="Статистика доступна только администраторам и депутатам"
        )
    
    stats = request_crud.get_statistics(db, district_id)
    return stats