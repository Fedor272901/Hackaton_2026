from sqlalchemy.orm import Session
from app.db.models import District, Deputy

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