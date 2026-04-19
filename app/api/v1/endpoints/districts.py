from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.db.models import User
from app.schemas.district import (
    DistrictCreate, 
    DistrictUpdate, 
    DistrictResponse, 
    DistrictWithDeputies
)
from app.schemas.deputy import DeputyResponse, AssignDeputyRequest
from app.crud import district as crud_district
from app.core.dependencies import get_current_active_user
from app.core.permissions import require_admin

router = APIRouter()


# =========================================================
# ПУБЛИЧНЫЕ РУЧКИ (просмотр)
# =========================================================

@router.get("/", response_model=List[DistrictResponse])
def read_districts(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
):
    """
    Получить список всех округов
    
    Параметры:
    - skip: пропустить N записей (для пагинации)
    - limit: количество записей (1-100)
    
    Пример: GET /districts/?skip=0&limit=20
    """
    return crud_district.get_districts(db, skip=skip, limit=limit)


@router.get("/{district_id}", response_model=DistrictWithDeputies)
def read_district(
    district_id: int,
    db: Session = Depends(get_db),
):
    """
    Получить округ по ID вместе со списком депутатов
    
    Пример: GET /districts/1
    """
    district = crud_district.get_district_with_deputies(db, district_id)
    if not district:
        raise HTTPException(404, "Округ не найден")
    return district


@router.get("/{district_id}/deputies", response_model=List[DeputyResponse])
def read_deputies_by_district(
    district_id: int,
    db: Session = Depends(get_db),
):
    """
    Получить список депутатов конкретного округа
    
    Пример: GET /districts/1/deputies
    """
    district = crud_district.get_district(db, district_id)
    if not district:
        raise HTTPException(404, "Округ не найден")
    return crud_district.get_deputies_by_district(db, district_id)


# =========================================================
# АДМИНСКИЕ РУЧКИ (управление)
# =========================================================

@router.post("/", response_model=DistrictResponse, status_code=201)
def create_district(
    district_data: DistrictCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    [АДМИН] Создать новый округ
    
    Требуется роль: admin
    
    Поля:
    - name: название округа (обязательно)
    - description: описание (опционально)
    - geometry: геоданные в формате WKT/GeoJSON (опционально)
    
    Пример тела запроса:
    {
        "name": "Центральный округ",
        "description": "Центральная часть города",
        "geometry": null
    }
    
    Пример curl:
    curl -X POST http://localhost:8000/districts/ \
      -H "Authorization: Bearer TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"name": "Центральный округ", "description": "Центр города"}'
    """
    return crud_district.create_district(db, district_data)


@router.patch("/{district_id}", response_model=DistrictResponse)
def update_district(
    district_id: int,
    district_update: DistrictUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    [АДМИН] Обновить данные округа
    
    Требуется роль: admin
    
    Все поля опциональны - обновятся только переданные.
    
    Поля для обновления:
    - name: новое название
    - description: новое описание
    - geometry: новые геоданные
    
    Пример (обновить только название):
    PATCH /districts/1
    {
        "name": "Северный округ"
    }
    """
    district = crud_district.update_district(db, district_id, district_update)
    if not district:
        raise HTTPException(404, "Округ не найден")
    return district


@router.delete("/{district_id}", status_code=204)
def delete_district(
    district_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    [АДМИН] Удалить округ
    
    Требуется роль: admin
    
    ВНИМАНИЕ:
    - Удаление ПОЛНОЕ, без возможности восстановления
    - Все депутаты округа останутся без привязки (district_id = NULL)
    - Обращения округа будут удалены КАСКАДНО
    
    Пример: DELETE /districts/1
    """
    success = crud_district.delete_district(db, district_id)
    if not success:
        raise HTTPException(404, "Округ не найден")
    return None


@router.post("/assign-deputy", response_model=DeputyResponse, status_code=201)
def assign_deputy(
    data: AssignDeputyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    [АДМИН] Привязать депутата к округу
    
    Требуется роль: admin
    
    Правила:
    - Пользователь должен существовать
    - Пользователь должен иметь роль "deputy"
    - Если депутат уже привязан к другому округу - привязка обновится
    
    Поля:
    - user_id: ID пользователя с ролью deputy
    - district_id: ID округа
    
    Пример тела запроса:
    {
        "user_id": 5,
        "district_id": 1
    }
    
    Пример curl:
    curl -X POST http://localhost:8000/districts/assign-deputy \
      -H "Authorization: Bearer TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"user_id": 5, "district_id": 1}'
    """
    deputy, error = crud_district.assign_deputy_to_district(
        db, data.user_id, data.district_id
    )
    
    if error:
        raise HTTPException(400, error)
    
    return deputy


@router.delete("/deputies/{user_id}", status_code=204)
def remove_deputy(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    [АДМИН] Отвязать депутата от округа
    
    Требуется роль: admin
    
    После отвязки:
    - Депутат остается в системе с ролью "deputy"
    - Депутат больше не привязан ни к какому округу
    - Назначенные на него обращения остаются за ним
    
    Пример: DELETE /districts/deputies/5
    """
    success = crud_district.remove_deputy_from_district(db, user_id)
    if not success:
        raise HTTPException(404, "Депутат не найден или не привязан к округу")
    return None