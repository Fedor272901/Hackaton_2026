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
from sqlalchemy.orm import Session
from typing import List, Optional
from app.api import deps
from app.db.database import get_db
from app.db.models import User, District, Deputy

# Схемы Pydantic для валидации входных/выходных данных
from app.schemas.district import District, DistrictCreate, DistrictUpdate, DistrictWithDeputies
from app.schemas.deputy import Deputy as DeputySchema

# CRUD функции для инкапсуляции логики работы с БД
from app.crud import district as crud_district

# Механизм проверки ролей — возвращает 403 если пользователь не ADMIN
from app.core.permissions import require_admin

# Для получения текущего пользователя (JWT токен декодируется автоматически)
from app.core.dependencies import get_current_active_user


router = APIRouter()


# ========================
# PUBLIC ENDPOINTS (доступны всем)
# ========================

@router.get("/", response_model=List[District])
def read_districts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
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
    districts = crud_district.get_districts(db, skip=skip, limit=limit)
    return districts


@router.get("/{district_id}", response_model=DistrictWithDeputies)
def read_district(
    district_id: int,
    db: Session = Depends(get_db)
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
    district = crud_district.get_district_with_deputies(db, district_id)

    if not district:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Округ с ID {district_id} не найден"
        )

    return district


@router.get("/{district_id}/deputies", response_model=List[DeputySchema])
def read_deputies_by_district(
    district_id: int,
    db: Session = Depends(get_db)
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
    district = crud_district.get_district(db, district_id)

    if not district:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Округ с ID {district_id} не найден"
        )

    deputies = crud_district.get_deputies_by_district(db, district_id)
    return deputies


# ========================
# ADMIN ONLY ENDPOINTS (CRUD операции)
# ========================

@router.post("/", response_model=District, status_code=status.HTTP_201_CREATED)
def create_district(
    district_data: DistrictCreate,
    db: Session = Depends(get_db),
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
    # Проверяем что округ с таким именем ещё не существует
    existing = db.query(District).filter(District.name == district_data.name).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Округ с названием '{district_data.name}' уже существует"
        )

    # Создаём новый округ через CRUD функцию
    new_district = crud_district.create_district(db, district_data)

    return new_district


@router.put("/{district_id}", response_model=District)
def update_district(
    district_id: int,
    district_data: DistrictUpdate,
    db: Session = Depends(get_db),
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
    # Проверяем существование округа
    existing_district = crud_district.get_district(db, district_id)

    if not existing_district:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Округ с ID {district_id} не найден"
        )

    # Если меняется название — проверяем на уникальность
    if district_data.name is not None and district_data.name != existing_district.name:
        duplicate = db.query(District).filter(
            District.name == district_data.name,
            District.id != district_id  # Исключаем текущий округ из проверки
        ).first()

        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Округ с названием '{district_data.name}' уже существует"
            )

    # Выполняем обновление через CRUD
    updated_district = crud_district.update_district(db, district_id, district_data)

    return updated_district


@router.delete("/{district_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_district(
    district_id: int,
    db: Session = Depends(get_db),
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
    # Проверяем существование округа
    district = crud_district.get_district(db, district_id)

    if not district:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Округ с ID {district_id} не найден"
        )

    # Проверяем есть ли депутаты в этом округе (защита от удаления с связями)
    deputies_count = db.query(Deputy).filter(Deputy.district_id == district_id).count()

    if deputies_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Невозможно удалить округ: в нём числится депутатов: {deputies_count}. Сначала переназначьте депутатов."
        )

    # Проверяем есть ли обращения в этом округе
    from app.db.models import Request
    requests_count = db.query(Request).filter(Request.district_id == district_id).count()

    if requests_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Невозможно удалить округ: в нём есть обращений: {requests_count}. Сначала архивируйте обращения."
        )

    # Удаляем округ через CRUD функцию
    crud_district.delete_district(db, district_id)

    # Возвращаем 204 No Content (пустое тело ответа)
    return None