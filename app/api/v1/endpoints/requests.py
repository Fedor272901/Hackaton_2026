# app/api/v1/endpoints/requests.py

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Path,
    File,
    UploadFile,
    Form,
)
from sqlalchemy.orm import Session
from typing import Optional, List
import os
import shutil
from datetime import datetime
import uuid

from app.core.config import SECRET_KEY, ALGORITHM
from geoalchemy2.shape import from_shape
from sqlalchemy import func
from sqlalchemy.orm import Session
from shapely.geometry import Point
from app.db.database import get_db
from app.db.models import User, Request, Deputy, District
from app.core.roles import Role
from app.schemas.requests import (
    RequestCreate,
    RequestUpdate,
    RequestResponse,
    RequestListResponse,
    RequestStatusResponse,
    RequestCategoryResponse,
    MessageCreate,
    MessageResponse,
    StatusHistoryResponse,
    StatisticsResponse,
)
from app.crud import request as request_crud
from app.core.dependencies import get_current_active_user
from app.core.permissions import require_admin, require_admin_or_deputy
from app.core.access import can_view_request
from app.core.rate_limit import rate_limiter
from app.core.spam_filter import spam_filter

router = APIRouter()


def get_request_or_404(db: Session, request_id: int) -> Request:
    request = request_crud.get_request_by_id(db, request_id)
    if not request:
        raise HTTPException(404, f"Обращение с ID {request_id} не найдено")
    return request


def save_upload_file(upload_file: UploadFile, user_id: int) -> str:
    """Сохраняет загруженный файл и возвращает путь к нему"""
    # Создаем директорию для загрузок, если её нет
    upload_dir = "uploads/requests"
    os.makedirs(upload_dir, exist_ok=True)

    # Генерируем уникальное имя файла
    file_ext = os.path.splitext(upload_file.filename)[1]
    unique_filename = (
        f"{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_ext}"
    )
    file_path = os.path.join(upload_dir, unique_filename)

    # Сохраняем файл
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)

    return f"/{file_path}"  # Возвращаем путь для доступа через веб


# ---------------------------
# Справочные эндпоинты (всем авторизованным)
# ---------------------------
@router.get("/statuses", response_model=List[RequestStatusResponse])
def get_statuses(db: Session = Depends(get_db)):
    """Получить список всех возможных статусов обращений"""
    return request_crud.get_request_statuses(db)


@router.get("/categories", response_model=List[RequestCategoryResponse])
def get_requests_categories(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Получить список всех категорий обращений"""
    return request_crud.get_request_categories(db)


@router.post("/", response_model=RequestResponse, status_code=201)
async def create_request(
    title: str = Form(...),
    description: str = Form(...),
    category_id: int = Form(...),
    address: str = Form(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    photos: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # Защиты (rate limit, спам, дубликаты)
    if not rate_limiter.check(current_user.id):
        raise HTTPException(429, "Лимит исчерпан: максимум 5 обращений в сутки")

    full_text = f"{title} {description}"
    is_spam, reason = spam_filter.check(full_text)
    if is_spam:
        raise HTTPException(400, f"Обращение отклонено: {reason}")

    if request_crud.check_duplicate_request(db, current_user.id, title):
        raise HTTPException(400, "Похожее обращение уже было отправлено недавно")

    # Проверка фото
    if len(photos) > 3:
        raise HTTPException(400, "Можно загрузить не более 3 фотографий")

    # Сохраняем фото
    photo_paths = []
    for photo in photos:
        if photo.size > 5 * 1024 * 1024:
            raise HTTPException(400, f"Файл {photo.filename} превышает 5 МБ")
        if photo.content_type not in [
            "image/jpeg",
            "image/png",
            "image/jpg",
            "image/webp",
        ]:
            raise HTTPException(400, f"Файл {photo.filename} должен быть изображением")
        file_path = save_upload_file(photo, current_user.id)
        photo_paths.append(file_path)

    # Определяем district_id
    district_id = None

    if latitude is not None and longitude is not None:
        try:
            point = from_shape(Point(longitude, latitude), srid=4326)
            district = (
                db.query(District)
                .filter(func.ST_Contains(District.geom, point))
                .first()
            )
            if district:
                district_id = district.id
        except Exception as e:
            print(f"Ошибка поиска района: {e}")

    # Если район не найден, берем первый существующий
    if district_id is None:
        first_district = db.query(District).first()
        if first_district:
            district_id = first_district.id

    # Создаем объект RequestCreate
    request_data = RequestCreate(
        title=title,
        description=description,
        category_id=category_id,
        address=address,
        district_id=district_id,
        latitude=latitude,
        longitude=longitude,
    )

    try:
        new_request = request_crud.create_request(db, request_data, current_user.id)
        return new_request
    except Exception as e:
        raise HTTPException(400, f"Ошибка при создании обращения: {str(e)}")


@router.get("/", response_model=RequestListResponse)
def get_requests_list(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    district_id: Optional[int] = None,
    category_id: Optional[int] = None,
    status_id: Optional[int] = None,
    my_requests: bool = False,
    include_closed: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Получить список обращений с фильтрацией и пагинацией"""

    # ФИЛЬТРАЦИЯ ПО РОЛИ
    if current_user.role == Role.CITIZEN:
        my_requests = True

    user_id = current_user.id if my_requests else None

    if current_user.role == Role.DEPUTY and not my_requests:
        deputy = db.query(Deputy).filter(Deputy.user_id == current_user.id).first()
        if deputy:
            district_id = deputy.district_id

    return request_crud.get_requests(
        db=db,
        skip=skip,
        limit=limit,
        user_id=user_id,
        district_id=district_id,
        category_id=category_id,
        status_id=status_id,
        include_closed=include_closed,
    )


@router.get("/my", response_model=List[RequestResponse])
def get_my_requests(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    include_closed: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Получить список обращений текущего пользователя"""
    result = request_crud.get_requests(
        db=db,
        skip=skip,
        limit=limit,
        user_id=current_user.id,
        include_closed=include_closed,
    )
    return result["items"]


@router.get("/{request_id}", response_model=RequestResponse)
def get_request_details(
    request_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Получить детальную информацию об обращении по ID"""
    request = get_request_or_404(db, request_id)

    if not can_view_request(current_user, request.user_id, request.district_id, db):
        raise HTTPException(403, "У вас нет прав для просмотра этого обращения")

    return request


@router.patch("/{request_id}", response_model=RequestResponse)
def update_request(
    request_id: int,
    request_update: RequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Обновить обращение"""
    request = get_request_or_404(db, request_id)

    if not can_view_request(current_user, request.user_id, request.district_id, db):
        raise HTTPException(403, "Нет прав на редактирование")

    try:
        return request_crud.update_request(
            db, request_id, request_update, current_user.id
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{request_id}/assign/{deputy_id}", response_model=RequestResponse)
def assign_deputy_to_request(
    request_id: int,
    deputy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Назначить депутата на обращение"""
    request = get_request_or_404(db, request_id)

    try:
        return request_crud.assign_deputy(db, request_id, deputy_id, current_user.id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/{request_id}", status_code=204)
def delete_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Удалить обращение"""
    if not request_crud.delete_request(db, request_id):
        raise HTTPException(404, f"Обращение с ID {request_id} не найдено")


# ---------------------------
# Сообщения к обращениям
# ---------------------------
@router.get("/{request_id}/messages", response_model=List[MessageResponse])
def get_request_messages(
    request_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Получить сообщения по обращению"""
    request = get_request_or_404(db, request_id)

    if not can_view_request(current_user, request.user_id, request.district_id, db):
        raise HTTPException(403, "У вас нет прав для просмотра сообщений")

    result = request_crud.get_request_messages(db, request_id, skip, limit)
    return result["items"]


@router.post("/{request_id}/messages", response_model=MessageResponse, status_code=201)
def add_message_to_request(
    request_id: int,
    message_data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Добавить сообщение к обращению"""
    request = get_request_or_404(db, request_id)

    if not can_view_request(current_user, request.user_id, request.district_id, db):
        raise HTTPException(403, "Вы не можете комментировать это обращение")

    return request_crud.add_message_to_request(
        db, request_id, current_user.id, message_data.text
    )


# ---------------------------
# История статусов
# ---------------------------
@router.get("/{request_id}/status-history", response_model=List[StatusHistoryResponse])
def get_request_status_history(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Получить историю изменения статусов обращения"""
    request = get_request_or_404(db, request_id)

    if not can_view_request(current_user, request.user_id, request.district_id, db):
        raise HTTPException(403, "У вас нет прав для просмотра истории")

    return request_crud.get_request_status_history(db, request_id)


# ---------------------------
# Статистика
# ---------------------------
@router.get("/statistics/summary", response_model=StatisticsResponse)
def get_requests_statistics(
    district_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_deputy),
):
    """Получить статистику по обращениям"""
    if current_user.role == Role.DEPUTY:
        deputy = db.query(Deputy).filter(Deputy.user_id == current_user.id).first()
        if not deputy:
            raise HTTPException(403, "Депутат не привязан ни к одному району")
        district_id = deputy.district_id

    return request_crud.get_statistics(db, district_id)
