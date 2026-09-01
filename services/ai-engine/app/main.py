import os
import threading

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .clip_engine import ClipEngine
from .face_engine import FaceEngine
from .yolo_engine import YoloEngine
from .utils.image_ops import load_image

app = FastAPI(title="ACUSEEK AI Engine", version="1.0.0")


class EmbedImageIn(BaseModel):
    image_url: str


class EmbedTextIn(BaseModel):
    text: str


class DetectIn(BaseModel):
    image_url: str


MODEL_DIR = os.environ.get("MODEL_DIR", "/models")


def load_models_background():
    """Preload all models on startup (takes time — do in background thread)."""
    def _load():
        try:
            ClipEngine.ensure_loaded()
            print("[AI] OpenCLIP loaded")
        except Exception as exc:
            print(f"[AI] OpenCLIP load failed: {exc}")
        try:
            FaceEngine.ensure_loaded()
            print("[AI] InsightFace loaded")
        except Exception as exc:
            print(f"[AI] InsightFace load failed: {exc}")
        try:
            YoloEngine.ensure_loaded()
            print("[AI] YOLOv8 loaded")
        except Exception as exc:
            print(f"[AI] YOLOv8 load failed: {exc}")

    threading.Thread(target=_load, daemon=True).start()


@app.on_event("startup")
async def startup():
    load_models_background()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/embed/text")
async def embed_text(payload: EmbedTextIn):
    try:
        embedding = ClipEngine.embed_text(payload.text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"CLIP error: {exc}")
    return {"embedding": embedding, "dim": len(embedding)}


@app.post("/embed/image")
async def embed_image(payload: EmbedImageIn):
    try:
        img = await load_image(payload.image_url)
        embedding = ClipEngine.embed_image(img)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"CLIP error: {exc}")
    return {"embedding": embedding, "dim": len(embedding)}


@app.post("/face/embed")
async def face_embed(payload: EmbedImageIn):
    try:
        img = await load_image(payload.image_url)
        embedding = FaceEngine.embed_face(img)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Face error: {exc}")
    if embedding is None:
        return {"embedding": None, "found": False}
    return {"embedding": embedding, "found": True, "dim": len(embedding)}


@app.post("/detect")
async def detect(payload: DetectIn):
    try:
        img = await load_image(payload.image_url)
        detections = YoloEngine.detect(img)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"YOLO error: {exc}")
    return {"detections": detections}
