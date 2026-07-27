"""Fetch and clean Einstein's Wikipedia article. Run once: python ingest.py"""

import re
from pathlib import Path

import wikipediaapi

OUTPUT_PATH = Path("data/einstein/wikipedia.txt")

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


def clean_text(text: str) -> str:
    # Cut at the first stop-section header (line that is exactly the section title).
    cut_at = len(text)
    for section in STOP_SECTIONS:
        # Match a line that is only the section title (wikipedia-api plain text format).
        match = re.search(rf"(?m)^{re.escape(section)}\s*$", text)
        if match and match.start() < cut_at:
            cut_at = match.start()
    text = text[:cut_at]

    # Strip reference markers: [1], [12], [a], [citation needed], etc.
    text = re.sub(r"\[[^\]]{0,40}\]", "", text)

    # Collapse extra blank lines left after stripping.
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def main() -> None:
    wiki = wikipediaapi.Wikipedia(
        user_agent="HistoryChat/0.1 (learning project; local ingest script)",
        language="en",
    )
    page = wiki.page("Albert Einstein")
    if not page.exists():
        raise SystemExit("Wikipedia page 'Albert Einstein' not found.")

    cleaned = clean_text(page.text)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(cleaned, encoding="utf-8")

    print(f"Saved to {OUTPUT_PATH}")
    print(f"Total characters: {len(cleaned)}")
    print(f"First 200 characters:\n{cleaned[:200]}")


if __name__ == "__main__":
    main()
