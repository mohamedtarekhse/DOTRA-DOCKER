from typing import Optional

from pydantic import BaseModel


class SearchQuery(BaseModel):
    query: str
    limit: int = 20
    camera_id: Optional[str] = None
    from_time: Optional[str] = None
    to_time: Optional[str] = None


class SearchResult(BaseModel):
    image_id: str
    image_url: str
    captured_at: str
    camera_name: Optional[str] = None
    score: float
