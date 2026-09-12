from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from typing import Annotated

from app.db.database import get_db
from app.schemas.user import UserCreate, UserRead, UserLogin
from app.schemas.token import Token
from app.crud.user import create_user, get_user_by_email
from app.core.security import verify_password, create_access_token

router = APIRouter()


def user_create_form(
    first_name: Annotated[str, Form(...)],
    last_name: Annotated[str, Form(...)],
    email: Annotated[str, Form(...)],
    password: Annotated[str, Form(...)],
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
