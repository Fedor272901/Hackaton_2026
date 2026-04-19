<<<<<<< HEAD
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.schemas.request_status import StatusCreate, StatusUpdate, StatusRead
from app.crud import request_status as crud
=======
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.request_status import StatusCreate, StatusUpdate, StatusRead
from app.services import RequestStatusService
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)

router = APIRouter()


<<<<<<< HEAD
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=list[StatusRead])
def get_statuses(db: Session = Depends(get_db)):
    """Получить все статусы. Доступно всем."""
    return crud.get_statuses(db)


@router.get("/{status_id}", response_model=StatusRead)
def get_status(status_id: int, db: Session = Depends(get_db)):
    """Получить статус по id."""
    status = crud.get_status(db, status_id)
=======
# ========================
# Dependency Injection for Services
# ========================

async def get_request_status_service(session: AsyncSession = Depends(get_db)) -> RequestStatusService:
    """
    Get RequestStatusService instance with database session.
    
    This dependency is used to inject the service into endpoint handlers.
    The service manages its own transactions for write operations.
    
    Args:
        session: Database session from get_db dependency
    
    Returns:
        RequestStatusService instance initialized with the session
    """
    return RequestStatusService(session)


# ========================
# PUBLIC ENDPOINTS (доступны всем авторизованным)
# ========================

@router.get("/", response_model=list[StatusRead])
async def get_statuses(
    service: RequestStatusService = Depends(get_request_status_service),
):
    """Получить все статусы. Доступно всем."""
    return await service.get_statuses()


@router.get("/{status_id}", response_model=StatusRead)
async def get_status(
    status_id: int,
    service: RequestStatusService = Depends(get_request_status_service),
):
    """Получить статус по id."""
    status = await service.get_status(status_id)
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    if status is None:
        raise HTTPException(status_code=404, detail="Статус не найден")
    return status


@router.post("/", response_model=StatusRead, status_code=201)
<<<<<<< HEAD
def create_status(data: StatusCreate, db: Session = Depends(get_db)):
    """Создать статус. В финале — только для админа."""
    # Проверяем уникальность кода
    existing = crud.get_status_by_code(db, data.code)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Статус с кодом '{data.code}' уже существует",
        )
    return crud.create_status(db, data)


@router.patch("/{status_id}", response_model=StatusRead)
def update_status(
    status_id: int,
    data: StatusUpdate,
    db: Session = Depends(get_db),
):
    """Обновить статус. В финале — только для админа."""
    status = crud.update_status(db, status_id, data)
=======
async def create_status(
    data: StatusCreate,
    service: RequestStatusService = Depends(get_request_status_service),
):
    """Создать статус. В финале — только для админа."""
    try:
        return await service.create_status(data)
    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e),
        )


@router.patch("/{status_id}", response_model=StatusRead)
async def update_status(
    status_id: int,
    data: StatusUpdate,
    service: RequestStatusService = Depends(get_request_status_service),
):
    """Обновить статус. В финале — только для админа."""
    status = await service.update_status(status_id, data)
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    if status is None:
        raise HTTPException(status_code=404, detail="Статус не найден")
    return status


@router.delete("/{status_id}", status_code=204)
<<<<<<< HEAD
def delete_status(status_id: int, db: Session = Depends(get_db)):
    """Удалить статус. В финале — только для админа."""
    ok = crud.delete_status(db, status_id)
    if not ok:
=======
async def delete_status(
    status_id: int,
    service: RequestStatusService = Depends(get_request_status_service),
):
    """Удалить статус. В финале — только для админа."""
    success = await service.delete_status(status_id)
    if not success:
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
        raise HTTPException(status_code=404, detail="Статус не найден")
