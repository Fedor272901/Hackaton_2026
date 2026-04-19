from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.request_status import StatusCreate, StatusUpdate, StatusRead
from app.services import RequestStatusService

router = APIRouter()


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
    if status is None:
        raise HTTPException(status_code=404, detail="Статус не найден")
    return status


@router.post("/", response_model=StatusRead, status_code=201)
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
    if status is None:
        raise HTTPException(status_code=404, detail="Статус не найден")
    return status


@router.delete("/{status_id}", status_code=204)
async def delete_status(
    status_id: int,
    service: RequestStatusService = Depends(get_request_status_service),
):
    """Удалить статус. В финале — только для админа."""
    success = await service.delete_status(status_id)
    if not success:
        raise HTTPException(status_code=404, detail="Статус не найден")
