from fastapi import APIRouter

from app.util import generate_username

router = APIRouter(prefix="/api")


@router.get("/username")
async def get_username():
    return {"username": generate_username()}
