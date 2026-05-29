import threading
from typing import List

import google.generativeai as genai

from app.config import settings

# A single embedding model is used for BOTH indexing and querying.
# Mixing models (e.g. gemini-embedding-001 vs text-embedding-004) produces
# vectors of different dimensions and different vector spaces, which makes
# every FAISS search result meaningless. text-embedding-004 is natively
# 768-dim, matching CodeSearchService.dimension.
EMBED_MODEL = "models/text-embedding-004"

# google.generativeai stores the API key in global module state, so
# configure() and the API call must not interleave across threads/requests.
_genai_lock = threading.Lock()


class EmbeddingsService:
    def __init__(self, api_keys: List[str] = None):
        source_keys = api_keys if api_keys else [settings.gemini_api_key]

        # Flatten any comma/newline separated key strings into a clean pool.
        self.api_keys: List[str] = []
        for k in source_keys:
            if isinstance(k, str):
                self.api_keys.extend(
                    sk.strip()
                    for sk in k.replace(",", "\n").split("\n")
                    if sk.strip()
                )

        if not self.api_keys:
            self.api_keys = ["dummy"]

        self.current_key_index = 0

    def get_embeddings(
        self, texts: List[str], task_type: str = "retrieval_document"
    ) -> List[List[float]]:
        """
        Embed a list of texts, rotating API keys on rate limits.
        Returns one vector per input text.
        """
        if not texts:
            return []

        last_error = None
        for _ in range(len(self.api_keys)):
            api_key = self.api_keys[self.current_key_index].strip()
            try:
                # Hold the lock across configure + call so a concurrent
                # request cannot swap the global key mid-request.
                with _genai_lock:
                    genai.configure(api_key=api_key, transport="rest")
                    result = genai.embed_content(
                        model=EMBED_MODEL,
                        content=texts,
                        task_type=task_type,
                    )
                return result["embedding"]
            except Exception as e:
                last_error = e
                if "429" in str(e) and len(self.api_keys) > 1:
                    self.current_key_index = (
                        self.current_key_index + 1
                    ) % len(self.api_keys)
                    print(
                        f"Embedding rate limit — rotating to key "
                        f"index {self.current_key_index}"
                    )
                    continue
                raise

        raise Exception(
            f"All {len(self.api_keys)} embedding API key(s) failed. "
            f"Last error: {last_error}"
        )

    def get_embedding(self, text: str) -> List[float]:
        """Embed a single query string."""
        return self.get_embeddings([text], task_type="retrieval_query")[0]
