import os

import cv2
import httpx
import numpy as np


async def load_image(image_url: str) -> np.ndarray:
    """Load an image from a URL (MinIO public) or a local filesystem path."""
    if os.path.exists(image_url):
        img = cv2.imread(image_url, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image file: " + image_url)
        return img
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(image_url)
        resp.raise_for_status()
    data = np.frombuffer(resp.content, np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image")
    return img
