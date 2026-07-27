"""SQLite database setup via SQLAlchemy.

Why a DB: store users, personalities, and chat messages so auth and
multi-user history can live outside the LLM pipeline.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

DATABASE_URL = "sqlite:///./historychat.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # needed for SQLite + FastAPI
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    messages: Mapped[list["Message"]] = relationship(back_populates="user")


class Personality(Base):
    __tablename__ = "personalities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # pending | processing | ready | failed
    status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    messages: Mapped[list["Message"]] = relationship(back_populates="personality")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    personality_id: Mapped[int] = mapped_column(ForeignKey("personalities.id"))
    role: Mapped[str] = mapped_column(String(32))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(back_populates="messages")
    personality: Mapped["Personality"] = relationship(back_populates="messages")


def get_db():
    """FastAPI dependency: yield a DB session, always close it after."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def seed_personalities() -> None:
    """Idempotent seed: insert starter figures if the table is empty."""
    db = SessionLocal()
    try:
        if db.query(Personality).count() > 0:
            return

        starters = [
            Personality(
                name="Einstein",
                photo_url=None,
                status="ready",  # existing wikipedia + chunks data
            ),
            Personality(
                name="Gandhi",
                photo_url=None,
                status="pending",
            ),
            Personality(
                name="Marie Curie",
                photo_url=None,
                status="pending",
            ),
        ]
        db.add_all(starters)
        db.commit()
        print("Seeded personalities: Einstein (ready), Gandhi (pending), Marie Curie (pending)")
    finally:
        db.close()
