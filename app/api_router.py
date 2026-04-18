from fastapi import APIRouter
from app.api.v1.endpoints import (
    users,
    auth,
    category,
    request_status,
    role_request,
    requests, districts
    )

from app.api.v1.endpoints import districts



api_router = APIRouter()

api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])

#блок 2
api_router.include_router(requests.router, prefix="/requests", tags=["Requests"])

# блок 3
api_router.include_router(districts.router, prefix="/districts", tags=["Districts"])

# блок 4 — категории, статусы, заявки на роль
api_router.include_router(category.router, prefix="/categories", tags=["Categories"])
api_router.include_router(request_status.router, prefix="/statuses", tags=["Statuses"])
api_router.include_router(role_request.router, prefix="/role-requests", tags=["Role Requests"])