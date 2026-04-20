from fastapi import APIRouter, Depends, HTTPException
<<<<<<< HEAD
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
=======
<<<<<<< HEAD
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
=======
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
from app.schemas.role_request import (
    RoleRequestCreate,
    RoleRequestDecision,
    RoleRequestRead,
)
<<<<<<< HEAD
from app.services import UserService, DeputyService
from app.core.dependencies import get_current_active_user
from app.db.models import User
=======
<<<<<<< HEAD
from app.crud import role_request as crud
=======
from app.services import UserService, DeputyService
from app.core.dependencies import get_current_active_user
from app.db.models import User
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev

router = APIRouter()


<<<<<<< HEAD
=======
<<<<<<< HEAD
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=RoleRequestRead, status_code=201)
def submit_role_request(data: RoleRequestCreate, db: Session = Depends(get_db)):
    """
    Гражданин подаёт заявку на роль депутата.
    В финале user_id будет браться из JWT-токена автоматически.
    """

    """
    Что передавать в теле запроса (JSON):
    {
    "user_id": 5,
    "requested_role": "deputy",
    "user_comment": "Хочу помогать жителям округа решать проблемы с ЖКХ и дорогами"
    }
    Ошибки:
    - 409 — у этого пользователя уже есть заявка на рассмотрении (pending).
    Дождись решения по текущей заявке перед подачей новой.
    """
    result = crud.create_role_request(db, data)
    if result is None:
        raise HTTPException(
            status_code=409,
            detail="У вас уже есть заявка на рассмотрении",
        )
=======
>>>>>>> front/dev
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
<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
    return result


@router.get("/", response_model=list[RoleRequestRead])
<<<<<<< HEAD
=======
<<<<<<< HEAD
def get_role_requests(
    status: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Список заявок. Можно фильтровать по статусу:
    ?status=pending  ?status=approved  ?status=rejected
    В финале — только для админа.
    """
    return crud.get_role_requests(db, status=status)


@router.get("/user/{user_id}", response_model=list[RoleRequestRead])
def get_my_role_requests(user_id: int, db: Session = Depends(get_db)):
    """
    Заявки конкретного пользователя.
    В финале user_id будет браться из JWT-токена.
    """
    return crud.get_role_requests_by_user(db, user_id)


@router.get("/{request_id}", response_model=RoleRequestRead)
def get_role_request(request_id: int, db: Session = Depends(get_db)):
    """Получить заявку по id. В финале — только для админа."""
    role_request = crud.get_role_request(db, request_id)
=======
>>>>>>> front/dev
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
<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
    if role_request is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return role_request


@router.post("/{request_id}/decision", response_model=RoleRequestRead)
<<<<<<< HEAD
=======
<<<<<<< HEAD
def decide_role_request(
    request_id: int,
    data: RoleRequestDecision,
    db: Session = Depends(get_db),
):
    """
    Админ одобряет или отклоняет заявку.
    **Параметр пути:**
    - `request_id` — ID заявки по которой принимается решение

    **Что передавать в теле запроса (JSON):**

    Чтобы **одобрить** заявку:
    ```json
    {
    "admin_id": 1,
    "status": "approved",
    "admin_comment": "Заявка одобрена. Добро пожаловать в команду!"
    }
    ```
    Чтобы **отклонить** заявку:
    ```json
    {
    "admin_id": 1,
    "status": "rejected",
    "admin_comment": "Недостаточно информации. Подайте заявку повторно с подробным описанием."
    }
    ```
    **Поля:**
    - `admin_id` — ID администратора который принимает решение
    - `status` — решение: `"approved"` (одобрить) или `"rejected"` (отклонить)
    - `admin_comment` — комментарий для заявителя, необязательное поле
    При одобрении: роль пользователя → deputy, создаётся запись в deputies.
    В финале admin_id будет браться из JWT-токена.
    """

    result = crud.decide_role_request(db, request_id, data)

    # если crud вернул словарь с ошибкой — обрабатываем
    if isinstance(result, dict) and "error" in result:
        error_msg = result["error"]
        if "не найден" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)
        raise HTTPException(status_code=400, detail=error_msg)

    return result
=======
>>>>>>> front/dev
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
<<<<<<< HEAD
=======
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
>>>>>>> front/dev
