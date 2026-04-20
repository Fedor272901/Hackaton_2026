<<<<<<< HEAD
=======
<<<<<<< HEAD
from sqlalchemy.orm import Session
from app.db import models


def create_status(db: Session, data):
=======
>>>>>>> front/dev
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import models


async def create_status(db: AsyncSession, data):
<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
    status = models.RequestStatus(
        code=data.code,
        name=data.name,
    )
    db.add(status)
<<<<<<< HEAD
=======
<<<<<<< HEAD
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
=======
>>>>>>> front/dev
    await db.commit()
    await db.refresh(status)
    return status


async def get_status(db: AsyncSession, status_id: int):
    result = await db.execute(
        select(models.RequestStatus).where(models.RequestStatus.id == status_id)
    )
    return result.scalar_one_or_none()


async def get_status_by_code(db: AsyncSession, code: str):
    result = await db.execute(
        select(models.RequestStatus).where(models.RequestStatus.code == code)
    )
    return result.scalar_one_or_none()


async def get_statuses(db: AsyncSession):
    result = await db.execute(
        select(models.RequestStatus).order_by(models.RequestStatus.id)
    )
    return result.scalars().all()


async def update_status(db: AsyncSession, status_id: int, data):
    status = await get_status(db, status_id)
<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
    if status is None:
        return None

    if data.code is not None:
        status.code = data.code
    if data.name is not None:
        status.name = data.name

<<<<<<< HEAD
=======
<<<<<<< HEAD
    db.commit()
    db.refresh(status)
    return status


def delete_status(db: Session, status_id: int):
    status = get_status(db, status_id)
    if status is None:
        return False
    db.delete(status)
    db.commit()
=======
>>>>>>> front/dev
    await db.commit()
    await db.refresh(status)
    return status


async def delete_status(db: AsyncSession, status_id: int):
    status = await get_status(db, status_id)
    if status is None:
        return False
    await db.delete(status)
    await db.commit()
<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
    return True
