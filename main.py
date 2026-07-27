import os

import httpx
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import create_access_token, get_current_user, hash_password, verify_password
from database import Message, Personality, User, get_db, init_db, seed_personalities
from pipeline import process_personality
from retrieve import retrieve

load_dotenv()

app = FastAPI()

# Local Ollama — no API key. Why local: zero cost / offline for learning.
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    seed_personalities()


class ChatRequest(BaseModel):
    personality_id: int
    message: str


class ChatResponse(BaseModel):
    reply: str


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: str

    model_config = {"from_attributes": True}


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str


class PersonalityOut(BaseModel):
    id: int
    name: str
    photo_url: str | None
    status: str

    model_config = {"from_attributes": True}


class PersonalitySearchRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class PersonalityStatusOut(BaseModel):
    id: int
    status: str


def build_system_prompt(figure: str, chunks: list[dict]) -> str:
    """Persona + grounding rules. Why a system prompt: it tells the model
    *how* to answer (in character, grounded) before it sees the user question."""
    source_blocks = []
    for i, chunk in enumerate(chunks, start=1):
        source_blocks.append(f"[Source {i}]\n{chunk['text']}")
    sources = "\n\n".join(source_blocks)

    return f"""You are role-playing as {figure} in an educational simulation.
Speak in the first person as {figure}.

Rules:
- Base your answers ONLY on the Source material below. Do not invent facts,
  opinions, or events that are not supported by it.
- If the Source material does not cover the question, say so in character
  (for example, admit you do not recall discussing that, or that it was
  outside what you wrote about) rather than guessing.
- Match the voice and tone suggested by the Source material — the documented
  personality and era — not a generic "old-timey" accent or caricature.
- Keep answers concise and conversational.

Source material:
{sources}
"""


def call_ollama(system_prompt: str, user_message: str) -> str:
    """POST to Ollama's local /api/chat. Uses httpx (already in the venv)."""
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    }
    try:
        response = httpx.post(OLLAMA_URL, json=payload, timeout=120.0)
        response.raise_for_status()
    except (httpx.ConnectError, httpx.ConnectTimeout):
        raise RuntimeError(
            "Ollama isn't running. Start it with `ollama serve`, "
            "then make sure you've pulled the model: `ollama pull llama3.2:3b`."
        ) from None
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"Ollama returned an error ({exc.response.status_code}): "
            f"{exc.response.text}"
        ) from None

    data = response.json()
    return data["message"]["content"]


@app.post("/auth/signup", response_model=TokenResponse)
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    email = req.email.lower().strip()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(email=email, hashed_password=hash_password(req.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token, user_id=user.id, email=user.email)


@app.post("/auth/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    email = req.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token, user_id=user.id, email=user.email)


@app.get("/auth/me")
def me(current_user: User = Depends(get_current_user)):
    """Example protected route — proves JWT dependency works."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "created_at": current_user.created_at.isoformat(),
    }


@app.get("/personalities", response_model=list[PersonalityOut])
def list_personalities(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Home-screen list: all personalities with status."""
    _ = current_user  # auth gate
    return db.query(Personality).order_by(Personality.name).all()


@app.post("/personalities/search", response_model=PersonalityOut)
def search_personality(
    req: PersonalitySearchRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Find or create a personality, then kick off RAG ingest if needed."""
    _ = current_user
    name = " ".join(req.name.split()).strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    existing = (
        db.query(Personality)
        .filter(func.lower(Personality.name) == name.lower())
        .first()
    )

    if existing and existing.status == "ready":
        return existing

    if existing is None:
        existing = Personality(name=name, photo_url=None, status="pending")
        db.add(existing)
        db.commit()
        db.refresh(existing)

    # Kick off pipeline for pending/failed; leave processing alone.
    if existing.status in ("pending", "failed"):
        existing.status = "processing"
        db.commit()
        db.refresh(existing)
        background_tasks.add_task(process_personality, existing.id)

    return existing


@app.get("/personalities/{personality_id}/status", response_model=PersonalityStatusOut)
def personality_status(
    personality_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Polling endpoint while background ingest runs."""
    _ = current_user
    personality = db.get(Personality, personality_id)
    if personality is None:
        raise HTTPException(status_code=404, detail="Personality not found")
    return PersonalityStatusOut(id=personality.id, status=personality.status)


@app.get("/personalities/{personality_id}/messages", response_model=list[MessageOut])
def list_messages(
    personality_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Restore chat history for this user + personality."""
    personality = db.get(Personality, personality_id)
    if personality is None:
        raise HTTPException(status_code=404, detail="Personality not found")

    rows = (
        db.query(Message)
        .filter(
            Message.user_id == current_user.id,
            Message.personality_id == personality_id,
        )
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )
    return [
        MessageOut(
            id=m.id,
            role=m.role,
            content=m.content,
            created_at=m.created_at.isoformat(),
        )
        for m in rows
    ]


@app.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    personality = db.get(Personality, req.personality_id)
    if personality is None:
        raise HTTPException(status_code=404, detail="Personality not found")
    if personality.status != "ready":
        raise HTTPException(
            status_code=400,
            detail=(
                f"'{personality.name}' is not ready yet "
                f"(status={personality.status}). "
                "Wait until ingestion finishes, then try again."
            ),
        )

    message_text = req.message.strip()
    if not message_text:
        raise HTTPException(status_code=400, detail="Message is required")

    db.add(
        Message(
            user_id=current_user.id,
            personality_id=personality.id,
            role="user",
            content=message_text,
        )
    )
    db.commit()

    try:
        chunks = retrieve(message_text, figure=personality.name, top_k=5)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from None

    system_prompt = build_system_prompt(personality.name, chunks)

    # Temporary debug print — remove once prompt looks right.
    print("\n===== SYSTEM PROMPT =====")
    print(system_prompt)
    print("===== END SYSTEM PROMPT =====\n")

    try:
        reply = call_ollama(system_prompt, message_text)
    except RuntimeError as exc:
        reply = str(exc)

    db.add(
        Message(
            user_id=current_user.id,
            personality_id=personality.id,
            role="assistant",
            content=reply,
        )
    )
    db.commit()

    return ChatResponse(reply=reply)


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/index.html")
