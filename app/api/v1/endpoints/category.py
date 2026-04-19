from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryRead
from app.services import CategoryService

router = APIRouter()


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
    if category is None:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    return category


@router.post("/", response_model=CategoryRead, status_code=201)
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
    if category is None:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    return category


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: int,
    service: CategoryService = Depends(get_category_service),
):
    """Удалить категорию. В финале — только для админа."""
    success = await service.delete_category(category_id)
    if not success:
        raise HTTPException(status_code=404, detail="Категория не найдена")
