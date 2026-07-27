"""Chunk Einstein Wikipedia text and embed locally. Run once: python embed.py

Why embeddings: they turn text into vectors so later we can find chunks
whose meaning is close to a user's question (retrieval), not just keyword match.

Anthropic's API does not offer embeddings, so we use a free local model
(sentence-transformers / all-MiniLM-L6-v2) instead of a paid embedding API.
"""

import json
import re
from pathlib import Path

from sentence_transformers import SentenceTransformer

INPUT_PATH = Path("data/einstein/wikipedia.txt")
OUTPUT_PATH = Path("data/einstein/chunks.json")
FIGURE = "einstein"

# Target chunk size in words (Architecture step 3: ~200-400).
MIN_WORDS = 200
TARGET_WORDS = 300
MAX_WORDS = 400

# Small, fast, free local model — no API key / no per-call cost.
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def word_count(text: str) -> int:
    return len(text.split())


def split_into_paragraphs(text: str) -> list[str]:
    parts = re.split(r"\n\s*\n", text.strip())
    return [p.strip() for p in parts if p.strip()]


def split_long_paragraph(paragraph: str) -> list[str]:
    """If one paragraph is too long, split on sentence boundaries."""
    if word_count(paragraph) <= MAX_WORDS:
        return [paragraph]

    # Split on sentence-ending punctuation followed by whitespace.
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

        # Prefer not exceeding MAX_WORDS — flush before adding when needed.
        if current and current_words + para_words > MAX_WORDS:
            chunks.append("\n\n".join(current))
            current = [para]
            current_words = para_words
        else:
            current.append(para)
            current_words += para_words

        # Soft flush around the target size once we have enough text.
        if current and current_words >= TARGET_WORDS:
            chunks.append("\n\n".join(current))
            current = []
            current_words = 0

    if current:
        leftover = "\n\n".join(current)
        # Only merge a tiny leftover if it won't blow past MAX_WORDS.
        if (
            chunks
            and word_count(leftover) < MIN_WORDS // 2
            and word_count(chunks[-1]) + word_count(leftover) <= MAX_WORDS + 50
        ):
            chunks[-1] = chunks[-1] + "\n\n" + leftover
        else:
            chunks.append(leftover)

    return chunks


def main() -> None:
    if not INPUT_PATH.exists():
        raise SystemExit(f"Missing {INPUT_PATH}. Run `python ingest.py` first.")

    text = INPUT_PATH.read_text(encoding="utf-8")
    chunks = chunk_text(text)
    if not chunks:
        raise SystemExit("No chunks produced — check the source text.")

    print(f"Chunked into {len(chunks)} pieces. Loading embedding model...")
    model = SentenceTransformer(MODEL_NAME)
    embeddings = model.encode(chunks, show_progress_bar=True)

    records = [
        {
            "text": chunk,
            "embedding": embedding.tolist(),
            "figure": FIGURE,
        }
        for chunk, embedding in zip(chunks, embeddings)
    ]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(records), encoding="utf-8")

    dims = len(records[0]["embedding"])
    print(f"Saved to {OUTPUT_PATH}")
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
