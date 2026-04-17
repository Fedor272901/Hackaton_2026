from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def test_users():
    return {"message": "users endpoint works"}
