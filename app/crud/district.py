"""
CRUD операции для работы с округами (District)

Этот модуль инкапсулирует всю логику работы с базой данных для сущности District.
Используется в API эндпоинтах для отделения бизнес-логики от HTTP слоя.

Функции:
- get_district: получение одного округа по ID
- get_districts: список округов с пагинацией
- get_district_with_deputies: округ с загруженными депутатами
- get_deputies_by_district: список депутатов округа
- create_district: создание нового округа
- update_district: обновление данных округа
- delete_district: удаление округа
"""

from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.db.models import District, Deputy
from app.schemas.district import DistrictCreate, DistrictUpdate


def get_district(db: Session, district_id: int) -> Optional[District]:
    """
    Получить округ по ID

    Параметры:
    - db: сессия базы данных
    - district_id: уникальный идентификатор округа

    Возвращает:
    - Объект District если найден, иначе None
    """
    return db.query(District).filter(District.id == district_id).first()


def get_districts(db: Session, skip: int = 0, limit: int = 100) -> List[District]:
    """
    Получить список округов с пагинацией

    Параметры:
    - db: сессия базы данных
    - skip: количество записей для пропуска (для пагинации)
    - limit: максимальное количество записей

    Возвращает:
    - Список объектов District
    """
    return db.query(District).offset(skip).limit(limit).all()


def get_district_with_deputies(db: Session, district_id: int) -> Optional[District]:
    """
    Получить округ вместе со списком депутатов

    Использует joinedload для оптимизации запроса (избегает N+1 проблемы).

    Параметры:
    - db: сессия базы данных
    - district_id: ID округа

    Возвращает:
    - Объект District с загруженной связью deputies, или None
    """
    return (
        db.query(District)
        .options(joinedload(District.deputies))
        .filter(District.id == district_id)
        .first()
    )


def get_deputies_by_district(db: Session, district_id: int) -> List[Deputy]:
    """
    Получить список депутатов по ID округа

    Параметры:
    - db: сессия базы данных
    - district_id: ID округа

    Возвращает:
    - Список объектов Deputy
    """
    return db.query(Deputy).filter(Deputy.district_id == district_id).all()


def create_district(db: Session, district_data: DistrictCreate) -> District:
    """
    Создать новый округ

    Параметры:
    - db: сессия базы данных
    - district_data: схема с данными для создания (name, description)

    Возвращает:
    - Созданный объект District с присвоенным ID

    Логика:
    1. Создаём новый экземпляр District из переданных данных
    2. Добавляем в сессию БД
    3. Коммитим транзакцию
    4. Обновляем объект (получаем автогенерируемый ID)
    """
    new_district = District(
        name=district_data.name,
        description=district_data.description
    )

    db.add(new_district)
    db.commit()
    db.refresh(new_district)

    return new_district


def update_district(
    db: Session,
    district_id: int,
    district_data: DistrictUpdate
) -> Optional[District]:
    """
    Обновить данные существующего округа

    Параметры:
    - db: сессия базы данных
    - district_id: ID обновляемого округа
    - district_data: схема с данными для обновления (частичное обновление)

    Возвращает:
    - Обновлённый объект District, или None если округ не найден

    Логика:
    1. Находим округ по ID
    2. Если не найден — возвращаем None
    3. Используем dict(exclude_unset=True) для обновления только переданных полей
    4. Коммитим изменения и возвращаем обновлённый объект
    """
    district = db.query(District).filter(District.id == district_id).first()

    if not district:
        return None

    # Получаем только те поля, которые были явно установлены в запросе
    update_data = district_data.dict(exclude_unset=True)

    # Обновляем каждое поле
    for field, value in update_data.items():
        if hasattr(district, field):
            setattr(district, field, value)

    db.commit()
    db.refresh(district)

    return district


def delete_district(db: Session, district_id: int) -> bool:
    """
    Удалить округ

    ВАЖНО: Перед вызовом этой функции необходимо убедиться,
    что в округе нет депутатов и обращений (проверка делается в endpoint).

    Параметры:
    - db: сессия базы данных
    - district_id: ID удаляемого округа

    Возвращает:
    - True если удаление успешно
    - False если округ не найден

    Логика:
    1. Находим округ по ID
    2. Если не найден — возвращаем False
    3. Удаляем объект
    4. Коммитим транзакцию
    """
    district = db.query(District).filter(District.id == district_id).first()

    if not district:
        return False

    db.delete(district)
    db.commit()

    return True