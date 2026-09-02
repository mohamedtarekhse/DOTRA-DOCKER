from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..routers.auth import get_current_user
from ..services.search_service import search_service
from ..schemas.search import SearchResult

router = APIRouter(prefix="/search", tags=["search"], dependencies=[Depends(get_current_user)])


@router.get("/images", response_model=list[SearchResult])
async def text_search(
    q: str = Query(..., description="Natural language query e.g. 'red truck near gate 1'"),
    limit: int = Query(20, le=100),
    camera_id: str | None = None,
    from_time: str | None = None,
    to_time: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """AcuSeek-style text-to-image search over indexed surveillance snapshots."""
    return await search_service.text_search(
        db, q, limit, camera_id, from_time, to_time
    )
