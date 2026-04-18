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
    return True