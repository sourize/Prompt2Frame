# Prompt2Frame

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React-61DAFB?logo=react)](https://reactjs.org)
[![Manim](https://img.shields.io/badge/Engine-Manim-ecec4f?logo=python)](https://github.com/ManimCommunity/manim)
[![Groq](https://img.shields.io/badge/AI-Groq-f55036?logo=groq)](https://groq.com)

**Prompt2Frame** transforms natural language descriptions into 2D mathematical animations using AI-powered Manim code generation. Describe what you want in plain English—"a red circle morphing into a blue square"—and the system handles prompt enrichment, code generation, validation, rendering, and caching.

---

## Architecture

A separated frontend-backend architecture with an optional Vercel serverless proxy layer for secure Hugging Face Spaces access.

```
prompt2frame/
├── backend/                         # Python/FastAPI service
│   ├── src/
│   │   ├── app.py                   # FastAPI app, routes, middleware, CORS
│   │   ├── config.py                # Pydantic-validated settings (env)
│   │   ├── generator.py             # Groq LLM → Manim code generation
│   │   ├── executor.py              # Manim subprocess rendering + ffmpeg
│   │   ├── prompt_expander.py       # LLM-based prompt enrichment
│   │   ├── validation.py            # Input sanitization, code security
│   │   ├── cache.py                 # In-memory prompt + filesystem video cache
│   │   ├── rate_limiter.py          # Sliding-window per-IP rate limiting
│   │   ├── circuit_breaker.py       # Circuit breaker for Groq API
│   │   ├── errors.py                # Structured error responses w/ correlation IDs
│   │   ├── templates.py             # Static Manim templates + smart template functions
│   │   └── template_helpers.py      # Parameter extraction for template customization
│   ├── media/videos/                # Generated video storage
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/                        # React 18 + Vite + TypeScript
│   ├── api/                         # Vercel serverless proxy functions
│   │   ├── generate.js              # Proxies /generate with HF_TOKEN
│   │   └── media.js                 # Proxies video streams securely
│   └── src/
│       ├── components/              # Header, SearchInterface, SuggestedQuestions
│       ├── pages/Index.tsx          # Main page (particle bg, footer, header)
│       └── lib/                     # Utilities
│
└── README.md
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.10+, FastAPI, Manim Community v0.17.3, Groq SDK (llama-3.3-70b-versatile) |
| **Frontend** | React 18, Vite, TypeScript, Tailwind CSS, Framer Motion, shadcn/ui, TanStack Query |
| **Deployment** | Vercel (frontend + proxy), Hugging Face Spaces / Railway / Render (backend) |
| **Infrastructure** | FFmpeg, uvicorn, gunicorn, Docker |

## Key Features

- **AI Code Generation**: Groq-powered Manim code generation with multi-stage prompting (intent analysis → code generation), syntax validation via AST parsing, and a self-healing loop that feeds render errors back to the LLM
- **Self-Healing Pipeline**: If Manim rendering fails, the error + broken code are sent back to the LLM for automatic correction (up to 2 retries)
- **Two-Tier Caching**: In-memory LRU cache for prompt expansions (24h TTL, 100 entries) + filesystem video cache with metadata tracking (7-day TTL)
- **Smart Prompt Expansion**: Short prompts (<200 chars) are enriched with spatial/timing context via LLM; detailed prompts pass through unchanged
- **Security**: Input sanitization (null bytes, control chars), dangerous pattern blocking (file I/O, network, subprocess), code security validation before execution, IP spoofing protection (X-Forwarded-For takes last entry)
- **Resilience**: Circuit breaker for Groq API (5 failures → 60s cooldown), sliding-window rate limiting (5 req/min, 20 req/hr per IP), CPU/memory/concurrency resource guard
- **Animation Templates**: 13 pre-built Manim templates (bounce, pendulum, neural network, spiral, heart, etc.) with smart parameter extraction for color/shape customization
- **Secure Proxy**: Vercel serverless functions inject `Authorization: Bearer <HF_TOKEN>` server-side, never exposing tokens to the client

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- FFmpeg (in system PATH)
- Groq API key (free at https://console.groq.com)

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set GROQ_API_KEY, PORT=5000, ALLOWED_ORIGINS=http://localhost:5173
uvicorn src.app:app --reload --port 5000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
# Edit .env: set VITE_BACKEND_URL=http://localhost:5000
npm run dev
```

### Production (Vercel + Hugging Face Spaces)

1. Deploy backend to Hugging Faces Spaces (or Railway/Render)
2. Set `VITE_BACKEND_URL` to your HF Space URL in Vercel environment variables
3. If the Space is private, set `HF_TOKEN` in Vercel secrets
4. The `api/` proxy functions automatically attach the token to each request

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service status + docs link |
| `/health` | GET | Comprehensive health check (Groq, FFmpeg, disk, cache, circuit breaker) |
| `/ready` | GET | Kubernetes readiness probe (200 if operational, 503 otherwise) |
| `/metrics` | GET | App and system metrics (requests, CPU, memory, disk) |
| `/generate` | POST | Generate animation from prompt |
| `/media/videos/{path}` | GET | Static file serving for generated videos |

### POST /generate

```json
{
  "prompt": "A red circle transforming into a blue square",
  "quality": "m",
  "timeout": 150
}
```

Response:
```json
{
  "videoUrl": "/media/videos/<run_id>/output.mp4",
  "renderTime": 12.34,
  "codeLength": 892,
  "expandedPrompt": "...",
  "generationMethod": "ai"
}
```

## Known Constraints

- Free-tier HF Spaces: 0.1 CPU, 2 concurrent requests max, renders capped at 120s
- `FORCE_LOW_QUALITY=1` recommended for free-tier (480p, 15fps)
- LaTeX not installed — use `Text()` instead of `MathTex()`/`Tex()`
- Manim subprocess has a hard 120s timeout (configurable via `MANIM_TIMEOUT_SECONDS`)
