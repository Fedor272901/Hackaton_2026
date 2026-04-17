from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.user import UserCreate
from app.crud.user import create_user, get_user_by_email
from app.db.database import SessionLocal, get_db
from app.core.dependencies import get_current_user

router = APIRouter()


@router.post("/")
def create_user_endpoint(user: UserCreate, db: Session = Depends(get_db)):

    existing_user = get_user_by_email(db, user.email)

    if existing_user:
        raise HTTPException(
            status_code=400, detail="User with this email already exists"
        )

    return create_user(db, user)


@router.get("/me")
def get_me(current_user=Depends(get_current_user)):

    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
    }
