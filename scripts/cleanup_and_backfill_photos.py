"""One-off: backfill photo_url for ready personalities + delete bad test rows.

Run from project root:
  PYTHONPATH=. python scripts/cleanup_and_backfill_photos.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import Message, Personality, SessionLocal, init_db
from ingest import WikipediaNotFoundError, fetch_thumbnail_url

BAD_NAMES = ("XyzzyNotAPerson999", "NotReadyTest")


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        # Delete bad rows (messages first due to FK)
        bad = (
            db.query(Personality)
            .filter(Personality.name.in_(BAD_NAMES))
            .all()
        )
        for p in bad:
            db.query(Message).filter(Message.personality_id == p.id).delete()
            print(f"Deleted personality: {p.name}")
            db.delete(p)
        db.commit()

        # Backfill thumbnails for ready figures missing photos
        ready = (
            db.query(Personality)
            .filter(Personality.status == "ready")
            .all()
        )
        for p in ready:
            if p.photo_url:
                print(f"Skip (already has photo): {p.name}")
                continue
            try:
                url = fetch_thumbnail_url(p.name)
            except WikipediaNotFoundError as exc:
                print(f"No photo for {p.name}: {exc}")
                continue
            if url:
                p.photo_url = url
                print(f"Backfilled {p.name}: {url}")
            else:
                print(f"No thumbnail on Wikipedia for {p.name}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
