from pydantic import BaseModel


class SearchResult(BaseModel):
    image_id: str
    image_url: str
    captured_at: str
    camera_name: Optional[str] = None
    score: float
