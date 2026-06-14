import os
import threading
from typing import List

import numpy as np

# Local, keyless embeddings via fastembed (ONNX runtime, no torch).
# First use downloads ~50MB of model weights into FASTEMBED_CACHE_PATH
# (or the user's HF cache), then everything runs offline on CPU.
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384

_model_lock = threading.Lock()
_model = None


def _get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from fastembed import TextEmbedding
                cache_dir = os.environ.get("FASTEMBED_CACHE_PATH")
                kwargs = {"model_name": EMBED_MODEL}
                if cache_dir:
                    kwargs["cache_dir"] = cache_dir
                _model = TextEmbedding(**kwargs)
    return _model


class EmbeddingsService:
    """Keyless embeddings via fastembed. The constructor accepts an unused
    ``api_keys`` argument for backward compatibility with callers that used
    to pass Gemini keys."""

    def __init__(self, api_keys: List[str] = None):
        # api_keys intentionally ignored — kept for signature compatibility.
        _ = api_keys

    def get_embeddings(
        self, texts: List[str], task_type: str = "retrieval_document"
    ) -> List[List[float]]:
        _ = task_type  # bge-small treats documents and queries uniformly
        if not texts:
            return []
        model = _get_model()
        vectors = [np.asarray(v, dtype="float32").tolist() for v in model.embed(texts)]
        return vectors

    def get_embedding(self, text: str) -> List[float]:
        return self.get_embeddings([text])[0]
