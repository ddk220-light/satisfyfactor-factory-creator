from fastapi import APIRouter
from backend.engine.theme_assigner import load_themes

router = APIRouter(prefix="/api")

@router.get("/themes")
def get_themes():
    return load_themes()
