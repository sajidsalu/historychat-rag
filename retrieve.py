"""Retrieve the most relevant Einstein chunks for a query.

Why retrieval: embed the question the same way we embedded the docs, then
pick the chunks whose vectors are closest (cosine similarity) — those become
the grounded context for the LLM later.
"""

import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

CHUNKS_PATH = Path("data/einstein/chunks.json")
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model: SentenceTransformer | None = None
_chunk_texts: list[str] | None = None
_embeddings: np.ndarray | None = None


def _load() -> tuple[list[str], np.ndarray]:
    """Load chunks + embeddings once (lazy), reuse on later calls."""
    global _chunk_texts, _embeddings
    if _chunk_texts is not None and _embeddings is not None:
        return _chunk_texts, _embeddings

    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(
            f"Missing {CHUNKS_PATH}. Run `python embed.py` first."
        )

    records = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    _chunk_texts = [r["text"] for r in records]
    _embeddings = np.array([r["embedding"] for r in records], dtype=np.float32)
    return _chunk_texts, _embeddings


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Cosine similarity of one vector `a` against every row in matrix `b`."""
    a_norm = a / (np.linalg.norm(a) + 1e-12)
    b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-12)
    return b_norm @ a_norm


def retrieve(query: str, top_k: int = 4) -> list[dict]:
    """Return top_k chunks most similar to `query`, highest score first.

    Each item: {"text": str, "score": float}
    """
    texts, embeddings = _load()
    model = _get_model()
    query_vec = model.encode(query)
    scores = cosine_similarity(np.asarray(query_vec, dtype=np.float32), embeddings)

    # Argsort descending, take top_k.
    top_indices = np.argsort(scores)[::-1][:top_k]
    return [
        {"text": texts[i], "score": float(scores[i])}
        for i in top_indices
    ]


if __name__ == "__main__":
    question = "What did Einstein think about war?"
    print(f"Query: {question}\n")
    results = retrieve(question, top_k=4)
    for i, hit in enumerate(results, start=1):
        snippet = hit["text"][:220].replace("\n", " ")
        print(f"--- Result {i} (score={hit['score']:.4f}) ---")
        print(snippet + ("..." if len(hit["text"]) > 220 else ""))
        print()
