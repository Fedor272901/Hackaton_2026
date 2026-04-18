# app/core/access.py

"""
Бизнес-логика доступа (кто что МОЖЕТ делать)

НЕ зависит от FastAPI
НЕ использует Depends

Используется внутри сервисов и роутеров
"""


from typing import Optional
from sqlalchemy.orm import Session

from app.db.models import User, Deputy
from app.core.roles import Role


# ========================
# ПРОСМОТР ОБРАЩЕНИЙ
# ========================


def can_view_request(
    user: User,
    owner_id: int,
    district_id: Optional[int],
    db: Optional[Session],
) -> bool:
    """
    Кто может смотреть обращение

    Правила:
    - SUPERUSER → всё
    - ADMIN → всё (только просмотр)
    - CITIZEN → только свои
    - DEPUTY → только свой район
    """

    # суперюзер видит всё
    if user.role == Role.SUPERUSER:
        return True

    # 🛠 админ видит всё (но не обязательно может редактировать)
    if user.role == Role.ADMIN:
        return True

    # 👤 гражданин — только свои обращения
    if user.role == Role.CITIZEN:
        return user.id == owner_id

    # 🏛 депутат — только свой район
    if user.role == Role.DEPUTY:
        if not db or not district_id:
            return False

        deputy = db.query(Deputy).filter(Deputy.user_id == user.id).first()
        return deputy is not None and deputy.district_id == district_id

    return False


# ========================
# ВЗАИМОДЕЙСТВИЕ С ОБРАЩЕНИЕМ
# ========================


def can_interact_with_request(
    user: User,
    owner_id: int,
    district_id: Optional[int],
    db: Session,
) -> bool:
    """
    Кто может:
    - писать сообщения
    - менять статус

    Правила:
    - SUPERUSER → всё
    - CITIZEN → только свои обращения
    - DEPUTY → только свой район
    - ADMIN → НЕ участвует
    """

    # суперюзер может всё
    if user.role == Role.SUPERUSER:
        return True

    # гражданин — только свои обращения
    if user.role == Role.CITIZEN:
        return user.id == owner_id

    # депутат — только свой район
    if user.role == Role.DEPUTY:
        deputy = db.query(Deputy).filter(Deputy.user_id == user.id).first()
        return deputy is not None and deputy.district_id == district_id

    # админ НЕ участвует в обработке
    return False


# ========================
# УДАЛЕНИЕ ОБРАЩЕНИЙ
# ========================


def can_delete_request(user: User) -> bool:
    """
    Кто может удалять обращения

    Правила:
    - ADMIN
    - SUPERUSER
    """
    return user.role in [Role.ADMIN, Role.SUPERUSER]


# ========================
# НАЗНАЧЕНИЕ ДЕПУТАТА
# ========================


def can_assign_deputy(user: User) -> bool:
    """
    Кто может назначать депутата

    Правила:
    - ADMIN
    - SUPERUSER
    """
    return user.role in [Role.ADMIN, Role.SUPERUSER]
