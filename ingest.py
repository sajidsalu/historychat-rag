"""Fetch and clean a historical figure's Wikipedia article.

Reusable for the API pipeline; also runnable as: python ingest.py
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote

import httpx
import wikipediaapi

# Drop these sections and everything after them (boilerplate, not biography).
STOP_SECTIONS = (
    "See also",
    "References",
    "External links",
    "Notes",
    "Further reading",
    "Bibliography",
    "Sources",
    "Publications",  # citation lists, not biographical prose
)

# Prefer canonical Wikipedia titles for known starter figures.
WIKI_TITLE_ALIASES = {
    "einstein": "Albert Einstein",
    "albert einstein": "Albert Einstein",
    "gandhi": "Mahatma Gandhi",
    "mahatma gandhi": "Mahatma Gandhi",
    "marie curie": "Marie Curie",
}

USER_AGENT = "HistoryChat/0.1 (learning project; local ingest)"
SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"


class WikipediaNotFoundError(Exception):
    """Raised when the Wikipedia page does not exist / is not a real article."""


def slugify(name: str) -> str:
    """Turn a display name into a filesystem-safe folder key."""
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower())
    return slug.strip("_") or "unknown"


def data_dir(figure_slug: str) -> Path:
    return Path("data") / figure_slug


def wikipedia_path(figure_slug: str) -> Path:
    return data_dir(figure_slug) / "wikipedia.txt"


def resolve_wiki_title(name: str) -> str:
    return WIKI_TITLE_ALIASES.get(name.strip().lower(), name.strip())


def clean_text(text: str) -> str:
    # Cut at the first stop-section header (line that is exactly the section title).
    cut_at = len(text)
    for section in STOP_SECTIONS:
        match = re.search(rf"(?m)^{re.escape(section)}\s*$", text)
        if match and match.start() < cut_at:
            cut_at = match.start()
    text = text[:cut_at]

    # Strip reference markers: [1], [12], [a], [citation needed], etc.
    text = re.sub(r"\[[^\]]{0,40}\]", "", text)

    # Collapse extra blank lines left after stripping.
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def fetch_page_summary(name: str) -> dict:
    """Hit Wikipedia REST summary. Rejects missing pages and disambiguation pages."""
    title = resolve_wiki_title(name)
    url = SUMMARY_URL.format(title=quote(title, safe=""))
    try:
        response = httpx.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            follow_redirects=True,
            timeout=30.0,
        )
    except httpx.HTTPError as exc:
        raise WikipediaNotFoundError(
            f"Could not reach Wikipedia for '{name}'."
        ) from exc

    if response.status_code == 404:
        raise WikipediaNotFoundError(
            f"No historical figure found with that name ('{name}')."
        )
    if response.status_code >= 400:
        raise WikipediaNotFoundError(
            f"Wikipedia lookup failed for '{name}' (HTTP {response.status_code})."
        )

    data = response.json()
    page_type = data.get("type")
    # "disambiguation" = not a single real figure article
    if page_type == "disambiguation":
        raise WikipediaNotFoundError(
            f"'{name}' matches multiple Wikipedia pages — try a more specific name."
        )
    return data


def thumbnail_from_summary(summary: dict) -> str | None:
    thumb = summary.get("thumbnail") or {}
    source = thumb.get("source")
    return source if source else None


def fetch_thumbnail_url(name: str) -> str | None:
    """Fetch only the thumbnail URL (for backfills). May raise WikipediaNotFoundError."""
    return thumbnail_from_summary(fetch_page_summary(name))


def fetch_wikipedia_text(name: str) -> str:
    """Fetch + clean Wikipedia prose for `name`. Raises WikipediaNotFoundError."""
    title = resolve_wiki_title(name)
    wiki = wikipediaapi.Wikipedia(
        user_agent=USER_AGENT,
        language="en",
    )
    page = wiki.page(title)
    if not page.exists():
        raise WikipediaNotFoundError(
            f"Wikipedia page not found for '{name}' (tried '{title}')."
        )
    return clean_text(page.text)


def ingest_figure(name: str) -> tuple[Path, str | None]:
    """Fetch Wikipedia text + thumbnail; save text to data/<slug>/wikipedia.txt.

    Returns (path_to_text, photo_url_or_none).
    """
    summary = fetch_page_summary(name)
    photo_url = thumbnail_from_summary(summary)

    figure_slug = slugify(name)
    cleaned = fetch_wikipedia_text(name)
    out = wikipedia_path(figure_slug)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(cleaned, encoding="utf-8")
    return out, photo_url


def main() -> None:
    name = "Albert Einstein"
    path, photo = ingest_figure(name)
    text = path.read_text(encoding="utf-8")
    print(f"Saved to {path}")
    print(f"Photo URL: {photo}")
    print(f"Total characters: {len(text)}")
    print(f"First 200 characters:\n{text[:200]}")


if __name__ == "__main__":
    main()
