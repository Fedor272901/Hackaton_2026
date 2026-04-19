from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.db.models import User
from app.schemas.district import (
    DistrictCreate,
    DistrictUpdate,
    DistrictResponse,
    DistrictWithDeputies,
    PointCheckRequest,
    PointCheckResponse
)
from app.schemas.deputy import DeputyResponse, AssignDeputyRequest
from app.crud import district as crud_district
from app.core.dependencies import get_current_active_user
from app.core.permissions import require_admin

router = APIRouter()

# =========================================================
# ПУБЛИЧНЫЕ РУЧКИ
# =========================================================

@router.get("/", response_model=List[DistrictResponse])
def read_districts(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
):
    """Получить список всех округов"""
    districts = crud_district.get_districts(db, skip=skip, limit=limit)
    
    # Добавляем GeoJSON в ответ
    result = []
    for d in districts:
        district_dict = {
            "id": d.id,
            "name": d.name,
            "description": d.description,
            "geometry": d.to_geojson()
        }
        result.append(district_dict)
    
    return result

@router.get("/{district_id}", response_model=DistrictWithDeputies)
def read_district(district_id: int, db: Session = Depends(get_db)):
    """Получить округ по ID вместе с депутатами"""
    district = crud_district.get_district_with_deputies(db, district_id)
    if not district:
        raise HTTPException(404, "Округ не найден")
    
    result = {
        "id": district.id,
        "name": district.name,
        "description": district.description,
        "geometry": district.to_geojson(),
        "deputies": district.deputies
    }
    return result

@router.post("/check-point", response_model=PointCheckResponse)
def check_point(point_data: PointCheckRequest, db: Session = Depends(get_db)):
    """
    Проверить, входит ли точка в какой-либо округ
    
    Пример запроса:
    {
        "latitude": 54.5293,
        "longitude": 36.2754
    }
    """
    district = crud_district.check_point_in_district(
        db, point_data.latitude, point_data.longitude
    )
    
    if district:
        return PointCheckResponse(
            is_inside=True,
            district_id=district.id,
            district_name=district.name,
            message=f"Точка находится в округе: {district.name}"
        )
    else:
        return PointCheckResponse(
            is_inside=False,
            message="Точка не принадлежит ни одному округу"
        )

# =========================================================
# АДМИНСКИЕ РУЧКИ
# =========================================================

@router.post("/", response_model=DistrictResponse, status_code=201)
def create_district(
    district_data: DistrictCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    [АДМИН] Создать новый округ с геометрией
    
    Пример тела запроса:
    {
        "name": "Ленинский округ",
        "description": "Центральная часть Калуги",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [36.2500, 54.5100],
                [36.3000, 54.5100],
                [36.3000, 54.5400],
                [36.2500, 54.5400],
                [36.2500, 54.5100]
            ]]
        }
    }
    """
    try:
        district = crud_district.create_district(db, district_data)
        return {
            "id": district.id,
            "name": district.name,
            "description": district.description,
            "geometry": district.to_geojson()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"Ошибка создания округа: {str(e)}")

@router.patch("/{district_id}", response_model=DistrictResponse)
def update_district(
    district_id: int,
    district_update: DistrictUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    [АДМИН] Обновить округ (включая геометрию)
    
    Пример обновления геометрии:
    PATCH /districts/1
    {
        "geometry": {
            "type": "Polygon",
            "coordinates": [[...новые координаты...]]
        }
    }
    """
    district = crud_district.update_district(db, district_id, district_update)
    if not district:
        raise HTTPException(404, "Округ не найден")
    
    return {
        "id": district.id,
        "name": district.name,
        "description": district.description,
        "geometry": district.to_geojson()
    }

@router.delete("/{district_id}", status_code=204)
def delete_district(
    district_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    [АДМИН] Полностью удалить округ
    
    ВНИМАНИЕ:
    - Удаляется запись об округе
    - Удаляются все геоданные из PostGIS
    - Депутаты отвязываются (district_id = NULL)
    - Обращения удаляются КАСКАДНО
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
    
    Пример:
    {
        "user_id": 5,
        "district_id": 1
    }
    """
    deputy, error = crud_district.assign_deputy_to_district(
        db, data.user_id, data.district_id
    )
    
    if error:
        raise HTTPException(400, error)
    
    return deputy