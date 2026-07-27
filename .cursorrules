# Project: HistoryChat — Talk to a Historical Figure (AI, RAG-based)

## What this is

A chatbot that lets a user pick a historical figure (e.g. Einstein, Gandhi) and
chat with an AI persona that answers "in character," grounded in real source
text (Wikipedia + public-domain writings) via RAG — not just the model's
generic training-data impression of the person.

This is a learning project. The person building it is a frontend dev with
**zero prior RAG/MCP/AI-app experience**, learning by doing. Prioritize:

- Small, working steps over big/clever ones.
- Explaining _why_, briefly, when introducing a new AI concept for the first time
  (RAG, embeddings, vector search, system prompts) — one or two sentences, not
  a lecture. After the first explanation, don't re-explain the same concept.
- Minimal token/API usage: prefer small test datasets (1 figure, ~3-5 short
  documents) while building/debugging. Only scale up data volume once the
  pipeline works end-to-end.

## Tech stack

- Backend: FastAPI (Python)
- Frontend: simple chat UI (plain HTML/JS or minimal React — keep it simple,
  this project is not about frontend polish)
- LLM: Anthropic Claude API (model: claude-sonnet-5)
- Embeddings + vector store: start with the simplest possible option
  (e.g. a flat numpy cosine-similarity search over a small local JSON/pickle
  file). Do NOT set up a hosted vector DB (Pinecone etc.) — unnecessary cost
  and complexity for this scale.
- Data source: Wikipedia (via API or MCP server) + optionally public-domain
  texts (e.g. Project Gutenberg letters/writings) for richer voice.

## Architecture (build in this order)

1. **Skeleton app** — FastAPI backend with one hardcoded response + simple
   chat frontend. No AI yet. Goal: prove the plumbing works.
2. **Data ingestion** — fetch Wikipedia article(s) for ONE figure to start.
   Clean the text (strip markup/references). Save as plain text files in
   `data/<figure_name>/`.
3. **Chunking + embeddings** — split source docs into small chunks (~200-400
   words), embed them, store vectors + chunk text + source figure as metadata.
4. **Retrieval** — given a user question + selected figure, embed the
   question, retrieve top-k (start with k=3-5) most similar chunks for that
   figure only.
5. **Persona system prompt** — construct the Claude API call: system prompt
   defines the persona + grounding rules (see below), retrieved chunks go in
   as context, user question as the message.
6. **Wire it together** — chat endpoint does steps 4+5 and returns the
   in-character answer to the frontend.
7. (Stretch) Multi-turn memory, citations, multi-figure comparison.

## Persona system prompt — core rules (don't deviate without discussing)

- Speak in first person as the selected figure.
- Answers must be grounded in the retrieved context chunks provided. If the
  context doesn't cover the question, say so _in character_ rather than
  inventing facts or opinions the person never expressed.
- Voice/tone should reflect the era and documented personality from the
  source material, not a generic "old-timey" affect.
- This is a simulation for educational/creative purposes — the UI (not every
  message) should carry a disclaimer that this is an AI simulation based on
  public writings, not the real person's actual views.

## Constraints / preferences

- Budget-conscious: no paid vector DB, no unnecessary API calls while testing.
  Use small/mock data during development; only call the real Claude API to
  test end-to-end behavior once the pipeline logic is verified with print
  statements / dummy data.
- Prefer well-known, boring, documented libraries over cutting-edge/obscure
  ones — this is a learning project, not a production system.
- When making multi-file changes, briefly state the plan before executing
  (equivalent of Plan Mode) so the person can follow along and learn.

## Current status

LLM provider: Ollama (local, llama3.2:3b) — fully offline, zero cost.
