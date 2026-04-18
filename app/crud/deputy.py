"""
CRUD операции для работы с депутатами (Deputy)

Этот модуль инкапсулирует всю логику работы с базой данных для сущности Deputy.
Используется в API эндпоинтах для отделения бизнес-логики от HTTP слоя.

Функции:
- get_deputy: получение одного депутата по ID
- get_deputies: список всех депутатов с пагинацией
- get_deputy_by_user_id: поиск депутата по ID пользователя
- get_deputies_by_district: список депутатов конкретного округа
- create_deputy: назначение нового депутата
- update_deputy: обновление данных депутата (перевод в другой округ и т.д.)
- delete_deputy: снятие полномочий депутата
"""

from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime

from app.db.models import Deputy, User, District
from app.schemas.deputy import DeputyCreate, DeputyUpdate


def get_deputy(db: Session, deputy_id: int) -> Optional[Deputy]:
    """
    Получить депутата по ID

    Параметры:
    - db: сессия базы данных
    - deputy_id: уникальный идентификатор записи депутата

    Возвращает:
    - Объект Deputy если найден, иначе None

    Использует joinedload для загрузки связанных данных (user, district)
    чтобы избежать N+1 запросов при последующем доступе к связям.
    """
    return (
        db.query(Deputy)
        .options(
            joinedload(Deputy.user),
            joinedload(Deputy.district)
        )
        .filter(Deputy.id == deputy_id)
        .first()
    )


def get_deputies(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    district_id: Optional[int] = None
) -> List[Deputy]:
    """
    Получить список депутатов с пагинацией и опциональной фильтрацией по округу

    Параметры:
    - db: сессия базы данных
    - skip: количество записей для пропуска (для пагинации)
    - limit: максимальное количество записей
    - district_id: опциональный фильтр по ID округа

    Возвращает:
    - Список объектов Deputy

    Логика:
    1. Формируем базовый запрос с загрузкой связанных данных
    2. Если указан district_id — добавляем фильтр
    3. Применяем пагинацию через offset/limit
    """
    query = db.query(Deputy).options(
        joinedload(Deputy.user),
        joinedload(Deputy.district)
    )

    if district_id is not None:
        query = query.filter(Deputy.district_id == district_id)

    return query.offset(skip).limit(limit).all()


def get_deputy_by_user_id(db: Session, user_id: int) -> Optional[Deputy]:
    """
    Найти депутата по ID связанного пользователя

    Используется когда нужно проверить является ли пользователь депутатом
    и получить его данные (округ, дата назначения и т.д.)

    Параметры:
    - db: сессия базы данных
    - user_id: ID пользователя в таблице users

    Возвращает:
    - Объект Deputy если пользователь является депутатом, иначе None
    """
    return (
        db.query(Deputy)
        .options(
            joinedload(Deputy.user),
            joinedload(Deputy.district)
        )
        .filter(Deputy.user_id == user_id)
        .first()
    )


def get_deputies_by_district(db: Session, district_id: int) -> List[Deputy]:
    """
    Получить всех депутатов конкретного округа

    Параметры:
    - db: сессия базы данных
    - district_id: ID округа

    Возвращает:
    - Список объектов Deputy принадлежащих этому округу
    """
    return (
        db.query(Deputy)
        .options(
            joinedload(Deputy.user),
            joinedload(Deputy.district)
        )
        .filter(Deputy.district_id == district_id)
        .all()
    )


def create_deputy(
    db: Session,
    deputy_data: DeputyCreate,
    appointed_by_user_id: int
) -> Deputy:
    """
    Назначить нового депутата

    ВАЖНО: Перед вызовом необходимо убедиться что:
    1. Пользователь существует и имеет роль "deputy"
    2. Округ существует
    3. Пользователь ещё не является депутатом (нет активной записи)

    Параметры:
    - db: сессия базы данных
    - deputy_data: схема с данными (user_id, district_id, office_phone, office_address)
    - appointed_by_user_id: ID администратора который назначает (для аудита)

    Возвращает:
    - Созданный объект Deputy с присвоенным ID и appointed_at

    Логика:
    1. Создаём новую запись депутата
    2. Устанавливаем дату назначения (appointed_at)
    3. Коммитим транзакцию
    4. Возвращаем обновлённый объект с загруженными связями
    """
    new_deputy = Deputy(
        user_id=deputy_data.user_id,
        district_id=deputy_data.district_id,
        office_phone=deputy_data.office_phone,
        office_address=deputy_data.office_address,
        appointed_at=datetime.utcnow()
    )

    db.add(new_deputy)
    db.commit()
    db.refresh(new_deputy)

    # Загружаем связанные данные для ответа
    return get_deputy(db, new_deputy.id)


def update_deputy(
    db: Session,
    deputy_id: int,
    deputy_data: DeputyUpdate
) -> Optional[Deputy]:
    """
    Обновить данные депутата

    Позволяет изменить:
    - Округ прикрепления (district_id)
    - Служебный телефон
    - Служебный адрес

    ВАЖНО: При смене округа необходимо убедиться что новый округ существует.

    Параметры:
    - db: сессия базы данных
    - deputy_id: ID обновляемой записи депутата
    - deputy_data: схема с данными для обновления (частичное обновление)

    Возвращает:
    - Обновлённый объект Deputy, или None если депутат не найден

    Логика:
    1. Находим депутата по ID
    2. Если не найден — возвращаем None
    3. Используем dict(exclude_unset=True) для обновления только переданных полей
    4. Коммитим изменения
    5. Возвращаем обновлённый объект с загруженными связями
    """
    deputy = db.query(Deputy).filter(Deputy.id == deputy_id).first()

    if not deputy:
        return None

    # Получаем только те поля, которые были явно установлены в запросе
    update_data = deputy_data.dict(exclude_unset=True)

    # Если меняется округ — проверяем его существование
    if "district_id" in update_data and update_data["district_id"] != deputy.district_id:
        new_district = db.query(District).filter(
            District.id == update_data["district_id"]
        ).first()

        if not new_district:
            raise ValueError(f"Округ с ID {update_data['district_id']} не найден")

    # Обновляем каждое поле
    for field, value in update_data.items():
        if hasattr(deputy, field):
            setattr(deputy, field, value)

    db.commit()
    db.refresh(deputy)

    # Возвращаем с загруженными связями
    return get_deputy(db, deputy.id)


def delete_deputy(db: Session, deputy_id: int) -> bool:
    """
    Снять полномочия депутата (удалить запись)

    ВАЖНО: Перед удалением необходимо:
    1. Переназначить все обращения этого депутата на других депутатов ИЛИ снять назначения
    2. Убедиться что нет активных процессов с участием депутата

    Параметры:
    - db: сессия базы данных
    - deputy_id: ID удаляемой записи депутата

    Возвращает:
    - True если удаление успешно
    - False если депутат не найден

    Логика:
    1. Находим депутата по ID
    2. Если не найден — возвращаем False
    3. Удаляем запись (связь пользователь-округ)
    4. Коммитим транзакцию

    Примечание: Пользователь остаётся в системе, просто теряет статус депутата.
    """
    deputy = db.query(Deputy).filter(Deputy.id == deputy_id).first()

    if not deputy:
        return False

    db.delete(deputy)
    db.commit()

    return True


def reassign_requests_from_deputy(
    db: Session,
    deputy_id: int,
    new_deputy_id: Optional[int] = None
) -> int:
    """
    Переназначить обращения с одного депутата на другого

    Вызывается перед удалением депутата чтобы не потерять обращения.

    Параметры:
    - db: сессия базы данных
    - deputy_id: ID депутата с которого снимаются обращения
    - new_deputy_id: ID депутата которому передаются обращения (или None для снятия назначения)

    Возвращает:
    - Количество переназначенных обращений

    Логика:
    1. Находим все обращения назначенные на этого депутата
    2. Обновляем assigned_deputy_id на новый или NULL
    3. Возвращаем количество затронутых записей
    """
    from app.db.models import Request

    count = db.query(Request).filter(
        Request.assigned_deputy_id == deputy_id
    ).count()

    # Обновляем назначения
    db.query(Request).filter(
        Request.assigned_deputy_id == deputy_id
    ).update({
        "assigned_deputy_id": new_deputy_id
    })

    db.commit()

    return count