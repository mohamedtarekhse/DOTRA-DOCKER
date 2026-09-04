import asyncio
import json

import httpx

from ..config import settings
from .celery_app import celery_app


@celery_app.task
def index_image(image_url: str, camera_id: str | None = None, metadata: dict | None = None):
    """Index a snapshot for AcuSeek text-to-image search."""
    async def _do():
        import asyncpg

        conn = await asyncpg.connect(settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"))

        # get CLIP embedding from AI engine
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.AI_ENGINE_URL}/embed/image",
                json={"image_url": image_url},
            )
            resp.raise_for_status()
            embedding = resp.json()["embedding"]

        # insert image_store + image_embeddings
        image_id = await conn.fetchval(
            "INSERT INTO image_store (camera_id, image_url, metadata) VALUES ($1, $2, $3::jsonb) RETURNING id",
            camera_id,
            image_url,
            json.dumps(metadata or {}),
        )
        emb_str = "[" + ",".join(str(f"{v:.6f}") for v in embedding) + "]"
        await conn.execute(
            "INSERT INTO image_embeddings (image_id, clip_embedding) VALUES ($1, $2::vector)",
            image_id,
            emb_str,
        )
        await conn.close()
        return str(image_id)

    return asyncio.run(_do())


@celery_app.task
def cleanup_old_data(days: int = 90):
    """Delete indexed images older than N days (retention)."""
    async def _do():
        import asyncpg
        conn = await asyncpg.connect(settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"))
        await conn.execute(
            "DELETE FROM image_store WHERE captured_at < NOW() - make_interval(days => $1)",
            days,
        )
        await conn.close()
        return "cleaned"

    return asyncio.run(_do())
