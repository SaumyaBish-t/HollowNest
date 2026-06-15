<div align="center">

# 🕸️ HollowNest

### *your AI workspace — patient, quiet, here.*

An autonomous, multi-model AI workspace that reads files, writes code, runs commands, browses the web, sends emails, opens GitHub issues — and streams every step back to you in real time.

🌐 **Live demo:** [hollow-nest.vercel.app](https://hollow-nest.vercel.app) *(Render free tier — first request after idle takes ~50s to wake)*

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=next.js&logoColor=white)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-336791?logo=postgresql&logoColor=white)](https://neon.tech/)
[![Clerk](https://img.shields.io/badge/Auth-Clerk-6C47FF?logo=clerk&logoColor=white)](https://clerk.com/)
[![Tailwind](https://img.shields.io/badge/Tailwind-4-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![MCP](https://img.shields.io/badge/Model%20Context%20Protocol-17+%20tools-c8c8dc)](https://modelcontextprotocol.io/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

</div>

---

## ✨ What it is

HollowNest is a full-stack AI workspace that wraps a custom agentic loop, the **Model Context Protocol (MCP)**, and a unified abstraction over **8 LLM providers** behind a dark, ethereal interface inspired by the *Void Whisper* design system.

You type or speak a task — *"scan this repo and open a GitHub issue for the worst bug,"* *"add input validation to the login form,"* *"summarise this PDF and send the result to my email"* — and the agent autonomously plans, calls tools, and streams its reasoning + every tool invocation back to you live.

## 🌟 Highlights

- **17+ MCP tools** — filesystem ops, surgical file edits, regex/semantic search, GitHub, Notion, Slack, web search, email, plan tracker, parallel subtasks, and more
- **8 LLM providers** under one BYOK roof — **Anthropic · OpenAI · NVIDIA NIM · Groq · Cerebras · OpenRouter · Qwen · Ollama Cloud** — with automatic key rotation across pasted keys
- **Real-time SSE streaming** of LLM tokens, tool calls, and tool results to the UI
- **Voice-driven workflows** — Groq Whisper for speech-to-text, browser `SpeechSynthesis` for replies, per-message playback controls
- **Agentic loop** with up to 10 tool iterations, parallel subtask execution, and a tier-based fallback chain on NVIDIA NIM
- **Real authentication via Clerk** — email + OAuth, with the backend verifying every request against Clerk's JWKS. All sessions, messages, and API keys are scoped per user
- **Session persistence** in Neon Postgres via async SQLAlchemy — every message and tool call recorded under the signed-in user's id
- **Local keyless embeddings** — FAISS over [`fastembed`](https://github.com/qdrant/fastembed) (`BAAI/bge-small-en-v1.5`, ONNX, 384-dim). No third-party API key, no torch
- **DuckDuckGo fallback** for web search — Tavily when a key is provided, otherwise free `ddgs` search
- **Zero-infra BYOK architecture** — users bring their own LLM keys, scoped to their Clerk user id in `localStorage`; the server never persists them

## 🖼️ Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI · async SQLAlchemy · asyncpg · Pydantic v2 · PyJWT |
| Frontend | Next.js 16 (App Router) · React 19 · TypeScript 5 · Tailwind CSS 4 · shadcn/ui · framer-motion |
| Streaming | Server-Sent Events |
| Database | Neon Postgres (serverless) |
| Auth | Clerk (JWKS-verified Bearer tokens on every backend call) |
| Embeddings | `fastembed` / `BAAI/bge-small-en-v1.5` (local, keyless) |
| Vector store | FAISS (`IndexFlatL2`, 384-dim) |
| Voice | Groq Whisper (`whisper-large-v3-turbo`) + browser `SpeechSynthesis` |
| Deployment | Render (backend, Docker) · Vercel (frontend) · Neon (DB) |

## 🧰 Tool catalog

**Built-in (no extra credentials)** — `read_file` · `write_file` · `edit_file` · `list_files` · `get_file_tree` · `regex_search` · `run_command` · `fetch_url` · `semantic_search` · `index_workspace` · `plan_tool` · `run_parallel_subtasks`

**External (connect once in Tool Store)** — `web_search` (Tavily, with DuckDuckGo fallback) · `github_tool` (incl. `create_repo`) · `send_email` (Brevo) · `notion_tool` · `slack_tool` · `query_database` (any Postgres URL)

> `screenshot_url` and `image_describe` were removed when the backend was retargeted to a slim image: vision is handled natively by the LLM providers, and Playwright was dropped to fit Render's 512MB free tier.

## 🤖 Models

The model selector is grouped by provider; click a key icon on any provider row to paste an API key and unlock its models.

| Provider | Recommended models |
|---|---|
| **Groq** | `openai/gpt-oss-120b` · `openai/gpt-oss-20b` · `llama-3.3-70b-versatile` |
| **Cerebras** | `gpt-oss-120b` · `qwen-3-coder-480b` · `zai-glm-4.7` |
| **NVIDIA NIM** | `openai/gpt-oss-120b` · `minimaxai/minimax-m2.7` · `qwen/qwen3-coder-480b-a35b-instruct` · `stepfun-ai/step-3.5-flash` |
| **OpenRouter** | `anthropic/claude-sonnet-4-5` · `openai/gpt-5` · `qwen/qwen3-coder` |
| **OpenAI** | `gpt-5` · `gpt-5-mini` · `gpt-4o` |
| **Anthropic** | `claude-opus-4-5` · `claude-sonnet-4-5` · `claude-haiku-4-5` |
| **Qwen** | `qwen3-coder-plus` · `qwen-max` · `qwen-plus` |
| **Ollama Cloud** | `gpt-oss:120b-cloud` · `deepseek-v3.1:671b-cloud` · `qwen3-coder:480b-cloud` · `kimi-k2:1t-cloud` |

## 🚀 Quick start

### Prerequisites
- Python **3.11+**
- Node **20+**
- A Neon Postgres database (free tier: [neon.tech](https://neon.tech/))
- A Clerk application (free tier: [clerk.com](https://clerk.com/))
- At least one LLM provider API key (Cerebras, Groq, or Ollama Cloud all have generous free tiers)

### 1. Clone

```bash
git clone https://github.com/SaumyaBish-t/HollowNest.git
cd HollowNest
```

### 2. Backend

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt

# Configure environment
cp .env.example .env       # then edit .env with DATABASE_URL + CLERK_JWT_ISSUER

# Initialise / migrate the database (idempotent)
python init_db.py

# Launch
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

> **Local dev without Clerk:** set `CLERK_DISABLE_AUTH=true` in `backend/.env`. Every request is then treated as a single pseudo user. Never enable in production.

### 3. Frontend

```bash
cd frontend/frontend                # double-nested by scaffold convention
npm install
cp .env.example .env.local          # then fill the Clerk + API URL values
npm run dev
```

Open **http://localhost:3000** and start whispering.

## 🔑 Environment variables

### `backend/.env`

```env
# Database (Neon Postgres) — required
DATABASE_URL=postgresql+asyncpg://user:pass@ep-xxx.region.aws.neon.tech/neondb?sslmode=require

# Clerk auth — required in production
CLERK_JWT_ISSUER=https://your-app.clerk.accounts.dev
CLERK_DISABLE_AUTH=false    # set true only for local dev

# CORS — comma-separated; *.vercel.app is auto-allowed
CORS_ORIGINS=https://your-app.vercel.app

# Optional tool credentials — when set, server-side fallback for these tools
TAVILY_API_KEY=             # otherwise web_search uses DuckDuckGo
BREVO_API_KEY=              # send_email
BREVO_SENDER_EMAIL=
BREVO_SENDER_NAME=

# Workspace where the agent reads/writes files
WORKSPACE_DIR=/tmp/agent_workspace

# Embedding cache (set in Docker / Render automatically)
HF_HOME=/tmp/hf_cache
FASTEMBED_CACHE_PATH=/tmp/hf_cache/fastembed
```

> **LLM provider keys (Groq, Anthropic, OpenAI, Cerebras, NVIDIA, OpenRouter, Qwen, Ollama) are BYOK only.** Users paste them in the model selector; the server has no fallback. Same for GitHub, Notion, Slack, Database Query — connected per-user from the Tool Store.

### `frontend/frontend/.env.local`

```env
NEXT_PUBLIC_API_URL=http://localhost:8000

NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxx
CLERK_SECRET_KEY=sk_test_xxx
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL=/
NEXT_PUBLIC_CLERK_SIGN_UP_FALLBACK_REDIRECT_URL=/
```

## 🏗️ Architecture

```
┌──────────────────────────┐                       ┌─────────────────────────────┐
│  Next.js frontend        │      SSE stream       │  FastAPI backend            │
│  • Sign-in via Clerk     │ ◀───────────────────▶ │  • require_user dependency  │
│  • Chat UI + voice       │                       │  • Agent orchestrator       │
│  • Model + key picker    │ ─ POST /agent/run ──▶ │  • LLM client (8 providers) │
│  • Tool activity feed    │   Authorization:      │  • MCP tool executor        │
│  • Per-message TTS/copy  │   Bearer <Clerk JWT>  │  • SQLAlchemy → Neon        │
└──────────────────────────┘                       └─────────────────────────────┘
                                                            │
                                                            │ FAISS index + local
                                                            ▼ fastembed embeddings
                                                ┌────────────────────────┐
                                                │  Workspace search       │
                                                │  (.nexus/search_index)  │
                                                └────────────────────────┘
```

### Agent loop

1. Frontend attaches `Authorization: Bearer <jwt>` to every request.
2. Backend verifies the JWT against Clerk's JWKS and resolves `user_id` (`require_user` FastAPI dep).
3. User message is persisted under that `user_id`.
4. LLM is called with the system prompt, the user's conversation history, and the curated MCP tool schema.
5. Tool calls are executed, streamed as `tool_start` / `tool_result` events, and appended to the conversation.
6. Loop ≤ 10 iterations.

### Security model

| | Storage | Scope |
|---|---|---|
| Clerk session JWT | HttpOnly cookie + memory | per browser tab |
| User's LLM provider keys | `localStorage` under `u:<clerkUserId>:apikey_<provider>` | per Clerk user |
| Server-side tool keys (Tavily, Brevo) | `.env` on the backend host | shared / optional |
| Chat sessions | Neon Postgres, `WHERE user_id = :clerk_user` on every query | per Clerk user |

## 📐 Design — *Void Whisper*

The UI is themed in the **Void Whisper** design language: deep void palette (`#07070f → #16162a`), silken silver accent (`#c8c8dc`), drifting moth particles, soul-pulse animations. Every component uses semantic Tailwind tokens mapped to CSS custom properties, so themes can be swapped by editing one block in [`globals.css`](frontend/frontend/src/app/globals.css).

## 🚢 Deploy

Production stack: **Neon Postgres** + **Render** (backend) + **Vercel** (frontend) + **Clerk** (auth). Step-by-step instructions, env-var tables, and a smoke-test checklist live in [`DEPLOYMENT.md`](DEPLOYMENT.md).

## 🗂️ Project structure

```
HollowNest/
├── backend/                       FastAPI service
│   ├── app/
│   │   ├── agent/                 orchestrator + LLM client + MCP tools
│   │   ├── routers/               /agent · /sessions · /uploads · /voice
│   │   ├── services/              FAISS code search, fastembed embeddings
│   │   ├── auth.py                Clerk JWT verifier + require_user dep
│   │   ├── config.py              provider catalogue + settings
│   │   ├── database.py            async SQLAlchemy engine
│   │   └── models.py              Session / Message / ToolCall
│   ├── init_db.py                 idempotent table + ALTER migrations
│   ├── Dockerfile                 python:3.11-slim + fastembed bake-in
│   ├── render.yaml                Render blueprint
│   └── requirements.txt
└── frontend/
    └── frontend/                  Next.js 16 app
        ├── src/
        │   ├── app/               layout + ClerkProvider + sign-in / sign-up
        │   ├── components/        ChatPanel, SessionSidebar, ToolStore, ...
        │   ├── hooks/             useVoiceRecorder, useTextToSpeech
        │   └── lib/               api.ts (authedFetch), keys.ts (scoped BYOK)
        ├── src/proxy.ts           Clerk middleware
        └── package.json
```

## 🛣️ Roadmap

- [ ] Task router — classify each message and auto-pick the right model
- [ ] Diff viewer for `write_file` / `edit_file`
- [ ] Workspace upload / zip download
- [ ] Cost + token tracker per session
- [ ] Agent memory scratchpad shared across runs
- [ ] One-click deploy buttons (Render · Vercel)
- [ ] Bring `screenshot_url` back behind a paid tier with Playwright

## 🤝 Contributing

PRs and issues welcome. Please open an issue first for anything non-trivial so we can align on direction.

## 📄 License

MIT — see [`LICENSE`](LICENSE).

---

<div align="center">

Built with care by **[Saumya Bisht](https://github.com/SaumyaBish-t)**
</div>
