from fastapi import APIRouter, Depends, Form
from sqlalchemy.orm import Session
from typing import Annotated
from fastapi import HTTPException

from app.db.database import get_db
from app.schemas.user import UserCreate, UserRead
from app.crud.user import create_user

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
