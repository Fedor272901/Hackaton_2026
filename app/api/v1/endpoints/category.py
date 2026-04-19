<<<<<<< HEAD
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryRead
from app.crud import category as crud
=======
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryRead
from app.services import CategoryService
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)

router = APIRouter()


<<<<<<< HEAD
# зависимость для БД — такой же стиль, как в users.py у команды
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=list[CategoryRead])
def get_categories(db: Session = Depends(get_db)):
    """Получить список всех категорий. Доступно всем."""
    return crud.get_categories(db)


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(category_id: int, db: Session = Depends(get_db)):
    """Получить категорию по id."""
    category = crud.get_category(db, category_id)
=======
# ========================
# Dependency Injection for Services
# ========================

async def get_category_service(session: AsyncSession = Depends(get_db)) -> CategoryService:
    """
    Get CategoryService instance with database session.
    
    This dependency is used to inject the service into endpoint handlers.
    The service manages its own transactions for write operations.
    
    Args:
        session: Database session from get_db dependency
    
    Returns:
        CategoryService instance initialized with the session
    """
    return CategoryService(session)


# ========================
# PUBLIC ENDPOINTS (доступны всем авторизованным)
# ========================

@router.get("/", response_model=list[CategoryRead])
async def get_categories(
    service: CategoryService = Depends(get_category_service),
):
    """Получить список всех категорий. Доступно всем."""
    return await service.get_categories()


@router.get("/{category_id}", response_model=CategoryRead)
async def get_category(
    category_id: int,
    service: CategoryService = Depends(get_category_service),
):
    """Получить категорию по id."""
    category = await service.get_category(category_id)
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    if category is None:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    return category


@router.post("/", response_model=CategoryRead, status_code=201)
<<<<<<< HEAD
def create_category(data: CategoryCreate, db: Session = Depends(get_db)):
    """Создать новую категорию. В финале — только для админа."""
    category = crud.create_category(db, data)
    return category


@router.patch("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: Session = Depends(get_db),
):
    """Обновить категорию. В финале — только для админа."""
    category = crud.update_category(db, category_id, data)
=======
async def create_category(
    data: CategoryCreate,
    service: CategoryService = Depends(get_category_service),
):
    """Создать новую категорию. В финале — только для админа."""
    return await service.create_category(data)


@router.patch("/{category_id}", response_model=CategoryRead)
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    service: CategoryService = Depends(get_category_service),
):
    """Обновить категорию. В финале — только для админа."""
    category = await service.update_category(category_id, data)
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
    if category is None:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    return category


@router.delete("/{category_id}", status_code=204)
<<<<<<< HEAD
def delete_category(category_id: int, db: Session = Depends(get_db)):
    """Удалить категорию. В финале — только для админа."""
    ok = crud.delete_category(db, category_id)
    if not ok:
=======
async def delete_category(
    category_id: int,
    service: CategoryService = Depends(get_category_service),
):
    """Удалить категорию. В финале — только для админа."""
    success = await service.delete_category(category_id)
    if not success:
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
        raise HTTPException(status_code=404, detail="Категория не найдена")
