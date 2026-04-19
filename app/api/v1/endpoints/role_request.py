from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.role_request import (
    RoleRequestCreate,
    RoleRequestDecision,
    RoleRequestRead,
)
from app.services import UserService, DeputyService
from app.core.dependencies import get_current_active_user
from app.db.models import User

router = APIRouter()


async def get_user_service(session: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(session)


async def get_deputy_service(session: AsyncSession = Depends(get_db)) -> DeputyService:
    return DeputyService(session)


@router.post("/", response_model=RoleRequestRead, status_code=201)
async def submit_role_request(
    data: RoleRequestCreate,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
):
    result = await service.create_role_request(current_user.id, data)
    if result is None:
        raise HTTPException(status_code=409, detail="У вас уже есть заявка на рассмотрении")
    return result


@router.get("/", response_model=list[RoleRequestRead])
async def get_role_requests(
    status: str | None = None,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
):
    return await service.get_role_requests(status=status)


@router.get("/my", response_model=list[RoleRequestRead])
async def get_my_role_requests(
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
):
    return await service.get_role_requests_by_user(current_user.id)


@router.get("/{request_id}", response_model=RoleRequestRead)
async def get_role_request(
    request_id: int,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
):
    role_request = await service.get_role_request(request_id)
    if role_request is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return role_request


@router.post("/{request_id}/decision", response_model=RoleRequestRead)
async def decide_role_request(
    request_id: int,
    data: RoleRequestDecision,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user),
):
    result = await service.decide_role_request(request_id, data, current_user.id)
    if isinstance(result, dict) and "error" in result:
        error_msg = result["error"]
        if "не найден" in error_msg or "Заявка" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    return result["request"]
