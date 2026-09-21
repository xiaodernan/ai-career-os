"""Hash embedding provider — OFFLINE DEV ONLY.

Deterministic bag-of-subword embeddings; enables the whole retrieval pipeline without
any external service. Documents ingested with this provider are marked in their
metadata so the UI can warn that semantic quality is degraded.
"""

import hashlib
import math


class HashEmbeddingProvider:
    name = "hash"

    def __init__(self, dim: int = 1536):
        self.dim = dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(t) for t in texts]

    def _one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = text.lower().split()
        for tok in tokens:
            for n in (tok, tok[:4], tok[-4:]):
                h = int.from_bytes(hashlib.blake2b(n.encode(), digest_size=8).digest(), "big")
                idx = h % self.dim
                sign = 1.0 if (h >> 63) & 1 == 0 else -1.0
                vec[idx] += sign * (1 + math.log1p(1))
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]
