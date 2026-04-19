from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


# ---------------------------
# Вспомогательные схемы для связанных объектов
# ---------------------------
class UserBriefResponse(BaseModel):
    """Краткая информация о пользователе для вложенных объектов"""
    id: int
    first_name: str
    last_name: str
    email: str
    role: str
    
    model_config = ConfigDict(from_attributes=True)


class DistrictBriefResponse(BaseModel):
    """Краткая информация о районе"""
    id: int
    name: str
    description: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class RequestCategoryResponse(BaseModel):
    """Категория обращения"""
    id: int
    name: str
    description: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class RequestStatusResponse(BaseModel):
    """Статус обращения"""
    id: int
    code: str
    name: str
    
    model_config = ConfigDict(from_attributes=True)


class DeputyBriefResponse(BaseModel):
    """Краткая информация о депутате"""
    id: int
    user: Optional[UserBriefResponse] = None
    appointed_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class RequestPhotoResponse(BaseModel):
    """Фотография обращения"""
    id: int
    file_url: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ---------------------------
# Схемы для создания и обновления обращений
# ---------------------------
class RequestCreate(BaseModel):
    """Схема для создания нового обращения"""
    title: str = Field(
        ..., 
        min_length=5, 
        max_length=200, 
        description="Заголовок обращения"
    )
    description: str = Field(
        ..., 
        min_length=20, 
        max_length=5000,
        description="Подробное описание проблемы"
    )
    district_id: int = Field(
        ..., 
        gt=0,
        description="ID района, к которому относится обращение"
    )
    category_id: int = Field(
        ..., 
        gt=0,
        description="ID категории обращения"
    )
    address: Optional[str] = Field(
        None, 
        max_length=500,
        description="Физический адрес (улица, дом)"
    )
    latitude: Optional[float] = Field(
        None, 
        ge=-90, 
        le=90, 
        description="Географическая широта"
    )
    longitude: Optional[float] = Field(
        None, 
        ge=-180, 
        le=180, 
        description="Географическая долгота"
    )
    photo_urls: Optional[List[str]] = Field(
        None, 
        description="Список URL загруженных фотографий"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Яма на дороге по улице Ленина",
                "description": "Глубокая яма на проезжей части, повреждено дорожное покрытие. "
                               "Создает аварийную ситуацию, водители вынуждены выезжать на встречную полосу.",
                "district_id": 1,
                "category_id": 3,
                "address": "ул. Ленина, д. 15",
                "latitude": 55.7558,
                "longitude": 37.6173,
                "photo_urls": [
                    "https://storage.example.com/photos/request_123_1.jpg",
                    "https://storage.example.com/photos/request_123_2.jpg"
                ]
            }
        }
    )


class RequestUpdate(BaseModel):
    """Схема для обновления существующего обращения"""
    title: Optional[str] = Field(
        None, 
        min_length=5, 
        max_length=200,
        description="Новый заголовок обращения"
    )
    description: Optional[str] = Field(
        None, 
        min_length=20,
        max_length=5000,
        description="Новое описание проблемы"
    )
    category_id: Optional[int] = Field(
        None, 
        gt=0,
        description="Новая категория обращения"
    )
    status_id: Optional[int] = Field(
        None, 
        gt=0,
        description="Новый статус обращения"
    )
    address: Optional[str] = Field(
        None, 
        max_length=500,
        description="Обновленный адрес"
    )
    latitude: Optional[float] = Field(
        None, 
        ge=-90, 
        le=90,
        description="Обновленная широта"
    )
    longitude: Optional[float] = Field(
        None, 
        ge=-180, 
        le=180,
        description="Обновленная долгота"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status_id": 2,
                "description": "Яма стала глубже, требуется срочный ремонт"
            }
        }
    )


# ---------------------------
# Схемы для ответов API
# ---------------------------
class RequestResponse(BaseModel):
    """Полная информация об обращении для ответа API"""
    id: int
    title: str
    description: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    
    # Связанные объекты
    user: Optional[UserBriefResponse] = None
    district: Optional[DistrictBriefResponse] = None
    category: Optional[RequestCategoryResponse] = None
    status: Optional[RequestStatusResponse] = None
    assigned_deputy: Optional[DeputyBriefResponse] = None
    photos: List[RequestPhotoResponse] = []
    
    model_config = ConfigDict(from_attributes=True)


class RequestListResponse(BaseModel):
    """Ответ со списком обращений и метаданными пагинации"""
    items: List[RequestResponse]
    total: int = Field(..., description="Общее количество обращений")
    skip: int = Field(..., description="Сколько записей пропущено")
    limit: int = Field(..., description="Максимальное количество записей на странице")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [],
                "total": 42,
                "skip": 0,
                "limit": 20
            }
        }
    )


# ---------------------------
# Схемы для сообщений
# ---------------------------
class MessageCreate(BaseModel):
    """Схема для создания нового сообщения"""
    text: str = Field(
        ..., 
        min_length=1, 
        max_length=2000,
        description="Текст сообщения"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "Когда планируется ремонт этого участка дороги?"
            }
        }
    )


class MessageResponse(BaseModel):
    """Ответ с информацией о сообщении"""
    id: int
    request_id: int
    user: Optional[UserBriefResponse] = None
    text: str
    is_system: bool = Field(False, description="Является ли сообщение системным")
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ---------------------------
# Схемы для истории статусов
# ---------------------------
class StatusHistoryResponse(BaseModel):
    """Запись в истории изменения статусов"""
    id: int
    request_id: int
    old_status: Optional[RequestStatusResponse] = None
    new_status: Optional[RequestStatusResponse] = None
    changed_by_user: Optional[UserBriefResponse] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ---------------------------
# Схемы для статистики
# ---------------------------
class StatusStats(BaseModel):
    """Статистика по одному статусу"""
    name: str
    count: int
    percentage: float


class CategoryStats(BaseModel):
    """Статистика по одной категории"""
    count: int
    percentage: float


class StatisticsResponse(BaseModel):
    """Статистика по обращениям"""
    total_requests: int = Field(..., description="Общее количество обращений")
    by_status: dict[str, StatusStats] = Field(
        ..., 
        description="Статистика по статусам (ключ - код статуса)"
    )
    by_category: dict[str, CategoryStats] = Field(
        ..., 
        description="Статистика по категориям (ключ - название категории)"
    )
    average_resolution_days: float = Field(
        ..., 
        description="Среднее время решения в днях"
    )
    district_id: Optional[int] = Field(
        None, 
        description="ID района, если статистика отфильтрована"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_requests": 156,
                "by_status": {
                    "new": {"name": "Новое", "count": 45, "percentage": 28.85},
                    "in_progress": {"name": "В работе", "count": 67, "percentage": 42.95},
                    "closed": {"name": "Закрыто", "count": 44, "percentage": 28.20}
                },
                "by_category": {
                    "Дороги": {"count": 78, "percentage": 50.0},
                    "ЖКХ": {"count": 45, "percentage": 28.85},
                    "Благоустройство": {"count": 33, "percentage": 21.15}
                },
                "average_resolution_days": 12.5,
                "district_id": None
            }
        }
    )


# ---------------------------
# Схема для ответа с ошибкой
# ---------------------------
class ErrorResponse(BaseModel):
    """Стандартный ответ с ошибкой"""
    detail: str = Field(..., description="Описание ошибки")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "Обращение с ID 123 не найдено"
            }
        }
    )