#!/usr/bin/env python
"""Pre-download AI model weights to ./data/models (optional, done automatically otherwise).

Usage:  python scripts/download_models.py
"""
import os

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "models")
os.makedirs(MODEL_DIR, exist_ok=True)
os.environ["MODEL_DIR"] = os.path.abspath(MODEL_DIR)


def download_clip():
    print(">>> OpenCLIP ViT-B-32 (laion2b) weights")
    print("    will be fetched automatically on first ai-engine container start (~340MB).")


def download_yolo():
    print(">>> Downloading YOLOv8m weights...")
    from ultralytics import YOLO
    model = YOLO("yolov8m.pt")  # downloads ~50MB
    print(f"YOLOv8m ready at: {model.ckpt_path if hasattr(model, 'ckpt_path') else model}")


def download_insightface():
    print(">>> InsightFace buffalo_l will download on first face use.")


if __name__ == "__main__":
    download_yolo()
    download_clip()
    download_insightface()
    print("Done. Models stored under", MODEL_DIR)
