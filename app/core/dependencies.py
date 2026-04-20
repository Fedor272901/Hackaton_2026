from jose import jwt, JWTError
<<<<<<< HEAD
=======
<<<<<<< HEAD
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

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
=======
>>>>>>> front/dev
from fastapi import Depends, HTTPException, Request, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.core.config import settings
from app.db.database import get_db
from app.db.models import User
from app.core.roles import Role

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.user_service import UserService

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить текущего авторизованного пользователя из JWT токена.
    
    Требует заголовок Authorization: Bearer <token>
    """
<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
    # 1. Достаём сам токен из заголовка
    token = credentials.credentials

    try:
        # 2. Раскодируем JWT (проверяем подпись + срок жизни)
<<<<<<< HEAD
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
=======
<<<<<<< HEAD
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
=======
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev

        # 3. Достаём user_id из токена
        user_id = int(payload.get("sub"))

        # если внутри токена нет id — токен неправильный
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

    except (JWTError, ValueError, TypeError):
        # если токен подделан / истёк / неправильный
        raise HTTPException(status_code=401, detail="Invalid token")

    # 4. Идём в базу и получаем пользователя
<<<<<<< HEAD
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
=======
<<<<<<< HEAD
    user = get_user_by_id(db, user_id)
=======
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev

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


<<<<<<< HEAD
=======
<<<<<<< HEAD
def get_current_active_user(current_user: User = Depends(get_current_user)):
    """
    Получить текущего активного пользователя

=======
>>>>>>> front/dev
async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Получить текущего пользователя, если он авторизован.
    
    Если токен отсутствует или невалиден — возвращает None.
    Используется в endpoints, где авторизация не обязательна.
    """
    try:
        # Пробуем получить токен из заголовка Authorization
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            # Пробуем получить токен из cookies
            token = request.cookies.get(settings.JWT_COOKIE_NAME)
            if not token:
                return None
        else:
            token = auth_header.split(" ", 1)[1]

        # Раскодируем JWT
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = int(payload.get("sub"))
        
        if user_id is None:
            return None

        # Получаем пользователя из БД
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if user:
            try:
                user.role = Role(user.role)
            except ValueError:
                return None
        
        return user

    except (JWTError, ValueError, TypeError, KeyError):
        # Любая ошибка означает "пользователь не авторизован"
        return None


def get_current_active_user(current_user: User = Depends(get_current_user)):
    """
    Получить текущего активного пользователя.
    
<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
    В будущем можно добавить проверку:
    - if not current_user.is_active:
    -     raise HTTPException(status_code=403, detail="User is inactive")
    """
    return current_user
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
>>>>>>> front/dev


async def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    """Factory dependency for UserService with AsyncSession injection."""
    return UserService(db)


# app/core/dependencies.py
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.crud.user import get_user_by_id  # или ваш async CRUD
from app.schemas.user import UserRead

security = HTTPBearer(auto_error=False)  # ← Важно: auto_error=False для опционального токена

async def get_optional_user_from_token(
    request: Request,
    db: AsyncSession = None,  # передаётся явно, если нужно
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserRead | None:
    """
    Опциональная зависимость: возвращает пользователя, если токен валиден,
    или None, если токена нет или он невалиден.
    Не выбрасывает исключение при отсутствии токена.
    """
    if not credentials:
        return None
    
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        
        # Если db передан — загрузить пользователя из БД
        if db:
            user = await get_user_by_id(db, int(user_id))
            return UserRead.model_validate(user) if user else None
        return UserRead(id=int(user_id), **payload)  # fallback без БД
        
    except (JWTError, ValueError, KeyError):
<<<<<<< HEAD
        return None  # Токен невалиден — возвращаем None, а не ошибку
=======
        return None  # Токен невалиден — возвращаем None, а не ошибку
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
