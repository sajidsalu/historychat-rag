"""Retrieve the most relevant chunks for a query + figure.

Why retrieval: embed the question the same way we embedded the docs, then
pick the chunks whose vectors are closest (cosine similarity) — those become
the grounded context for the LLM later.
"""

import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from embed import MODEL_NAME, chunks_path
from ingest import slugify

_model: SentenceTransformer | None = None
# Cache embeddings per figure slug so we don't re-read JSON every request.
_cache: dict[str, tuple[list[str], np.ndarray]] = {}


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _load(figure_slug: str) -> tuple[list[str], np.ndarray]:
    if figure_slug in _cache:
        return _cache[figure_slug]

    path = chunks_path(figure_slug)
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Ingest/embed this figure first "
            f"(status should be 'ready')."
        )

    records = json.loads(path.read_text(encoding="utf-8"))
    texts = [r["text"] for r in records]
    embeddings = np.array([r["embedding"] for r in records], dtype=np.float32)
    _cache[figure_slug] = (texts, embeddings)
    return texts, embeddings


def invalidate_cache(figure: str | None = None) -> None:
    """Drop cached vectors (e.g. after a new embed finishes)."""
    if figure is None:
        _cache.clear()
        return
    _cache.pop(slugify(figure), None)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Cosine similarity of one vector `a` against every row in matrix `b`."""
    a_norm = a / (np.linalg.norm(a) + 1e-12)
    b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-12)
    return b_norm @ a_norm


def retrieve(query: str, figure: str = "einstein", top_k: int = 4) -> list[dict]:
    """Return top_k chunks for `figure` most similar to `query`.

    Each item: {"text": str, "score": float}
    """
    figure_slug = slugify(figure)
    texts, embeddings = _load(figure_slug)
    model = _get_model()
    query_vec = model.encode(query)
    scores = cosine_similarity(np.asarray(query_vec, dtype=np.float32), embeddings)

    top_indices = np.argsort(scores)[::-1][:top_k]
    return [
        {"text": texts[i], "score": float(scores[i])}
        for i in top_indices
    ]


if __name__ == "__main__":
    question = "What did Einstein think about war?"
    print(f"Query: {question}\n")
    results = retrieve(question, figure="einstein", top_k=4)
    for i, hit in enumerate(results, start=1):
        snippet = hit["text"][:220].replace("\n", " ")
        print(f"--- Result {i} (score={hit['score']:.4f}) ---")
        print(snippet + ("..." if len(hit["text"]) > 220 else ""))
        print()
