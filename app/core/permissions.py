"""
Модуль для проверки прав доступа и ролей пользователей

Здесь вся логика RBAC (roles & permissions)

Роли:
- CITIZEN  — обычный пользователь
- DEPUTY   — депутат (работает с районом)
- ADMIN    — администратор (управляет системой)
- SUPERUSER — разработчик (имеет полный доступ, только для тестов)

Использование:
    from app.core.permissions import require_role, require_admin, require_deputy

    @router.post("/admin-only")
    def admin_endpoint(
        current_user: User = Depends(require_admin)
    ):
        return {"message": "Только админ видит это"}
"""

# app/core/permissions.py
"""
Модуль для проверки прав доступа (интеграция с FastAPI)

❗ ВАЖНО:
- Используется ТОЛЬКО в Depends
- НЕ содержит бизнес-логики
- НЕ проверяет районы, ownership и т.д.

Разделение:
permissions.py → "кто пользователь?"
access.py      → "что ему можно делать?"
"""

from typing import List
from fastapi import HTTPException, Depends

from app.db.models import User
from app.core.dependencies import get_current_active_user
from app.core.roles import Role


# ========================
# БАЗОВАЯ ПРОВЕРКА РОЛИ
# ========================


def has_role(user: User, allowed_roles: list[Role]) -> bool:
    """
    Универсальная проверка ролей

    Правила:
    - SUPERUSER → всегда True
    - остальные → только если входят в allowed_roles
    """

    if user.role == Role.SUPERUSER:
        return True

    return user.role in allowed_roles


# ========================
# DEPENDS-ФАБРИКА
# ========================


def require_role(allowed_roles: List[Role]):
    """
    Фабрика зависимостей для FastAPI

    Используется в роутерах:
        current_user: User = Depends(require_role([...]))
    """

    def role_checker(current_user: User = Depends(get_current_active_user)):
        if not has_role(current_user, allowed_roles):
            roles_text = ", ".join([r.value for r in allowed_roles])

            raise HTTPException(
                status_code=403,
                detail=f"Доступ запрещен. Требуется роль: {roles_text}",
            )

        return current_user

    return role_checker


# ========================
# ГОТОВЫЕ ПРОВЕРКИ
# ========================

# Только админ
require_admin = require_role([Role.ADMIN])

# Только депутат
require_deputy = require_role([Role.DEPUTY])

# Админ ИЛИ депутат
require_admin_or_deputy = require_role([Role.ADMIN, Role.DEPUTY])


# ========================
# OWNERSHIP (ОПЦИОНАЛЬНО)
# ========================


def require_ownership_or_admin(
    resource_owner_id: int,
    error_message: str = "У вас нет прав для выполнения этого действия",
):
    """
    Проверка:
    - владелец ресурса
    - или ADMIN / SUPERUSER

    Используется, когда не хочется писать отдельную проверку в access.py
    """

    def checker(current_user: User = Depends(get_current_active_user)):
        if not (
            current_user.id == resource_owner_id
            or current_user.role in [Role.ADMIN, Role.SUPERUSER]
        ):
            raise HTTPException(status_code=403, detail=error_message)

        return current_user

    return checker


# ВРЕМЕННАЯ СОВМЕСТИМОСТЬ (чтобы не ломать старый код)
from app.core.access import can_view_request as check_resource_access
