from jose import jwt, JWTError
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from app.core.config import SECRET_KEY, ALGORITHM
from app.db.database import get_db
from app.crud.user import get_user_by_id
from app.db.models import User
from app.core.roles import Role

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    # 1. Достаём сам токен из заголовка
    token = credentials.credentials

    try:
        # 2. Раскодируем JWT (проверяем подпись + срок жизни)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # 3. Достаём user_id из токена
        user_id = int(payload.get("sub"))

        # если внутри токена нет id — токен неправильный
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

    except (JWTError, ValueError, TypeError):
        # если токен подделан / истёк / неправильный
        raise HTTPException(status_code=401, detail="Invalid token")

    # 4. Идём в базу и получаем пользователя
    user = get_user_by_id(db, user_id)

    # если пользователя нет в БД — доступ запрещён
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # 5. Приводим роль к Enum (ЕДИНОЖДЫ)
    try:
        user.role = Role(user.role)
    except ValueError:
        raise HTTPException(status_code=500, detail="Некорректная роль пользователя")

    # 6. Возвращаем пользователя
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)):
    """
    Получить текущего активного пользователя

    В будущем можно добавить проверку:
    - if not current_user.is_active:
    -     raise HTTPException(status_code=403, detail="User is inactive")
    """
    return current_user


async def get_optional_user_from_token(request: Request) -> Optional[dict]:
    """
    Получить текущего пользователя из токена в cookies для шаблонов.

    Эта функция пытается извлечь пользователя из cookies с токеном.
    Если пользователь не авторизован или токен невалиден, возвращает None.

    Возвращает словарь с данными пользователя или None.
    """
    try:
        db = next(get_db())

        token = request.cookies.get('access_token')

        if not token:
            return None

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = int(payload.get("sub"))

            if user_id is None:
                return None

            user = get_user_by_id(db, user_id)

            if not user:
                return None

            return {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role.value if hasattr(user.role, 'value') else str(user.role),
                'is_active': user.is_active,
            }

        except (JWTError, ValueError, TypeError):
            return None

    except Exception:
        return None
    finally:
        try:
            db.close()
        except:
            pass