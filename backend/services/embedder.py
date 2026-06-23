"""Lazy-loaded OpenCLIP embedder shared by retrieval."""

from functools import lru_cache
from typing import Optional

import numpy as np
import torch
from PIL import Image


@lru_cache(maxsize=1)
def _load_clip():
    import open_clip

    model, _, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32",
        pretrained="laion2b_s34b_b79k",
    )
    tokenizer = open_clip.get_tokenizer("ViT-B-32")
    model.eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)
    return model, preprocess, tokenizer, device


def embed_text(text: str) -> np.ndarray:
    model, _, tokenizer, device = _load_clip()
    tokens = tokenizer([text]).to(device)
    with torch.no_grad():
        vec = model.encode_text(tokens)
        vec = vec / vec.norm(dim=-1, keepdim=True)
    return vec.cpu().numpy()[0].astype(np.float32)


def embed_image(image_path: str) -> Optional[np.ndarray]:
    model, preprocess, _, device = _load_clip()
    try:
        img = Image.open(image_path).convert("RGB")
    except OSError:
        return None
    tensor = preprocess(img).unsqueeze(0).to(device)
    with torch.no_grad():
        vec = model.encode_image(tensor)
        vec = vec / vec.norm(dim=-1, keepdim=True)
    return vec.cpu().numpy()[0].astype(np.float32)
