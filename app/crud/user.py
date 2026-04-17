from sqlalchemy.orm import Session
from app.db import models


def create_user(db: Session, user_data):
    user = models.User(
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        email=user_data.email,
        password_hash=user_data.password,  # пока без хеша
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user
