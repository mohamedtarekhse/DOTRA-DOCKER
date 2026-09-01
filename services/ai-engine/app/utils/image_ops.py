import os

import cv2
import httpx
import numpy as np


async def load_image(image_url: str) -> np.ndarray:
    """Load an image from a URL (MinIO public) into a BGR numpy array."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(image_url)
        resp.raise_for_status()
    data = np.frombuffer(resp.content, np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image")
    return img


def to_rgb(img_bgr: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
