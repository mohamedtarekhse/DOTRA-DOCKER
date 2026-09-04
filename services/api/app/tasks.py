"""Celery task dispatch helpers (safe when broker/worker is unavailable)."""

from .workers.indexer_tasks import index_image  # noqa: F401

def enqueue_index(image_url: str, camera_id: str | None = None, metadata: dict | None = None):
    """Fire-and-forget index task; never raises on broker errors."""
    try:
        index_image.apply_async(
            (image_url, camera_id, metadata),
            countdown=0,
            ignore_result=True,
        )
    except Exception:  # broker down / worker disabled — indexing is best-effort
        pass