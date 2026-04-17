"""
Модуль для проверки прав доступа и ролей пользователей

Использование:
    from app.core.permissions import require_role, require_admin, require_deputy
    
    @router.post("/admin-only")
    def admin_endpoint(
        current_user: User = Depends(require_admin)
    ):
        return {"message": "Только админ видит это"}
"""
from functools import wraps
from typing import List, Optional, Callable
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User, Deputy
from app.core.dependencies import get_current_active_user


def require_role(allowed_roles: List[str]):
    """
    Фабрика зависимостей для проверки роли пользователя
    
    Args:
        allowed_roles: список разрешенных ролей (например, ["admin", "deputy"])
    
    Returns:
        Функция-зависимость для FastAPI
    
    Пример:
        @router.post("/protected")
        def protected_endpoint(
            current_user: User = Depends(require_role(["admin", "moderator"]))
        ):
            return {"message": f"Привет, {current_user.role}"}
    """
    def role_checker(current_user: User = Depends(get_current_active_user)):
        if current_user.role not in allowed_roles:
            roles_text = ", ".join(allowed_roles)
            raise HTTPException(
                status_code=403,
                detail=f"Доступ запрещен. Требуется одна из ролей: {roles_text}"
            )
        return current_user
    return role_checker


# Предопределенные проверки для удобства
require_admin = require_role(["admin"])
require_deputy = require_role(["deputy"])
require_admin_or_deputy = require_role(["admin", "deputy"])


def require_ownership_or_admin(
    resource_owner_id: int,
    error_message: str = "У вас нет прав для выполнения этого действия"
):
    """
    Проверка: пользователь является владельцем ресурса ИЛИ администратором
    
    Args:
        resource_owner_id: ID владельца ресурса
        error_message: сообщение при ошибке
    
    Пример:
        @router.delete("/requests/{request_id}")
        def delete_request(
            request_id: int,
            current_user: User = Depends(get_current_active_user),
            db: Session = Depends(get_db)
        ):
            request = get_request(db, request_id)
            
            # Проверяем права
            _ = require_ownership_or_admin(
                request.user_id,
                "Вы не можете удалить чужое обращение"
            )(current_user)
            
            # Удаляем...
    """
    def ownership_checker(current_user: User = Depends(get_current_active_user)):
        if current_user.role != "admin" and current_user.id != resource_owner_id:
            raise HTTPException(status_code=403, detail=error_message)
        return current_user
    return ownership_checker


def require_deputy_with_district(allowed_district_id: Optional[int] = None):
    """
    Проверка: пользователь - депутат И (опционально) привязан к определенному району
    
    Args:
        allowed_district_id: ID разрешенного района (если None - любой район)
    
    Returns:
        Объект Deputy
    
    Пример:
        @router.post("/requests/{request_id}/process")
        def process_request(
            request_id: int,
            deputy: Deputy = Depends(require_deputy_with_district()),
            db: Session = Depends(get_db)
        ):
            # deputy - объект модели Deputy
            return {"deputy_district": deputy.district_id}
    """
    def deputy_checker(
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ):
        # Проверяем роль
        if current_user.role != "deputy":
            raise HTTPException(
                status_code=403,
                detail="Требуется роль депутата"
            )
        
        # Получаем запись депутата
        deputy = db.query(Deputy).filter(Deputy.user_id == current_user.id).first()
        
        if not deputy:
            raise HTTPException(
                status_code=403,
                detail="Депутат не привязан ни к одному району"
            )
        
        # Проверяем район, если указан
        if allowed_district_id is not None and deputy.district_id != allowed_district_id:
            raise HTTPException(
                status_code=403,
                detail=f"Это действие разрешено только для депутатов района #{allowed_district_id}"
            )
        
        return deputy
    return deputy_checker


def check_resource_access(
    user: User,
    resource_owner_id: int,
    resource_district_id: Optional[int] = None,
    db: Optional[Session] = None
) -> bool:
    """
    Проверка доступа к ресурсу (синхронная функция, не зависимость)
    
    Правила:
    - Админ: доступ ко всему
    - Гражданин: только к своим ресурсам
    - Депутат: к ресурсам своего района
    
    Args:
        user: пользователь
        resource_owner_id: ID владельца ресурса
        resource_district_id: ID района ресурса (для депутатов)
        db: сессия БД (обязательно для депутатов)
    
    Returns:
        True если доступ разрешен
    
    Пример:
        if not check_resource_access(current_user, request.user_id, request.district_id, db):
            raise HTTPException(403, "Доступ запрещен")
    """
    # Админ может всё
    if user.role == "admin":
        return True
    
    # Гражданин - только своё
    if user.role == "citizen":
        return user.id == resource_owner_id
    
    # Депутат - свой район
    if user.role == "deputy":
        if resource_district_id is None:
            return False
        
        if db is None:
            raise ValueError("Для проверки доступа депутата требуется сессия БД")
        
        deputy = db.query(Deputy).filter(Deputy.user_id == user.id).first()
        return deputy is not None and deputy.district_id == resource_district_id
    
    return False


# ==================== ДЕКОРАТОРЫ (альтернативный подход) ====================
def roles_required(allowed_roles: List[str]):
    """
    Декоратор для проверки ролей (альтернатива Depends)
    
    ВНИМАНИЕ: В FastAPI рекомендуется использовать Depends вместо декораторов!
    Декораторы хуже интегрируются с OpenAPI и автодокументацией.
    
    Пример:
        @router.post("/legacy-endpoint")
        @roles_required(["admin"])
        def legacy_endpoint(current_user: User = Depends(get_current_active_user)):
            return {"message": "Старый подход"}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Ищем current_user в аргументах
            current_user = kwargs.get('current_user')
            if not current_user:
                # Пробуем найти в позиционных аргументах
                for arg in args:
                    if isinstance(arg, User):
                        current_user = arg
                        break
            
            if not current_user:
                raise HTTPException(500, "Не удалось найти пользователя в аргументах")
            
            if current_user.role not in allowed_roles:
                raise HTTPException(
                    403,
                    f"Требуется роль: {', '.join(allowed_roles)}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator