<<<<<<< HEAD
from sqlalchemy.orm import Session
from app.db.models import District, Deputy, User
from app.schemas.district import DistrictCreate, DistrictUpdate
from app.core.roles import Role

def get_district(db: Session, district_id: int):
    """Получить округ по ID"""
    return db.query(District).filter(District.id == district_id).first()

def get_districts(db: Session, skip: int = 0, limit: int = 100):
    """Получить список округов с пагинацией"""
    return db.query(District).offset(skip).limit(limit).all()

def get_district_with_deputies(db: Session, district_id: int):
    """Получить округ вместе со списком депутатов"""
    return db.query(District).filter(District.id == district_id).first()

def get_deputies_by_district(db: Session, district_id: int):
    """Получить список депутатов по ID округа"""
    return db.query(Deputy).filter(Deputy.district_id == district_id).all()


# НОВЫЕ ФУНКЦИИ

def create_district(db: Session, district_data: DistrictCreate):
    district = District(
        name=district_data.name,
        description=district_data.description,
        geometry=district_data.geometry
    )
    db.add(district)
    db.commit()
    db.refresh(district)
    return district


def update_district(db: Session, district_id: int, update_data: DistrictUpdate):
    district = db.query(District).filter(District.id == district_id).first()
    if not district:
        return None
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(district, field, value)
    
    db.commit()
    db.refresh(district)
    return district


def delete_district(db: Session, district_id: int) -> bool:
    district = db.query(District).filter(District.id == district_id).first()
    if not district:
        return False
    
    db.delete(district)
    db.commit()
    return True


def assign_deputy_to_district(db: Session, user_id: int, district_id: int):
    # Проверяем что пользователь существует и имеет роль deputy
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None, "Пользователь не найден"
    
    if user.role != Role.DEPUTY:
        return None, "Пользователь не является депутатом"
    
    # Проверяем что округ существует
    district = db.query(District).filter(District.id == district_id).first()
    if not district:
        return None, "Округ не найден"
    
    # Проверяем не привязан ли уже депутат к другому округу
    existing = db.query(Deputy).filter(Deputy.user_id == user_id).first()
    if existing:
        # Обновляем округ
        existing.district_id = district_id
        db.commit()
        db.refresh(existing)
        return existing, None
    
    # Создаем новую привязку
    deputy = Deputy(user_id=user_id, district_id=district_id)
    db.add(deputy)
    db.commit()
    db.refresh(deputy)
    return deputy, None


def remove_deputy_from_district(db: Session, user_id: int):
    deputy = db.query(Deputy).filter(Deputy.user_id == user_id).first()
    if not deputy:
        return False
    
    db.delete(deputy)
    db.commit()
=======
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

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from typing import List, Optional

from app.db.models import District, Deputy
from app.schemas.district import DistrictCreate, DistrictUpdate


async def get_district(db: AsyncSession, district_id: int) -> Optional[District]:
    """
    Получить округ по ID

    Параметры:
    - db: сессия базы данных
    - district_id: уникальный идентификатор округа

    Возвращает:
    - Объект District если найден, иначе None
    """
    result = await db.execute(select(District).where(District.id == district_id))
    return result.scalar_one_or_none()


async def get_districts(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[District]:
    """
    Получить список округов с пагинацией

    Параметры:
    - db: сессия базы данных
    - skip: количество записей для пропуска (для пагинации)
    - limit: максимальное количество записей

    Возвращает:
    - Список объектов District
    """
    query = select(District).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def get_district_with_deputies(db: AsyncSession, district_id: int) -> Optional[District]:
    """
    Получить округ вместе со списком депутатов

    Использует joinedload для оптимизации запроса (избегает N+1 проблемы).

    Параметры:
    - db: сессия базы данных
    - district_id: ID округа

    Возвращает:
    - Объект District с загруженной связью deputies, или None
    """
    result = await db.execute(
        select(District)
        .options(joinedload(District.deputies))
        .where(District.id == district_id)
    )
    return result.unique().scalar_one_or_none()


async def get_deputies_by_district(db: AsyncSession, district_id: int) -> List[Deputy]:
    """
    Получить список депутатов по ID округа

    Параметры:
    - db: сессия базы данных
    - district_id: ID округа

    Возвращает:
    - Список объектов Deputy
    """
    result = await db.execute(
        select(Deputy).where(Deputy.district_id == district_id)
    )
    return result.scalars().all()


async def create_district(db: AsyncSession, district_data: DistrictCreate) -> District:
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
    await db.commit()
    await db.refresh(new_district)

    return new_district


async def update_district(
    db: AsyncSession,
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
    result = await db.execute(select(District).where(District.id == district_id))
    district = result.scalar_one_or_none()

    if not district:
        return None

    # Получаем только те поля, которые были явно установлены в запросе
    update_data = district_data.dict(exclude_unset=True)

    # Обновляем каждое поле
    for field, value in update_data.items():
        if hasattr(district, field):
            setattr(district, field, value)

    await db.commit()
    await db.refresh(district)

    return district


async def delete_district(db: AsyncSession, district_id: int) -> bool:
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
    result = await db.execute(select(District).where(District.id == district_id))
    district = result.scalar_one_or_none()

    if not district:
        return False

    await db.delete(district)
    await db.commit()

>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    return True