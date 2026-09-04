import ast

import httpx
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import ImageEmbedding, ImageStore, Camera


async def _embed_query(query: str) -> list[float]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{settings.AI_ENGINE_URL}/embed/text",
            json={"text": query},
        )
        resp.raise_for_status()
        return resp.json()["embedding"]


class SearchService:
    async def text_search(
        self, db: AsyncSession, query: str, limit: int = 20,
        camera_id: str | None = None, from_time: str | None = None, to_time: str | None = None,
    ) -> list[dict]:
        query_vec = await _embed_query(query)
        frags = []
        for v in query_vec:
            try:
                frags.append(f"{float(v):.6f}")
            except (TypeError, ValueError):
                continue
        if not frags:
            return []
        vec_str = "[" + ",".join(frags) + "]"

        sql = f"""
            SELECT ie.image_id, img_store.image_url, img_store.captured_at,
                   c.name as camera_name,
                   1 - (ie.clip_embedding <=> '{vec_str}'::vector) AS score
            FROM image_embeddings ie
            JOIN image_store img_store ON img_store.id = ie.image_id
            LEFT JOIN cameras c ON c.id = img_store.camera_id
            {self._conditions(camera_id, from_time, to_time)}
            ORDER BY ie.clip_embedding <=> '{vec_str}'::vector
            LIMIT :limit
        """
        cond_params = self._bind_params(camera_id, from_time, to_time)
        result = await db.execute(text(sql), {**cond_params, "limit": limit})
        rows = result.fetchall()
        return [
            {
                "image_id": str(r.image_id),
                "image_url": r.image_url,
                "captured_at": str(r.captured_at),
                "camera_name": r.camera_name,
                "score": round(float(r.score), 4),
            }
            for r in rows
        ]

    @staticmethod
    def _conditions(camera_id, from_time, to_time) -> str:
        conds = ["1=1"]
        if camera_id:
            conds.append("img_store.camera_id = :camera_id")
        if from_time:
            conds.append("img_store.captured_at >= :from_time")
        if to_time:
            conds.append("img_store.captured_at <= :to_time")
        return "WHERE " + " AND ".join(conds)

    @staticmethod
    def _bind_params(camera_id, from_time, to_time) -> dict:
        params = {}
        if camera_id:
            params["camera_id"] = camera_id
        if from_time:
            params["from_time"] = from_time
        if to_time:
            params["to_time"] = to_time
        return params


search_service = SearchService()
