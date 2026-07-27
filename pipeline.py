"""Background RAG pipeline: Wikipedia ingest → chunk/embed → status update."""

from database import Personality, SessionLocal
from embed import embed_figure
from ingest import WikipediaNotFoundError, ingest_figure
from retrieve import invalidate_cache


def process_personality(personality_id: int) -> None:
    """Run ingest+embed for one personality; update status along the way.

    Uses its own DB session because BackgroundTasks outlive the request.
    """
    db = SessionLocal()
    try:
        personality = db.get(Personality, personality_id)
        if personality is None:
            return

        personality.status = "processing"
        db.commit()

        try:
            ingest_figure(personality.name)
            embed_figure(personality.name)
            invalidate_cache(personality.name)
            personality.status = "ready"
            db.commit()
            print(f"[pipeline] {personality.name} ready (id={personality_id})")
        except WikipediaNotFoundError as exc:
            personality.status = "failed"
            db.commit()
            print(f"[pipeline] {personality.name} failed: {exc}")
        except Exception as exc:
            personality.status = "failed"
            db.commit()
            print(f"[pipeline] {personality.name} failed: {exc}")
    finally:
        db.close()
