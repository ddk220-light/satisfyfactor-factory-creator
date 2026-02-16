from fastapi import APIRouter
from backend.db import get_db, init_resource_nodes, get_resource_nodes

router = APIRouter(prefix="/api/map")


@router.get("/nodes")
def nodes():
    db = get_db()
    init_resource_nodes(db)
    return get_resource_nodes(db)
