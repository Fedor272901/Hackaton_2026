# app/crud/district.py

from sqlalchemy.orm import Session
from geoalchemy2 import functions as geofunc
from app.db.models import District, Deputy, User
from app.schemas.district import DistrictCreate, DistrictUpdate
from app.core.roles import Role
import json

def get_district(db: Session, district_id: int):
    return db.query(District).filter(District.id == district_id).first()

def get_districts(db: Session, skip: int = 0, limit: int = 100):
    return db.query(District).offset(skip).limit(limit).all()

def get_district_with_deputies(db: Session, district_id: int):
    return db.query(District).filter(District.id == district_id).first()

def get_deputies_by_district(db: Session, district_id: int):
    return db.query(Deputy).filter(Deputy.district_id == district_id).all()

def create_district(db: Session, district_data: DistrictCreate):
    """Создание округа с геометрией"""
    # Конвертируем GeoJSON в PostGIS geometry
    geometry = District.from_geojson(district_data.geometry.model_dump())
    
    district = District(
        name=district_data.name,
        description=district_data.description,
        geom=geometry
    )
    db.add(district)
    db.commit()
    db.refresh(district)
    return district

def update_district(db: Session, district_id: int, update_data: DistrictUpdate):
    """Обновление округа (включая геометрию)"""
    district = db.query(District).filter(District.id == district_id).first()
    if not district:
        return None
    
    update_dict = update_data.model_dump(exclude_unset=True)
    
    # Особая обработка для геометрии
    if 'geometry' in update_dict and update_dict['geometry'] is not None:
        geometry = District.from_geojson(update_dict['geometry'])
        district.geom = geometry
        del update_dict['geometry']
    
    # Остальные поля
    for field, value in update_dict.items():
        setattr(district, field, value)
    
    db.commit()
    db.refresh(district)
    return district

def delete_district(db: Session, district_id: int) -> bool:
    """Полное удаление округа вместе с геометрией"""
    district = db.query(District).filter(District.id == district_id).first()
    if not district:
        return False
    
    # Отвязываем депутатов
    db.query(Deputy).filter(Deputy.district_id == district_id).update(
        {Deputy.district_id: None}
    )
    
    # Удаляем округ (геометрия удалится каскадно)
    db.delete(district)
    db.commit()
    return True

def check_point_in_district(db: Session, latitude: float, longitude: float):
    """Проверка вхождения точки в округ"""
    point_wkt = f'POINT({longitude} {latitude})'
    
    district = db.query(District).filter(
        geofunc.ST_Within(
            geofunc.ST_SetSRID(geofunc.ST_GeomFromText(point_wkt), 4326),
            District.geom
        )
    ).first()
    
    return district

def assign_deputy_to_district(db: Session, user_id: int, district_id: int):
    """Привязка депутата к округу"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None, "Пользователь не найден"
    
    if user.role != Role.DEPUTY:
        return None, "Пользователь не является депутатом"
    
    district = db.query(District).filter(District.id == district_id).first()
    if not district:
        return None, "Округ не найден"
    
    existing = db.query(Deputy).filter(Deputy.user_id == user_id).first()
    if existing:
        existing.district_id = district_id
        db.commit()
        db.refresh(existing)
        return existing, None
    
    deputy = Deputy(user_id=user_id, district_id=district_id)
    db.add(deputy)
    db.commit()
    db.refresh(deputy)
    return deputy, None

def remove_deputy_from_district(db: Session, user_id: int):
    """Отвязка депутата от округа"""
    deputy = db.query(Deputy).filter(Deputy.user_id == user_id).first()
    if not deputy:
        return False
    
    db.delete(deputy)
    db.commit()
    return True