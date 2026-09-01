import os

import numpy as np
import torch

MODEL_DIR = os.environ.get("MODEL_DIR", "/models")
MODEL_NAME = "ViT-B-32"
PRETRAINED = "laion2b_s34b_b79k"


class ClipEngine:
    """OpenCLIP text/image vectorizer -> 512-d embeddings for AcuSeek search."""

    _model = None
    _tokenizer = None
    _preprocess = None
    _device = None

    @classmethod
    def ensure_loaded(cls):
        if cls._model is not None:
            return
        import open_clip
        cls._device = "cuda" if torch.cuda.is_available() else "cpu"
        model, _, preprocess = open_clip.create_model_and_transforms(
            MODEL_NAME, pretrained=PRETRAINED,
            cache_dir=os.path.join(MODEL_DIR, "openclip"), device=cls._device,
        )
        tokenizer = open_clip.get_tokenizer(MODEL_NAME)
        model.eval()
        cls._model = model
        cls._tokenizer = tokenizer
        cls._preprocess = preprocess

    @classmethod
    def _normalize(cls, vec: torch.Tensor) -> list[float]:
        with torch.no_grad():
            vec = vec / vec.norm(dim=-1, keepdim=True)
        return vec.cpu().numpy().tolist()[0]

    @classmethod
    def embed_text(cls, text: str) -> list[float]:
        cls.ensure_loaded()
        with torch.no_grad():
            tokens = cls._tokenizer([text]).to(cls._device)
            vec = cls._model.encode_text(tokens)
        return cls._normalize(vec)

    @classmethod
    def embed_image(cls, image_bgr: np.ndarray) -> list[float]:
        cls.ensure_loaded()
        rgb = image_bgr[:, :, ::-1].copy()
        from PIL import Image
        pil = Image.fromarray(rgb)
        tensor = cls._preprocess(pil).unsqueeze(0).to(cls._device)
        with torch.no_grad():
            vec = cls._model.encode_image(tensor)
        return cls._normalize(vec)
