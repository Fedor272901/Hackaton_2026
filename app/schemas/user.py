from pydantic import BaseModel, EmailStr
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from app.core.roles import Role
from datetime import datetime


class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str

class UserRead(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    role: str

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


# Новые схемы
class UserUpdate(BaseModel):
    """Обновление пользователя (админом)"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=100)
    role: Optional[Role] = None


class UserResponse(BaseModel):
    """Ответ с данными пользователя (без пароля)"""
    id: int
    first_name: str
    last_name: str
    email: str
    role: Role
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)



class UserListResponse(BaseModel):
    """Список пользователей с пагинацией"""
    items: list[UserResponse]
    total: int
    skip: int
    limit: int