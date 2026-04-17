from jose import jwt, JWTError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import SECRET_KEY, ALGORITHM
from app.db.database import get_db
from app.crud.user import get_user_by_id

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

    except JWTError:
        # если токен подделан / истёк / неправильный
        raise HTTPException(status_code=401, detail="Invalid token")

    # 4. Идём в базу и получаем пользователя
    user = get_user_by_id(db, user_id)

    # если пользователя нет в БД — доступ запрещён
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # 5. Возвращаем пользователя дальше в endpoint
    return user
