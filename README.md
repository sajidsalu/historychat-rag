HistoryChat

Chat with an AI persona of a historical figure (currently: Einstein), grounded in real Wikipedia content via RAG (Retrieval-Augmented Generation), running entirely locally and free (Ollama for the LLM, sentence-transformers for embeddings).

AI simulation for educational purposes — not the real person's actual views.

How it works
Wikipedia article is fetched and cleaned (ingest.py)
Text is split into chunks and embedded locally with sentence-transformers (embed.py)
On each chat message, the most relevant chunks are retrieved via cosine similarity (retrieve.py)
Retrieved chunks + a persona system prompt are sent to a local LLM via Ollama, which replies in character (main.py)
Tech stack
Backend: FastAPI (Python)
Embeddings: sentence-transformers (all-MiniLM-L6-v2), runs locally, free
LLM: Ollama (llama3.2:1b or 3b), runs locally, free
Frontend: plain HTML/CSS/JS, no framework
Setup on a fresh machine
1. Prerequisites
Python 3.10+
Ollama installed
2. Clone and install
bash
git clone <your-repo-url>
cd historychat

python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt
3. Pull the local LLM
bash
ollama pull llama3.2:1b

(Use llama3.2:3b instead if your machine has more RAM to spare — better quality, slower.)

4. Start Ollama (if not already running as a service)
bash
ollama serve

Check it's up:

bash
curl http://localhost:11434
5. Prepare the data (first run only)
bash
python ingest.py     # fetches + cleans Wikipedia article
python embed.py       # chunks + embeds it locally

This creates data/einstein/wikipedia.txt and data/einstein/chunks.json. Only needs to be re-run if you add a new figure or change the source text.

6. Run the app
bash
uvicorn main:app --reload

If port 8000 is already in use:

bash
uvicorn main:app --reload --port 8001
7. Open it

Visit http://localhost:8000 (or whichever port you used), pick a figure, and start chatting.

Notes
No API keys required — everything runs locally, zero cost.
First response after starting Ollama may be slow (model loads into memory).
Currently only "Einstein" has data. To add another figure, re-run ingest.py/embed.py with a different Wikipedia page and add it to the frontend dropdown.
Project status / roadmap

See .cursorrules for current build status and architecture notes.

<img width="1452" height="1054" alt="Screenshot from 2026-07-27 15-16-41" src="https://github.com/user-attachments/assets/f545db6b-497c-4e8a-8add-a8a8733c1d1b" />
