from pydantic import BaseModel


class SearchResult(BaseModel):
    image_id: str
    image_url: str
    captured_at: str
    camera_name: str | None = None
    score: float
