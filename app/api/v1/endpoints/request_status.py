from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.schemas.request_status import StatusCreate, StatusUpdate, StatusRead
from app.crud import request_status as crud

router = APIRouter()


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
    if status is None:
        raise HTTPException(status_code=404, detail="Статус не найден")
    return status


@router.post("/", response_model=StatusRead, status_code=201)
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
    if status is None:
        raise HTTPException(status_code=404, detail="Статус не найден")
    return status


@router.delete("/{status_id}", status_code=204)
def delete_status(status_id: int, db: Session = Depends(get_db)):
    """Удалить статус. В финале — только для админа."""
    ok = crud.delete_status(db, status_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Статус не найден")
