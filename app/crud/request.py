<<<<<<< HEAD
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
=======
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy import and_, or_, func, select
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
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


<<<<<<< HEAD
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
=======
async def get_request_statuses(db: AsyncSession):
    """Получить все возможные статусы обращений"""
    result = await db.execute(select(RequestStatus))
    return list(result.scalars().all())


async def get_request_categories(db: AsyncSession):
    """Получить все категории обращений"""
    result = await db.execute(select(RequestCategory))
    return list(result.scalars().all())


async def get_request_by_id(db: AsyncSession, request_id: int):
    """Получить обращение по ID с загрузкой всех связанных данных"""
    result = await db.execute(
        select(Request)
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
        .options(
            joinedload(Request.user),
            joinedload(Request.district),
            joinedload(Request.category),
            joinedload(Request.status),
            joinedload(Request.assigned_deputy).joinedload(Deputy.user),
            joinedload(Request.photos),
        )
<<<<<<< HEAD
        .filter(Request.id == request_id)
        .first()
    )


def get_requests(
    db: Session,
=======
        .where(Request.id == request_id)
    )
    return result.scalar_one_or_none()


async def get_requests(
    db: AsyncSession,
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
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
<<<<<<< HEAD
    query = db.query(Request).options(
=======
    # Build query with eager loading
    stmt = select(Request).options(
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
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
<<<<<<< HEAD
        closed_status = db.query(RequestStatus).filter(RequestStatus.code == "closed").first()
=======
        result = await db.execute(
            select(RequestStatus).where(RequestStatus.code == "closed")
        )
        closed_status = result.scalar_one_or_none()
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
        if closed_status:
            filters.append(Request.status_id != closed_status.id)
    
    if filters:
<<<<<<< HEAD
        query = query.filter(and_(*filters))
    
    # Получаем общее количество (для пагинации на фронтенде)
    total = query.count()
    
    # Применяем пагинацию и сортировку
    requests = query.order_by(Request.created_at.desc()).offset(skip).limit(limit).all()
=======
        stmt = stmt.where(and_(*filters))
    
    # Get total count for pagination
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()
    
    # Apply pagination and sorting
    stmt = stmt.order_by(Request.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    requests = result.scalars().unique().all()
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    
    return {
        "items": requests,
        "total": total,
        "skip": skip,
        "limit": limit
    }


<<<<<<< HEAD
def create_request(db: Session, request_data: RequestCreate, user_id: int):
=======
async def create_request(db: AsyncSession, request_data: RequestCreate, user_id: int):
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    """
    Создать новое обращение
    
    Параметры:
    - request_data: данные обращения из схемы
    - user_id: ID пользователя, создающего обращение
<<<<<<< HEAD
    """
    # Получаем статус "новое" по умолчанию
    default_status = db.query(RequestStatus).filter(RequestStatus.code == "new").first()
=======
    
    DATA INTEGRITY: Перед созданием записи выполняется проверка существования
    всех связанных сущностей (district, category). Это предотвращает создание
    "висячих" записей с невалидными foreign key.
    """
    # Data integrity: ensuring foreign key references exist before commit
    # Проверяем существование района перед созданием обращения
    result = await db.execute(
        select(District).where(District.id == request_data.district_id)
    )
    district = result.scalar_one_or_none()
    if not district:
        raise ValueError(f"Район с ID {request_data.district_id} не найден")
    
    # Data integrity: ensuring foreign key references exist before commit
    # Проверяем существование категории перед созданием обращения
    result = await db.execute(
        select(RequestCategory).where(RequestCategory.id == request_data.category_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise ValueError(f"Категория с ID {request_data.category_id} не найдена")
    
    # Получаем статус "новое" по умолчанию
    result = await db.execute(
        select(RequestStatus).where(RequestStatus.code == "new")
    )
    default_status = result.scalar_one_or_none()
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    if not default_status:
        # Если статус не найден, создаем его (на всякий случай)
        default_status = RequestStatus(code="new", name="Новое")
        db.add(default_status)
<<<<<<< HEAD
        db.commit()
        db.refresh(default_status)
=======
        await db.commit()
        await db.refresh(default_status)
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    
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
<<<<<<< HEAD
    db.commit()
    db.refresh(request)
=======
    await db.commit()
    await db.refresh(request)
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    
    # Добавляем фото, если они есть
    if request_data.photo_urls:
        for photo_url in request_data.photo_urls:
            photo = RequestPhoto(
                request_id=request.id,
                file_url=photo_url,
                created_at=datetime.utcnow()
            )
            db.add(photo)
        
<<<<<<< HEAD
        db.commit()
        db.refresh(request)
=======
        await db.commit()
        await db.refresh(request)
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    
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
    
<<<<<<< HEAD
    db.commit()
    
    # Загружаем связанные данные для ответа
    return get_request_by_id(db, request.id)


def update_request(
    db: Session,
=======
    await db.commit()
    
    # Загружаем связанные данные для ответа
    return await get_request_by_id(db, request.id)


async def update_request(
    db: AsyncSession,
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
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
<<<<<<< HEAD
    """
    request = db.query(Request).filter(Request.id == request_id).first()
=======
    
    DATA INTEGRITY: При обновлении district_id или category_id выполняется
    проверка существования связанных записей перед коммитом.
    """
    result = await db.execute(
        select(Request).where(Request.id == request_id)
    )
    request = result.scalar_one_or_none()
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    if not request:
        return None
    
    old_status_id = request.status_id
    
    # Обновляем поля, если они предоставлены
    update_data = request_update.dict(exclude_unset=True)
    
<<<<<<< HEAD
    # Особая обработка для смены статуса
    if "status_id" in update_data and update_data["status_id"] != old_status_id:
        # Проверяем, что статус существует
        new_status = db.query(RequestStatus).filter(RequestStatus.id == update_data["status_id"]).first()
=======
    # Data integrity: ensuring foreign key references exist before commit
    # Проверяем существование нового района при смене district_id
    if "district_id" in update_data and update_data["district_id"] != request.district_id:
        result = await db.execute(
            select(District).where(District.id == update_data["district_id"])
        )
        new_district = result.scalar_one_or_none()
        if not new_district:
            raise ValueError(f"Район с ID {update_data['district_id']} не найден")
    
    # Data integrity: ensuring foreign key references exist before commit
    # Проверяем существование новой категории при смене category_id
    if "category_id" in update_data and update_data["category_id"] != request.category_id:
        result = await db.execute(
            select(RequestCategory).where(RequestCategory.id == update_data["category_id"])
        )
        new_category = result.scalar_one_or_none()
        if not new_category:
            raise ValueError(f"Категория с ID {update_data['category_id']} не найдена")
    
    # Особая обработка для смены статуса
    if "status_id" in update_data and update_data["status_id"] != old_status_id:
        # Проверяем, что статус существует
        result = await db.execute(
            select(RequestStatus).where(RequestStatus.id == update_data["status_id"])
        )
        new_status = result.scalar_one_or_none()
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
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
<<<<<<< HEAD
        old_status = db.query(RequestStatus).filter(RequestStatus.id == old_status_id).first()
=======
        result = await db.execute(
            select(RequestStatus).where(RequestStatus.id == old_status_id)
        )
        old_status = result.scalar_one_or_none()
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
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
    
<<<<<<< HEAD
    db.commit()
    db.refresh(request)
    
    return get_request_by_id(db, request_id)


def assign_deputy(db: Session, request_id: int, deputy_id: int, assigned_by_user_id: int):
=======
    await db.commit()
    await db.refresh(request)
    
    return await get_request_by_id(db, request_id)


async def assign_deputy(db: AsyncSession, request_id: int, deputy_id: int, assigned_by_user_id: int):
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    """
    Назначить депутата на обращение
    
    Параметры:
    - request_id: ID обращения
    - deputy_id: ID депутата
    - assigned_by_user_id: ID пользователя, который назначает (админ)
    """
<<<<<<< HEAD
    request = db.query(Request).filter(Request.id == request_id).first()
=======
    result = await db.execute(
        select(Request).where(Request.id == request_id)
    )
    request = result.scalar_one_or_none()
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    if not request:
        return None
    
    # Проверяем, что депутат существует и привязан к тому же району
<<<<<<< HEAD
    deputy = db.query(Deputy).filter(Deputy.id == deputy_id).first()
=======
    result = await db.execute(
        select(Deputy).where(Deputy.id == deputy_id)
    )
    deputy = result.scalar_one_or_none()
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    if not deputy:
        raise ValueError(f"Депутат с ID {deputy_id} не найден")
    
    if deputy.district_id != request.district_id:
        raise ValueError(f"Депутат не привязан к району этого обращения")
    
    old_deputy_id = request.assigned_deputy_id
    request.assigned_deputy_id = deputy_id
    request.updated_at = datetime.utcnow()
    
    # Создаем системное сообщение о назначении
<<<<<<< HEAD
    deputy_user = db.query(User).filter(User.id == deputy.user_id).first()
=======
    result = await db.execute(
        select(User).where(User.id == deputy.user_id)
    )
    deputy_user = result.scalar_one_or_none()
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    message_text = f"Обращение назначено депутату {deputy_user.first_name} {deputy_user.last_name}"
    
    system_message = Message(
        request_id=request_id,
        user_id=assigned_by_user_id,
        text=message_text,
        is_system=True,
        created_at=datetime.utcnow()
    )
    db.add(system_message)
    
<<<<<<< HEAD
    db.commit()
    db.refresh(request)
    
    return get_request_by_id(db, request_id)


def add_message_to_request(
    db: Session,
=======
    await db.commit()
    await db.refresh(request)
    
    return await get_request_by_id(db, request_id)


async def add_message_to_request(
    db: AsyncSession,
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
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
<<<<<<< HEAD
    request = db.query(Request).filter(Request.id == request_id).first()
=======
    result = await db.execute(
        select(Request).where(Request.id == request_id)
    )
    request = result.scalar_one_or_none()
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
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
<<<<<<< HEAD
    db.commit()
    db.refresh(message)
    
    # Обновляем updated_at у обращения
    request.updated_at = datetime.utcnow()
    db.commit()
=======
    await db.commit()
    await db.refresh(message)
    
    # Обновляем updated_at у обращения
    request.updated_at = datetime.utcnow()
    await db.commit()
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    
    return message


<<<<<<< HEAD
def get_request_messages(db: Session, request_id: int, skip: int = 0, limit: int = 50):
=======
async def get_request_messages(db: AsyncSession, request_id: int, skip: int = 0, limit: int = 50):
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
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


<<<<<<< HEAD
def get_request_status_history(db: Session, request_id: int):
=======
async def get_request_status_history(db: AsyncSession, request_id: int):
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    """
    Получить историю изменения статусов обращения
    
    Параметры:
    - request_id: ID обращения
    """
<<<<<<< HEAD
    history = (
        db.query(StatusHistory)
=======
    result = await db.execute(
        select(StatusHistory)
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
        .options(
            joinedload(StatusHistory.old_status),
            joinedload(StatusHistory.new_status),
            joinedload(StatusHistory.changed_by_user)
        )
<<<<<<< HEAD
        .filter(StatusHistory.request_id == request_id)
        .order_by(StatusHistory.created_at.desc())
        .all()
    )
    
    return history


def delete_request(db: Session, request_id: int) -> bool:
=======
        .where(StatusHistory.request_id == request_id)
        .order_by(StatusHistory.created_at.desc())
    )
    
    return list(result.scalars().unique().all())


async def delete_request(db: AsyncSession, request_id: int) -> bool:
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    """
    Удалить обращение (только для админов)
    
    Параметры:
    - request_id: ID обращения
    """
<<<<<<< HEAD
    request = db.query(Request).filter(Request.id == request_id).first()
=======
    result = await db.execute(
        select(Request).where(Request.id == request_id)
    )
    request = result.scalar_one_or_none()
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    if not request:
        return False
    
    # Сначала удаляем связанные данные
<<<<<<< HEAD
    db.query(Message).filter(Message.request_id == request_id).delete()
    db.query(RequestPhoto).filter(RequestPhoto.request_id == request_id).delete()
    db.query(StatusHistory).filter(StatusHistory.request_id == request_id).delete()
    
    # Затем удаляем само обращение
    db.delete(request)
    db.commit()
=======
    await db.execute(
        delete(Message).where(Message.request_id == request_id)
    )
    await db.execute(
        delete(RequestPhoto).where(RequestPhoto.request_id == request_id)
    )
    await db.execute(
        delete(StatusHistory).where(StatusHistory.request_id == request_id)
    )
    
    # Затем удаляем само обращение
    await db.delete(request)
    await db.commit()
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    
    return True


<<<<<<< HEAD
def get_statistics(db: Session, district_id: Optional[int] = None):
=======
async def get_statistics(db: AsyncSession, district_id: Optional[int] = None):
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    """
    Получить статистику по обращениям
    
    Параметры:
    - district_id: опциональный фильтр по району
<<<<<<< HEAD
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
=======
    
    OPTIMIZATION: Этот метод использует ОДИН агрегирующий SQL-запрос с GROUP BY
    вместо N+1 отдельных SELECT COUNT запросов. Ранее для каждого статуса и категории
    выполнялся отдельный запрос (N+1 проблема), что создавало нагрузку на БД.
    Теперь все данные собираются одним запросом, что снижает количество round-trips
    к базе данных с ~20+ до 1-2 запросов.
    """
    filters = []
    if district_id:
        filters.append(Request.district_id == district_id)
    
    # Get total count
    total_query = select(func.count()).select_from(Request)
    if filters:
        total_query = total_query.where(and_(*filters))
    total_result = await db.execute(total_query)
    total = total_result.scalar()
    
    # OPTIMIZATION: Один запрос с GROUP BY вместо цикла с отдельными COUNT для каждого статуса
    # Было: for status in statuses: count = query.filter(...).count() -> N запросов
    # Стало: один запрос с группировкой по status_id
    status_query = select(Request.status_id, func.count(Request.id).label('count'))
    if filters:
        status_query = status_query.where(and_(*filters))
    status_query = status_query.group_by(Request.status_id)
    status_stats_raw = await db.execute(status_query)
    status_stats_raw = status_stats_raw.fetchall()
    
    # Получаем все статусы для маппинга
    result = await db.execute(select(RequestStatus))
    statuses = list(result.scalars().all())
    status_map = {s.id: s for s in statuses}
    
    status_stats = {}
    for status in statuses:
        # Находим count из агрегированного результата
        count = next((r.count for r in status_stats_raw if r.status_id == status.id), 0)
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
        status_stats[status.code] = {
            "name": status.name,
            "count": count,
            "percentage": round(count / total * 100, 2) if total > 0 else 0
        }
    
<<<<<<< HEAD
    # Статистика по категориям
    categories = db.query(RequestCategory).all()
    category_stats = {}
    
    for category in categories:
        count = query.filter(Request.category_id == category.id).count()
=======
    # OPTIMIZATION: Один запрос с GROUP BY вместо цикла с отдельными COUNT для каждой категории
    # Было: for category in categories: count = query.filter(...).count() -> N запросов
    # Стало: один запрос с группировкой по category_id
    category_query = select(Request.category_id, func.count(Request.id).label('count'))
    if filters:
        category_query = category_query.where(and_(*filters))
    category_query = category_query.group_by(Request.category_id)
    category_stats_raw = await db.execute(category_query)
    category_stats_raw = category_stats_raw.fetchall()
    
    # Получаем все категории для маппинга
    result = await db.execute(select(RequestCategory))
    categories = list(result.scalars().all())
    category_map = {c.id: c for c in categories}
    
    category_stats = {}
    for category in categories:
        # Находим count из агрегированного результата
        count = next((r.count for r in category_stats_raw if r.category_id == category.id), 0)
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
        category_stats[category.name] = {
            "count": count,
            "percentage": round(count / total * 100, 2) if total > 0 else 0
        }
    
<<<<<<< HEAD
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
=======
    # Среднее время решения - используем SQL AVG агрегацию
    result = await db.execute(
        select(RequestStatus).where(RequestStatus.code == "closed")
    )
    closed_status = result.scalar_one_or_none()
    if closed_status:
        # OPTIMIZATION: используем SQL AVG вместо загрузки всех записей в Python
        resolution_query = select(
            func.avg(
                func.extract('epoch', Request.closed_at - Request.created_at) / 86400
            ).label('avg_days')
        ).where(Request.status_id == closed_status.id)
        if filters:
            resolution_query = resolution_query.where(and_(*filters))
        
        avg_result = await db.execute(resolution_query)
        avg_resolution_days = avg_result.scalar() or 0
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    else:
        avg_resolution_days = 0
    
    return {
        "total_requests": total,
        "by_status": status_stats,
        "by_category": category_stats,
        "average_resolution_days": round(avg_resolution_days, 1),
        "district_id": district_id
    }

<<<<<<< HEAD
def check_duplicate_request(db: Session, user_id: int, text: str, hours: int = 24) -> bool:
=======
async def check_duplicate_request(db: AsyncSession, user_id: int, text: str, hours: int = 24) -> bool:
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    """Проверка на похожие обращения за последние N часов"""
    from datetime import datetime, timedelta
    from difflib import SequenceMatcher
    
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
<<<<<<< HEAD
    recent = db.query(Request).filter(
        Request.user_id == user_id,
        Request.created_at >= cutoff_time
    ).all()
=======
    result = await db.execute(
        select(Request).where(
            Request.user_id == user_id,
            Request.created_at >= cutoff_time
        )
    )
    recent = list(result.scalars().all())
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    
    for req in recent:
        # Сравниваем заголовки
        title_similarity = SequenceMatcher(None, text, req.title).ratio()
        if title_similarity > 0.7:  # 70% схожести
            return True
        
        # Сравниваем описание
        desc_similarity = SequenceMatcher(None, text, req.description).ratio()
        if desc_similarity > 0.6:  # 60% схожести
            return True
    
    return False