from fastapi import APIRouter, Depends, Form, HTTPException, Request
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
import traceback

from app.db.database import get_db
from app.schemas.user import UserCreate, UserRead, UserLogin
from app.schemas.token import Token
from app.services.user_service import UserService
from app.core.security import verify_password, create_access_token
from app.core.dependencies import get_current_user, get_user_service

router = APIRouter()

# 🔹 РЕГИСТРАЦИЯ (HTML Form)
@router.post("/register", response_model=UserRead)
async def register(
    first_name: Annotated[str, Form(...)],
    last_name: Annotated[str, Form(...)],
    email: Annotated[str, Form(...)],
    password: Annotated[str, Form(...)],
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