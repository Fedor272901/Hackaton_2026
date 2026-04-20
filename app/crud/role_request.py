from datetime import datetime

<<<<<<< HEAD
=======
<<<<<<< HEAD
from sqlalchemy.orm import Session
from app.db import models


def create_role_request(db: Session, data):
    """Гражданин подаёт заявку на роль депутата."""

    # Проверяем: нет ли уже висящей заявки от этого пользователя
    existing = db.query(models.RoleRequest).filter(
        models.RoleRequest.user_id == data.user_id,
        models.RoleRequest.status == "pending",
    ).first()
=======
>>>>>>> front/dev
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import models


async def create_role_request(db: AsyncSession, data):
    """Гражданин подаёт заявку на роль депутата."""

    # Проверяем: нет ли уже висящей заявки от этого пользователя
    existing_query = select(models.RoleRequest).where(
        models.RoleRequest.user_id == data.user_id,
        models.RoleRequest.status == "pending",
    )
    result = await db.execute(existing_query)
    existing = result.scalar_one_or_none()
<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev

    if existing:
        return None  # в эндпоинте вернём 409

    role_request = models.RoleRequest(
        user_id=data.user_id,
        requested_role=data.requested_role,
        status="pending",
        user_comment=data.user_comment,
    )
    db.add(role_request)
<<<<<<< HEAD
=======
<<<<<<< HEAD
    db.commit()
    db.refresh(role_request)
    return role_request


def get_role_request(db: Session, request_id: int):
    return db.query(models.RoleRequest).filter(
        models.RoleRequest.id == request_id
    ).first()


def get_role_requests(db: Session, status: str | None = None):
    """Список всех заявок. Можно фильтровать по статусу: pending / approved / rejected."""
    query = db.query(models.RoleRequest)
    if status is not None:
        query = query.filter(models.RoleRequest.status == status)
    return query.order_by(models.RoleRequest.created_at.desc()).all()


def get_role_requests_by_user(db: Session, user_id: int):
    """Все заявки конкретного пользователя."""
    return db.query(models.RoleRequest).filter(
        models.RoleRequest.user_id == user_id
    ).order_by(models.RoleRequest.created_at.desc()).all()


def decide_role_request(db: Session, request_id: int, data):
=======
>>>>>>> front/dev
    await db.commit()
    await db.refresh(role_request)
    return role_request


async def get_role_request(db: AsyncSession, request_id: int):
    result = await db.execute(
        select(models.RoleRequest).where(models.RoleRequest.id == request_id)
    )
    return result.scalar_one_or_none()


async def get_role_requests(db: AsyncSession, status: str | None = None):
    """Список всех заявок. Можно фильтровать по статусу: pending / approved / rejected."""
    query = select(models.RoleRequest)
    if status is not None:
        query = query.where(models.RoleRequest.status == status)
    query = query.order_by(models.RoleRequest.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


async def get_role_requests_by_user(db: AsyncSession, user_id: int):
    """Все заявки конкретного пользователя."""
    query = select(models.RoleRequest).where(
        models.RoleRequest.user_id == user_id
    ).order_by(models.RoleRequest.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


async def decide_role_request(db: AsyncSession, request_id: int, data):
<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
    """
    Админ одобряет или отклоняет заявку.

    Если status = "approved" — выполняем ТРАНЗАКЦИЮ:
      1. Меняем статус заявки на "approved".
      2. Меняем роль пользователя на "deputy".
      3. Создаём запись в таблице deputies.
    Всё в одном db.commit() — либо всё, либо ничего.

    Если status = "rejected" — только меняем статус заявки.
    """

    # Проверяем что статус допустимый
    if data.status not in ("approved", "rejected"):
        return {"error": "Статус должен быть approved или rejected"}

<<<<<<< HEAD
    role_request = await get_role_request(db, request_id)
=======
<<<<<<< HEAD
    role_request = get_role_request(db, request_id)
=======
    role_request = await get_role_request(db, request_id)
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
    if role_request is None:
        return {"error": "Заявка не найдена"}

    if role_request.status != "pending":
        return {"error": "Заявка уже обработана"}

    # Обновляем саму заявку
    role_request.status = data.status
    role_request.admin_comment = data.admin_comment
    role_request.processed_by_admin_id = data.admin_id
    role_request.decided_at = datetime.utcnow()

    if data.status == "approved":
        # Меняем роль пользователя
<<<<<<< HEAD
=======
<<<<<<< HEAD
        user = db.query(models.User).filter(
            models.User.id == role_request.user_id
        ).first()

        if user is None:
            db.rollback()
=======
>>>>>>> front/dev
        user_query = select(models.User).where(
            models.User.id == role_request.user_id
        )
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()

        if user is None:
            await db.rollback()
<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
            return {"error": "Пользователь не найден"}

        user.role = "deputy"

        # Создаём запись в deputies (если ещё нет)
<<<<<<< HEAD
=======
<<<<<<< HEAD
        existing_deputy = db.query(models.Deputy).filter(
            models.Deputy.user_id == user.id
        ).first()
=======
>>>>>>> front/dev
        deputy_query = select(models.Deputy).where(
            models.Deputy.user_id == user.id
        )
        deputy_result = await db.execute(deputy_query)
        existing_deputy = deputy_result.scalar_one_or_none()
<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev

        if existing_deputy is None:
            deputy = models.Deputy(
                user_id=user.id,
                district_id=None,  # округ назначит админ отдельно (блок 3)
            )
            db.add(deputy)

    # Один коммит на всё — атомарно
<<<<<<< HEAD
    await db.commit()
    await db.refresh(role_request)
=======
<<<<<<< HEAD
    db.commit()
    db.refresh(role_request)
=======
    await db.commit()
    await db.refresh(role_request)
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
    return role_request
