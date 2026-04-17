from sqlalchemy.orm import Session
from app.db import models


def create_status(db: Session, data):
    status = models.RequestStatus(
        code=data.code,
        name=data.name,
    )
    db.add(status)
    db.commit()
    db.refresh(status)
    return status


def get_status(db: Session, status_id: int):
    return db.query(models.RequestStatus).filter(
        models.RequestStatus.id == status_id
    ).first()


def get_status_by_code(db: Session, code: str):
    return db.query(models.RequestStatus).filter(
        models.RequestStatus.code == code
    ).first()


def get_statuses(db: Session):
    return db.query(models.RequestStatus).order_by(
        models.RequestStatus.id
    ).all()


def update_status(db: Session, status_id: int, data):
    status = get_status(db, status_id)
    if status is None:
        return None

    if data.code is not None:
        status.code = data.code
    if data.name is not None:
        status.name = data.name

    db.commit()
    db.refresh(status)
    return status


def delete_status(db: Session, status_id: int):
    status = get_status(db, status_id)
    if status is None:
        return False
    db.delete(status)
    db.commit()
    return True
