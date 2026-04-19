from fastapi import APIRouter
from app.api.v1.endpoints import (
    users,
    auth,
    category,
    request_status,
    role_request,
<<<<<<< HEAD
    requests, districts
    )

from app.api.v1.endpoints import districts
=======
    requests,
    districts,
    deputies  # Новый роутер для депутатов
)
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)



api_router = APIRouter()

api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])

<<<<<<< HEAD
#блок 2
api_router.include_router(requests.router, prefix="/requests", tags=["Requests"])

# блок 3
api_router.include_router(districts.router, prefix="/districts", tags=["Districts"])

# блок 4 — категории, статусы, заявки на роль
=======
# Блок 2: Обращения (Requests)
api_router.include_router(requests.router, prefix="/requests", tags=["Requests"])

# Блок 3: Округа (Districts) и Депутаты (Deputies)
api_router.include_router(districts.router, prefix="/districts", tags=["Districts"])
api_router.include_router(deputies.router, prefix="/deputies", tags=["Deputies"])

# Блок 4 — категории, статусы, заявки на роль
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
api_router.include_router(category.router, prefix="/categories", tags=["Categories"])
api_router.include_router(request_status.router, prefix="/statuses", tags=["Statuses"])
api_router.include_router(role_request.router, prefix="/role-requests", tags=["Role Requests"])