import os

import numpy as np

MODEL_DIR = os.environ.get("MODEL_DIR", "/models")
FACE_MODEL_PREFIX = "buffalo_l"


class FaceEngine:
    """InsightFace wrapper — face detection + 512-d embedding extraction."""

    _model = None

    @classmethod
    def ensure_loaded(cls):
        if cls._model is not None:
            return cls._model
        import insightface
        from insightface.app import FaceAnalysis
        app = FaceAnalysis(name=FACE_MODEL_PREFIX, root=MODEL_DIR, providers=cls._providers())
        app.prepare(ctx_id=0, det_size=(640, 640))
        cls._model = app
        return app

    @staticmethod
    def _providers():
        try:
            import onnxruntime as ort
            if "CUDAExecutionProvider" in ort.get_available_providers():
                return ["CUDAExecutionProvider", "CPUExecutionProvider"]
        except Exception:
            pass
        return ["CPUExecutionProvider"]

    @classmethod
    def embed_face(cls, image: np.ndarray) -> list[float] | None:
        app = cls.ensure_loaded()
        faces = app.get(image)
        if not faces:
            return None
        # use the largest face
        faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)
        return faces[0].normed_embedding.tolist()
