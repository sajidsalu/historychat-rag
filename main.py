import os

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from retrieve import retrieve

load_dotenv()

app = FastAPI()

# Local Ollama — no API key. Why local: zero cost / offline for learning.
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

# Only Einstein has ingested/embedded data so far.
SUPPORTED_FIGURES = {"einstein"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    figure: str
    message: str


def build_system_prompt(figure: str, chunks: list[dict]) -> str:
    """Persona + grounding rules. Why a system prompt: it tells the model
    *how* to answer (in character, grounded) before it sees the user question."""
    source_blocks = []
    for i, chunk in enumerate(chunks, start=1):
        source_blocks.append(f"[Source {i}]\n{chunk['text']}")
    sources = "\n\n".join(source_blocks)

    return f"""You are role-playing as {figure.title()} in an educational simulation.
Speak in the first person as {figure.title()}.

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


@app.post("/chat")
async def chat(req: ChatRequest):
    figure_key = req.figure.strip().lower()

    if figure_key not in SUPPORTED_FIGURES:
        return {
            "reply": (
                f"Sorry — I don't have source data for {req.figure} yet. "
                "Only Einstein is available right now."
            )
        }

    chunks = retrieve(req.message, top_k=5)
    system_prompt = build_system_prompt(figure_key, chunks)

    # Temporary debug print — remove once prompt looks right.
    print("\n===== SYSTEM PROMPT =====")
    print(system_prompt)
    print("===== END SYSTEM PROMPT =====\n")

    try:
        reply = call_ollama(system_prompt, req.message)
    except RuntimeError as exc:
        return {"reply": str(exc)}

    return {"reply": reply}


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/index.html")
