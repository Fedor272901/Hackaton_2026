from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from typing import Optional, List
from datetime import datetime

from app.db.models import (
    Request,
    RequestStatus,
    RequestCategory,
    RequestPhoto,
    StatusHistory,
    Message,
    User,
    District,
    Deputy
)
from app.schemas.requests import RequestCreate, RequestUpdate


def get_request_statuses(db: Session):
    """Получить все возможные статусы обращений"""
    return db.query(RequestStatus).all()


def get_request_categories(db: Session):
    """Получить все категории обращений"""
    return db.query(RequestCategory).all()


def get_request_by_id(db: Session, request_id: int):
    """Получить обращение по ID с загрузкой всех связанных данных"""
    return (
        db.query(Request)
        .options(
            joinedload(Request.user),
            joinedload(Request.district),
            joinedload(Request.category),
            joinedload(Request.status),
            joinedload(Request.assigned_deputy).joinedload(Deputy.user),
            joinedload(Request.photos),
        )
        .filter(Request.id == request_id)
        .first()
    )


def get_requests(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    user_id: Optional[int] = None,
    district_id: Optional[int] = None,
    category_id: Optional[int] = None,
    status_id: Optional[int] = None,
    assigned_deputy_id: Optional[int] = None,
    include_closed: bool = True
):
    """
    Получить список обращений с фильтрацией и пагинацией
    
    Параметры:
    - skip: сколько записей пропустить (для пагинации)
    - limit: максимальное количество записей
    - user_id: фильтр по ID пользователя-автора
    - district_id: фильтр по ID района
    - category_id: фильтр по ID категории
    - status_id: фильтр по ID статуса
    - assigned_deputy_id: фильтр по ID назначенного депутата
    - include_closed: включать ли закрытые обращения
    """
    query = db.query(Request).options(
        joinedload(Request.user),
        joinedload(Request.district),
        joinedload(Request.category),
        joinedload(Request.status),
        joinedload(Request.assigned_deputy).joinedload(Deputy.user),
    )
    
    # Применяем фильтры
    filters = []
    
    if user_id is not None:
        filters.append(Request.user_id == user_id)
    
    if district_id is not None:
        filters.append(Request.district_id == district_id)
    
    if category_id is not None:
        filters.append(Request.category_id == category_id)
    
    if status_id is not None:
        filters.append(Request.status_id == status_id)
    
    if assigned_deputy_id is not None:
        filters.append(Request.assigned_deputy_id == assigned_deputy_id)
    
    if not include_closed:
        # Исключаем закрытые обращения (нужно знать ID статуса "закрыто")
        closed_status = db.query(RequestStatus).filter(RequestStatus.code == "closed").first()
        if closed_status:
            filters.append(Request.status_id != closed_status.id)
    
    if filters:
        query = query.filter(and_(*filters))
    
    # Получаем общее количество (для пагинации на фронтенде)
    total = query.count()
    
    # Применяем пагинацию и сортировку
    requests = query.order_by(Request.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "items": requests,
        "total": total,
        "skip": skip,
        "limit": limit
    }


def create_request(db: Session, request_data: RequestCreate, user_id: int):
    """
    Создать новое обращение
    
    Параметры:
    - request_data: данные обращения из схемы
    - user_id: ID пользователя, создающего обращение
    """
    # Получаем статус "новое" по умолчанию
    default_status = db.query(RequestStatus).filter(RequestStatus.code == "new").first()
    if not default_status:
        # Если статус не найден, создаем его (на всякий случай)
        default_status = RequestStatus(code="new", name="Новое")
        db.add(default_status)
        db.commit()
        db.refresh(default_status)
    
    # Создаем обращение
    request = Request(
        user_id=user_id,
        district_id=request_data.district_id,
        category_id=request_data.category_id,
        status_id=default_status.id,
        title=request_data.title,
        description=request_data.description,
        address=request_data.address,
        latitude=request_data.latitude,
        longitude=request_data.longitude,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(request)
    db.commit()
    db.refresh(request)
    
    # Добавляем фото, если они есть
    if request_data.photo_urls:
        for photo_url in request_data.photo_urls:
            photo = RequestPhoto(
                request_id=request.id,
                file_url=photo_url,
                created_at=datetime.utcnow()
            )
            db.add(photo)
        
        db.commit()
        db.refresh(request)
    
    # Записываем в историю статусов
    status_history = StatusHistory(
        request_id=request.id,
        new_status_id=default_status.id,
        changed_by_user_id=user_id,
        created_at=datetime.utcnow()
    )
    db.add(status_history)
    
    # Создаем системное сообщение о создании обращения
    system_message = Message(
        request_id=request.id,
        user_id=user_id,
        text=f"Обращение создано",
        is_system=True,
        created_at=datetime.utcnow()
    )
    db.add(system_message)
    
    db.commit()
    
    # Загружаем связанные данные для ответа
    return get_request_by_id(db, request.id)


def update_request(
    db: Session,
    request_id: int,
    request_update: RequestUpdate,
    changed_by_user_id: int
):
    """
    Обновить обращение (статус, назначенного депутата и т.д.)
    
    Параметры:
    - request_id: ID обращения
    - request_update: данные для обновления
    - changed_by_user_id: ID пользователя, который вносит изменения
    """
    request = db.query(Request).filter(Request.id == request_id).first()
    if not request:
        return None
    
    old_status_id = request.status_id
    
    # Обновляем поля, если они предоставлены
    update_data = request_update.dict(exclude_unset=True)
    
    # Особая обработка для смены статуса
    if "status_id" in update_data and update_data["status_id"] != old_status_id:
        # Проверяем, что статус существует
        new_status = db.query(RequestStatus).filter(RequestStatus.id == update_data["status_id"]).first()
        if not new_status:
            raise ValueError(f"Статус с ID {update_data['status_id']} не найден")
        
        # Если статус меняется на "закрыто", устанавливаем closed_at
        if new_status.code == "closed":
            request.closed_at = datetime.utcnow()
        
        # Записываем в историю статусов
        status_history = StatusHistory(
            request_id=request_id,
            old_status_id=old_status_id,
            new_status_id=update_data["status_id"],
            changed_by_user_id=changed_by_user_id,
            created_at=datetime.utcnow()
        )
        db.add(status_history)
        
        # Создаем системное сообщение о смене статуса
        old_status = db.query(RequestStatus).filter(RequestStatus.id == old_status_id).first()
        system_message = Message(
            request_id=request_id,
            user_id=changed_by_user_id,
            text=f"Статус изменен с '{old_status.name}' на '{new_status.name}'",
            is_system=True,
            created_at=datetime.utcnow()
        )
        db.add(system_message)
    
    # Обновляем остальные поля
    for field, value in update_data.items():
        if hasattr(request, field):
            setattr(request, field, value)
    
    request.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(request)
    
    return get_request_by_id(db, request_id)


def assign_deputy(db: Session, request_id: int, deputy_id: int, assigned_by_user_id: int):
    """
    Назначить депутата на обращение
    
    Параметры:
    - request_id: ID обращения
    - deputy_id: ID депутата
    - assigned_by_user_id: ID пользователя, который назначает (админ)
    """
    request = db.query(Request).filter(Request.id == request_id).first()
    if not request:
        return None
    
    # Проверяем, что депутат существует и привязан к тому же району
    deputy = db.query(Deputy).filter(Deputy.id == deputy_id).first()
    if not deputy:
        raise ValueError(f"Депутат с ID {deputy_id} не найден")
    
    if deputy.district_id != request.district_id:
        raise ValueError(f"Депутат не привязан к району этого обращения")
    
    old_deputy_id = request.assigned_deputy_id
    request.assigned_deputy_id = deputy_id
    request.updated_at = datetime.utcnow()
    
    # Создаем системное сообщение о назначении
    deputy_user = db.query(User).filter(User.id == deputy.user_id).first()
    message_text = f"Обращение назначено депутату {deputy_user.first_name} {deputy_user.last_name}"
    
    system_message = Message(
        request_id=request_id,
        user_id=assigned_by_user_id,
        text=message_text,
        is_system=True,
        created_at=datetime.utcnow()
    )
    db.add(system_message)
    
    db.commit()
    db.refresh(request)
    
    return get_request_by_id(db, request_id)


def add_message_to_request(
    db: Session,
    request_id: int,
    user_id: int,
    text: str,
    is_system: bool = False
):
    """
    Добавить сообщение к обращению
    
    Параметры:
    - request_id: ID обращения
    - user_id: ID пользователя, отправляющего сообщение
    - text: текст сообщения
    - is_system: является ли сообщение системным
    """
    request = db.query(Request).filter(Request.id == request_id).first()
    if not request:
        return None
    
    message = Message(
        request_id=request_id,
        user_id=user_id,
        text=text,
        is_system=is_system,
        created_at=datetime.utcnow()
    )
    
    db.add(message)
    db.commit()
    db.refresh(message)
    
    # Обновляем updated_at у обращения
    request.updated_at = datetime.utcnow()
    db.commit()
    
    return message


def get_request_messages(db: Session, request_id: int, skip: int = 0, limit: int = 50):
    """
    Получить сообщения по обращению
    
    Параметры:
    - request_id: ID обращения
    - skip: сколько сообщений пропустить
    - limit: максимальное количество сообщений
    """
    messages = (
        db.query(Message)
        .options(joinedload(Message.user))
        .filter(Message.request_id == request_id)
        .order_by(Message.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    total = db.query(Message).filter(Message.request_id == request_id).count()
    
    return {
        "items": messages,
        "total": total,
        "skip": skip,
        "limit": limit
    }


def get_request_status_history(db: Session, request_id: int):
    """
    Получить историю изменения статусов обращения
    
    Параметры:
    - request_id: ID обращения
    """
    history = (
        db.query(StatusHistory)
        .options(
            joinedload(StatusHistory.old_status),
            joinedload(StatusHistory.new_status),
            joinedload(StatusHistory.changed_by_user)
        )
        .filter(StatusHistory.request_id == request_id)
        .order_by(StatusHistory.created_at.desc())
        .all()
    )
    
    return history


def delete_request(db: Session, request_id: int) -> bool:
    """
    Удалить обращение (только для админов)
    
    Параметры:
    - request_id: ID обращения
    """
    request = db.query(Request).filter(Request.id == request_id).first()
    if not request:
        return False
    
    # Сначала удаляем связанные данные
    db.query(Message).filter(Message.request_id == request_id).delete()
    db.query(RequestPhoto).filter(RequestPhoto.request_id == request_id).delete()
    db.query(StatusHistory).filter(StatusHistory.request_id == request_id).delete()
    
    # Затем удаляем само обращение
    db.delete(request)
    db.commit()
    
    return True


def get_statistics(db: Session, district_id: Optional[int] = None):
    """
    Получить статистику по обращениям
    
    Параметры:
    - district_id: опциональный фильтр по району
    """
    query = db.query(Request)
    
    if district_id:
        query = query.filter(Request.district_id == district_id)
    
    total = query.count()
    
    # Статистика по статусам
    statuses = db.query(RequestStatus).all()
    status_stats = {}
    
    for status in statuses:
        count = query.filter(Request.status_id == status.id).count()
        status_stats[status.code] = {
            "name": status.name,
            "count": count,
            "percentage": round(count / total * 100, 2) if total > 0 else 0
        }
    
    # Статистика по категориям
    categories = db.query(RequestCategory).all()
    category_stats = {}
    
    for category in categories:
        count = query.filter(Request.category_id == category.id).count()
        category_stats[category.name] = {
            "count": count,
            "percentage": round(count / total * 100, 2) if total > 0 else 0
        }
    
    # Среднее время решения
    closed_status = db.query(RequestStatus).filter(RequestStatus.code == "closed").first()
    if closed_status:
        closed_requests = query.filter(Request.status_id == closed_status.id).all()
        resolution_times = []
        for req in closed_requests:
            if req.closed_at and req.created_at:
                delta = req.closed_at - req.created_at
                resolution_times.append(delta.days)
        
        avg_resolution_days = sum(resolution_times) / len(resolution_times) if resolution_times else 0
    else:
        avg_resolution_days = 0
    
    return {
        "total_requests": total,
        "by_status": status_stats,
        "by_category": category_stats,
        "average_resolution_days": round(avg_resolution_days, 1),
        "district_id": district_id
    }