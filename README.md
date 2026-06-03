# TUTOR AI — React Edition

> Your intelligent SSC study companion — powered by your syllabus, running locally with Ollama.

---

## What changed from the original

| Area | Before | After |
|------|--------|-------|
| Frontend | Streamlit (Python) | **React 18** (JS) |
| Image upload | Broken — file bytes consumed before read | **Fixed** — `File` object passed directly to `FormData` |
| Image UI | Sidebar toggle → separate section | **Paperclip button** (📎) in input bar, just like Claude |
| Markdown | Plain text | **react-markdown** with GFM tables, code blocks |
| Subject switch | Required full page reload | Instant, no reload |
| Error handling | Streamlit overlay | Inline dismissible error banner |
| Future mobile | Not portable | **React** → React Native ready |

---

## Prerequisites

- **Python 3.11+**
- **Node.js 18+** and npm
- **Ollama** running locally:
  ```bash
  ollama pull qwen2.5:7b      # text questions
  ollama pull llava:7b         # image questions
  ```

---

## Setup

### 1. Backend .env
```bash
cp .env.example .env
# Edit API_SECRET_KEY to any long random string
```

### 2. Frontend .env
```bash
cd frontend
# Edit .env — set REACT_APP_API_KEY to same value as API_SECRET_KEY
npm install
```

---

## Running

**Terminal 1 — API:**
```bash
pip install -r requirements.txt
bash start_api.sh
# → http://localhost:8000
```

**Terminal 2 — Frontend:**
```bash
bash start_frontend.sh
# → http://localhost:3000
```

---

## Why image upload was broken

Streamlit's `UploadedFile` is a stream. After `st.image(uploaded_file)` rendered the preview, the read cursor was at EOF — so `uploaded_file.read()` returned empty bytes (0 bytes sent to the API).

**Fix:** React passes the raw `File` object directly to `FormData`. The browser reads it fresh each time, so the API always receives the full image.

---

## Image upload (how to use)

1. Click the **📎 paperclip** button in the input bar
2. Select a JPEG/PNG/WEBP/GIF (up to 10 MB)
3. Preview thumbnail appears; optionally type context
4. Press Enter or Send — goes to `/chat/image`

---

## Project Structure

```
tutor_ai_react/
├── api/            FastAPI backend (unchanged)
├── chat/           LLM responder + retriever (unchanged)
├── config/         settings + config.yaml (unchanged)
├── core/           session store, indexer (unchanged)
├── books/          SSC book data (unchanged)
├── frontend/       React app (NEW)
│   ├── src/
│   │   ├── App.js
│   │   ├── api.js
│   │   ├── index.css
│   │   └── components/
│   │       ├── Sidebar.js
│   │       ├── Message.js
│   │       └── ChatInput.js
│   └── public/index.html
├── start_api.sh
├── start_frontend.sh
└── requirements.txt
```
