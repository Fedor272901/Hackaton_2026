from fastapi import APIRouter
from app.api.v1.endpoints import (
    users,
    auth,
    category,
    request_status,
    role_request,
    requests,
    districts,
    deputies  # Новый роутер для депутатов
)



api_router = APIRouter()

api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])

# Блок 2: Обращения (Requests)
api_router.include_router(requests.router, prefix="/requests", tags=["Requests"])

# Блок 3: Округа (Districts) и Депутаты (Deputies)
api_router.include_router(districts.router, prefix="/districts", tags=["Districts"])
api_router.include_router(deputies.router, prefix="/deputies", tags=["Deputies"])

# Блок 4 — категории, статусы, заявки на роль
api_router.include_router(category.router, prefix="/categories", tags=["Categories"])
api_router.include_router(request_status.router, prefix="/statuses", tags=["Statuses"])
api_router.include_router(role_request.router, prefix="/role-requests", tags=["Role Requests"])