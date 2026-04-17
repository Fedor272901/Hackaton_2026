from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryRead
from app.crud import category as crud

router = APIRouter()


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
    if category is None:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    return category


@router.post("/", response_model=CategoryRead, status_code=201)
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
    if category is None:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    return category


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    """Удалить категорию. В финале — только для админа."""
    ok = crud.delete_category(db, category_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Категория не найдена")
