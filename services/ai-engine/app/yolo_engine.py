import os

import numpy as np

MODEL_DIR = os.environ.get("MODEL_DIR", "/models")


class YoloEngine:
    """YOLOv8m person/vehicle detection for restricted zone breaches."""

    _model = None

    @classmethod
    def ensure_loaded(cls):
        if cls._model is not None:
            return cls._model
        from ultralytics import YOLO
        # Use GPU if available
        cls._model = YOLO(os.path.join(MODEL_DIR, "yolov8m.pt"))
        return cls._model

    @classmethod
    def detect(cls, image: np.ndarray) -> list[dict]:
        model = cls.ensure_loaded()
        results = model.predict(image, verbose=False)[0]
        detections = []
        for box in results.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            label = results.names[cls_id]
            detections.append(
                {
                    "label": label,
                    "confidence": round(conf, 4),
                    "bbox": [float(x) for x in box.xyxy[0].tolist()],
                }
            )
        return detections
