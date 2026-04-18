from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.api import deps
from app.schemas.district import District, DistrictWithDeputies
from app.schemas.deputy import Deputy
from app.crud import district as crud_district

router = APIRouter()

@router.get("/", response_model=List[District])
def read_districts(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
):
    """Получить список всех округов"""
    districts = crud_district.get_districts(db, skip=skip, limit=limit)
    return districts

@router.get("/{district_id}", response_model=DistrictWithDeputies)
def read_district(
    district_id: int,
    db: Session = Depends(deps.get_db),
):
    """Получить округ по ID с депутатами"""
    district = crud_district.get_district(db, district_id)
    if not district:
        raise HTTPException(status_code=404, detail="Округ не найден")
    return district

@router.get("/{district_id}/deputies", response_model=List[Deputy])
def read_deputies_by_district(
    district_id: int,
    db: Session = Depends(deps.get_db),
):
    """Получить депутатов конкретного округа"""
    # Проверяем существование округа
    district = crud_district.get_district(db, district_id)
    if not district:
        raise HTTPException(status_code=404, detail="Округ не найден")
    deputies = crud_district.get_deputies_by_district(db, district_id)
    return deputies