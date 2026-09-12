from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.crud.request import get_requests
from app.crud.category import get_request_categories
from app.crud.status import get_request_statuses


router = APIRouter(prefix="/citizen", tags=["Citizen API"])


@router.get("/dashboard")
async def citizen_dashboard_api(db: Session = Depends(get_db)):
    """
    API для SSR страницы citizen dashboard
    Возвращает JSON, который потом вставляется в HTML
    """

    requests_data = get_requests(db, skip=0, limit=50)
    categories = get_request_categories(db)
    statuses = get_request_statuses(db)

    return {
        "requests": requests_data["items"],
        "total": requests_data["total"],
        "categories": categories,
        "statuses": statuses,
    }
