<<<<<<< HEAD
from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from typing import Annotated
=======
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
import traceback
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)

from app.db.database import get_db
from app.schemas.user import UserCreate, UserRead, UserLogin
from app.schemas.token import Token
<<<<<<< HEAD
from app.crud.user import create_user, get_user_by_email
from app.core.security import verify_password, create_access_token

router = APIRouter()


def user_create_form(
=======
from app.services.user_service import UserService
from app.core.security import verify_password, create_access_token
from app.core.dependencies import get_current_user, get_user_service

router = APIRouter()

# 🔹 РЕГИСТРАЦИЯ (HTML Form)
@router.post("/register", response_model=UserRead)
async def register(
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    first_name: Annotated[str, Form(...)],
    last_name: Annotated[str, Form(...)],
    email: Annotated[str, Form(...)],
    password: Annotated[str, Form(...)],
<<<<<<< HEAD
) -> UserCreate:
    return UserCreate(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=password,
    )


@router.post("/register", response_model=UserRead)
def register(
    user: UserCreate,
    db: Session = Depends(get_db),
):
    new_user = create_user(db, user)

    if not new_user:
        raise HTTPException(status_code=400, detail="Email already exists")

    return new_user


@router.post("/login", response_model=Token)
def login(
    user_data: UserLogin,
    db: Session = Depends(get_db),
):
    # 1. ищем пользователя
    user = get_user_by_email(db, user_data.email)

    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    # 2. проверяем пароль
    if not verify_password(user_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    # 3. создаем токен
    access_token = create_access_token(
        data={
            "sub": user.id,  # кто пользователь
            "role": user.role,  # какая у него роль
        }
    )

    # 3. возвращаем пользователя
    return {"access_token": access_token, "token_type": "bearer"}
=======
    service: UserService = Depends(get_user_service),
) -> UserRead:
    """Register a new user via HTML form."""
    try:
        user_in = UserCreate(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=password,
        )
        new_user = await service.create_user(user_in)
        return new_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # 🔍 Выводит реальный стек ошибки в консоль сервера (убрать в продакшене)
        print(f"❌ Registration failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")

# 🔹 ВХОД (HTML Form)
@router.post("/login", response_model=Token)
async def login(
    email: Annotated[str, Form(...)],
    password: Annotated[str, Form(...)],
    db: AsyncSession = Depends(get_db),
    service: UserService = Depends(get_user_service),
) -> Token:
    """Authenticate user via HTML form and return JWT."""
    try:
        user = await service.get_user_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=400, detail="Invalid email or password")

        # Безопасное получение роли (учитываем, что relationship может быть None)
        role_name = getattr(user.role, "name", None) or "user"

        access_token = create_access_token(
            data={"sub": str(user.id), "role": role_name}
        )
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Login failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")

# 🔹 ПОЛУЧЕНИЕ ТЕКУЩЕГО ПОЛЬЗОВАТЕЛЯ (JSON API)
@router.get("/me", response_model=UserRead)
async def get_current_user_info(
    current_user: Annotated[UserRead, Depends(get_current_user)],
) -> UserRead:
    return current_user
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
