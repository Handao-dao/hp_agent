# Text Annotation Framework

A small reference framework for turning arbitrary text into structured, clickable annotations.

This project is intentionally separate from the existing reading-helper app. It extracts the reusable architecture:

- schema models for documents, chunks, annotations, and results
- profile-driven prompt construction
- a generic annotation engine
- chunking and streaming events for long text
- a Vue reference app with a generic annotated-text renderer

## Quick Start

Backend:

```bash
cd backend
uv sync
uv run uvicorn text_annotation_framework.api:app --reload --port 8010
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5174
```

The backend uses a deterministic mock annotator when no LLM key is configured, so the demo works offline.

## Optional Real LLM

Set these environment variables before starting the backend:

```env
LLM_API_KEY=sk-your-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_ID=gpt-4.1-mini
```

Any OpenAI-compatible chat-completions endpoint should work.

## Core API

- `GET /api/profiles`
- `POST /api/annotate`
- `POST /api/annotate-stream`

`POST /api/annotate` body:

```json
{
  "text": "The resilient system recovered after a timeout.",
  "profile": "english_reading",
  "options": {}
}
```

Result shape:

```json
{
  "original_text": "...",
  "annotated_text": "...",
  "annotations": [
    {
      "surface": "resilient",
      "label": "有韧性的",
      "type": "keyword",
      "context": "...",
      "start_index": 4,
      "end_index": 13,
      "metadata": {}
    }
  ],
  "metadata": {}
}
```
