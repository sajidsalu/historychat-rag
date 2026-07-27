"""Chunk Wikipedia text and embed locally.

Reusable for the API pipeline; also runnable as: python embed.py

Why embeddings: they turn text into vectors so later we can find chunks
whose meaning is close to a user's question (retrieval), not just keyword match.
"""

import json
import re
from pathlib import Path

from sentence_transformers import SentenceTransformer

from ingest import slugify, wikipedia_path

# Target chunk size in words (Architecture step 3: ~200-400).
MIN_WORDS = 200
TARGET_WORDS = 300
MAX_WORDS = 400

# Small, fast, free local model — no API key / no per-call cost.
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model: SentenceTransformer | None = None


def chunks_path(figure_slug: str) -> Path:
    return Path("data") / figure_slug / "chunks.json"


def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def word_count(text: str) -> int:
    return len(text.split())


def split_into_paragraphs(text: str) -> list[str]:
    parts = re.split(r"\n\s*\n", text.strip())
    return [p.strip() for p in parts if p.strip()]


def split_long_paragraph(paragraph: str) -> list[str]:
    """If one paragraph is too long, split on sentence boundaries."""
    if word_count(paragraph) <= MAX_WORDS:
        return [paragraph]

    sentences = re.split(r"(?<=[.!?])\s+", paragraph)
    chunks: list[str] = []
    current: list[str] = []

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        trial = " ".join(current + [sentence])
        if current and word_count(trial) > MAX_WORDS:
            chunks.append(" ".join(current))
            current = [sentence]
        else:
            current.append(sentence)

    if current:
        chunks.append(" ".join(current))
    return chunks


def chunk_text(text: str) -> list[str]:
    """Build ~200-400 word chunks, preferring paragraph boundaries."""
    paragraphs: list[str] = []
    for para in split_into_paragraphs(text):
        paragraphs.extend(split_long_paragraph(para))

    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    for para in paragraphs:
        para_words = word_count(para)

        if current and current_words + para_words > MAX_WORDS:
            chunks.append("\n\n".join(current))
            current = [para]
            current_words = para_words
        else:
            current.append(para)
            current_words += para_words

        if current and current_words >= TARGET_WORDS:
            chunks.append("\n\n".join(current))
            current = []
            current_words = 0

    if current:
        leftover = "\n\n".join(current)
        if (
            chunks
            and word_count(leftover) < MIN_WORDS // 2
            and word_count(chunks[-1]) + word_count(leftover) <= MAX_WORDS + 50
        ):
            chunks[-1] = chunks[-1] + "\n\n" + leftover
        else:
            chunks.append(leftover)

    return chunks


def embed_figure(name: str) -> Path:
    """Chunk + embed data/<slug>/wikipedia.txt → chunks.json for this figure."""
    figure_slug = slugify(name)
    input_path = wikipedia_path(figure_slug)
    output_path = chunks_path(figure_slug)

    if not input_path.exists():
        raise FileNotFoundError(
            f"Missing {input_path}. Run ingest for '{name}' first."
        )

    text = input_path.read_text(encoding="utf-8")
    chunks = chunk_text(text)
    if not chunks:
        raise ValueError(f"No chunks produced for '{name}'.")

    model = get_embedding_model()
    embeddings = model.encode(chunks, show_progress_bar=False)

    records = [
        {
            "text": chunk,
            "embedding": embedding.tolist(),
            "figure": figure_slug,
        }
        for chunk, embedding in zip(chunks, embeddings)
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(records), encoding="utf-8")
    return output_path


def main() -> None:
    name = "Einstein"
    print(f"Embedding figure: {name}")
    path = embed_figure(name)
    records = json.loads(path.read_text(encoding="utf-8"))
    dims = len(records[0]["embedding"])
    print(f"Saved to {path}")
    print(f"Number of chunks: {len(records)}")
    print(f"Embedding dimensions: {dims}")
    print(
        "Word counts (min/avg/max): "
        f"{min(word_count(c['text']) for c in records)} / "
        f"{sum(word_count(c['text']) for c in records) // len(records)} / "
        f"{max(word_count(c['text']) for c in records)}"
    )


if __name__ == "__main__":
    main()
