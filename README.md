<div align="center">

# 🕸️ HollowNest

### *your AI workspace — patient, quiet, here.*

An autonomous, multi-model AI workspace that reads files, writes code, runs commands, browses the web, sends emails, opens GitHub issues — and streams every step back to you in real time.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=next.js&logoColor=white)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-336791?logo=postgresql&logoColor=white)](https://neon.tech/)
[![Tailwind](https://img.shields.io/badge/Tailwind-4-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![MCP](https://img.shields.io/badge/Model%20Context%20Protocol-20+%20tools-c8c8dc)](https://modelcontextprotocol.io/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

</div>

---

## ✨ What it is

HollowNest is a full-stack AI workspace that wraps a custom agentic loop, the **Model Context Protocol (MCP)**, and a unified abstraction over **7 LLM providers** behind a dark, ethereal interface inspired by the *Void Whisper* design system.

You type or speak a task — *"scan this repo and open a GitHub issue for the worst bug,"* *"add input validation to the login form,"* *"summarise this PDF and send the result to my email"* — and the agent autonomously plans, calls tools, and streams its reasoning + every tool invocation back to you live.

## 🌟 Highlights

- **20+ MCP tools** — filesystem ops, surgical file edits, regex/semantic search, GitHub, Notion, Slack, vision (image description), screenshots, web search, email, plan tracker, and more
- **7 LLM providers** under one BYOK roof — **Anthropic · OpenAI · NVIDIA NIM · Groq · Cerebras · OpenRouter · Qwen** — with automatic key rotation across pasted keys
- **Real-time SSE streaming** of LLM tokens, tool calls, and tool results to the UI
- **Voice-driven workflows** — Groq Whisper for speech-to-text, browser `SpeechSynthesis` for replies, per-message playback controls
- **Agentic loop** with up to 10 tool iterations, parallel subtask execution, and a Tier-based fallback chain on NVIDIA NIM
- **Session persistence** in Neon Postgres via async SQLAlchemy — every message and tool call recorded
- **FAISS semantic code search** over the workspace with incremental re-indexing
- **Zero-infra BYOK architecture** — users bring their own API keys, stored only in `localStorage`; the server never touches them in storage

## 🖼️ Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI · async SQLAlchemy · asyncpg · Pydantic v2 |
| Frontend | Next.js 16 (App Router) · React · TypeScript · Tailwind CSS 4 · shadcn/ui · framer-motion |
| Streaming | Server-Sent Events (`sse-starlette`) |
| Database | Neon Postgres (serverless) |
| Vector search | FAISS + Gemini embeddings (text-embedding-004) |
| Voice | Groq Whisper (`whisper-large-v3-turbo`) + browser `SpeechSynthesis` |
| Web automation | Playwright (Chromium, headless) |
| Auth | None — BYOK keys act as the identity layer |

## 🧰 Tool catalog

**Built-in (always on)** — `read_file` · `write_file` · `edit_file` · `list_files` · `get_file_tree` · `regex_search` · `run_command` · `fetch_url` · `screenshot_url` · `query_database` · `lint_code` · `semantic_search` · `index_workspace` · `image_describe` · `plan_tool` · `run_parallel_subtasks`

**External (one key away)** — `web_search` (Tavily) · `github_tool` (incl. `create_repo`) · `send_email` (Brevo) · `notion_tool` · `slack_tool`

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

## 🚀 Quick start

### Prerequisites
- Python **3.11+**
- Node **20+**
- A Neon Postgres database (free tier: [neon.tech](https://neon.tech/))
- At least one LLM provider API key (Cerebras, Groq, or Gemini all have generous free tiers)

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
playwright install chromium

# Configure environment
cp .env.example .env       # then edit .env with your keys + DATABASE_URL

# Initialise the database (idempotent)
python init_db.py

# Launch
python -m uvicorn app.main:app --host 127.0.0.1 --port 8002
```

### 3. Frontend

```bash
cd frontend/frontend                # double-nested by scaffold convention
npm install
# point at the running backend
echo "NEXT_PUBLIC_API_URL=http://localhost:8002" > .env.local
npm run dev
```

Open **http://localhost:3000** and start whispering.

## 🔑 Environment variables (`backend/.env`)

```env
# Database (Neon Postgres) — required
DATABASE_URL=postgresql+asyncpg://user:pass@ep-xxx.region.aws.neon.tech/neondb

# LLM providers — fill at least one
GEMINI_API_KEY=
GROQ_API_KEY=
CEREBRAS_API_KEY=
NVIDIA_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
OPENROUTER_API_KEY=
DASHSCOPE_API_KEY=

# External tools — optional, each unlocks a tool
TAVILY_API_KEY=
GITHUB_TOKEN=
BREVO_API_KEY=
BREVO_SENDER_EMAIL=
NOTION_API_KEY=
SLACK_WEBHOOK_URL=

# Workspace where the agent reads/writes files
WORKSPACE_DIR=/tmp/agent_workspace
```

Any provider whose key sits in `.env` is **auto-activated** in the UI. Anything missing stays locked until the user pastes a key in the model dropdown's *Add key* panel.

## 🏗️ Architecture

```
┌──────────────────────────┐         SSE          ┌─────────────────────────────┐
│  Next.js frontend        │ ◀─── stream ────────▶│  FastAPI backend            │
│  • Chat UI + voice       │                       │  • Agent orchestrator      │
│  • Model + key picker    │ ── POST /agent/run ──▶│  • LLM client (7 providers)│
│  • Tool activity feed    │                       │  • MCP tool executor       │
│  • Per-message TTS/copy  │                       │  • SQLAlchemy → Neon       │
└──────────────────────────┘                       └─────────────────────────────┘
                                                            │
                                                            │ FAISS + Gemini embeddings
                                                            ▼
                                                ┌────────────────────────┐
                                                │  Local workspace index │
                                                └────────────────────────┘
```

The agent loop:

1. User message → backend persists it.
2. LLM is called with the system prompt, conversation history, and the curated MCP tool schema.
3. If the LLM returns text, it's streamed token-by-token to the frontend.
4. If the LLM returns a tool call, the backend executes the tool, streams a `tool_start` / `tool_result`, appends the result to the conversation, and loops back to step 2.
5. Hard cap at 10 iterations to prevent runaway loops.

## 📐 Design — *Void Whisper*

The UI is themed in the **Void Whisper** design language: deep void palette (`#07070f → #16162a`), silken silver accent (`#c8c8dc`), drifting moth particles, soul-pulse animations, and the hand-drawn *Amatic SC* display font. Every component uses semantic Tailwind tokens mapped to CSS custom properties, so themes can be swapped by editing one block in [`globals.css`](frontend/frontend/src/app/globals.css).

## 🗂️ Project structure

```
HollowNest/
├── backend/                    FastAPI service
│   ├── app/
│   │   ├── agent/              orchestrator + LLM client + MCP tools
│   │   ├── routers/            /agent · /sessions · /uploads · /voice
│   │   ├── services/           FAISS code search, embeddings
│   │   ├── config.py           provider catalogue + settings
│   │   ├── database.py         async SQLAlchemy engine
│   │   └── models.py           Session / Message / ToolCall
│   ├── init_db.py
│   └── requirements.txt
└── frontend/
    └── frontend/               Next.js 16 app
        ├── src/
        │   ├── app/            layout, globals.css (Void Whisper)
        │   ├── components/     ChatPanel, SessionSidebar, ToolStore,
        │   │                   ProviderSelector, ToolCallPanel, ...
        │   ├── hooks/          useVoiceRecorder, useTextToSpeech
        │   └── lib/            api.ts, keys.ts (BYOK storage)
        └── package.json
```

## 🛣️ Roadmap

- [ ] Task router — classify each message and auto-pick the right model
- [ ] Diff viewer for `write_file` / `edit_file`
- [ ] Workspace upload / zip download
- [ ] Cost + token tracker per session
- [ ] Agent memory scratchpad shared across runs
- [ ] One-click deploy buttons (Railway · Vercel)

## 🤝 Contributing

PRs and issues welcome. Please open an issue first for anything non-trivial so we can align on direction.

## 📄 License

MIT — see [`LICENSE`](LICENSE).

---

<div align="center">

Built with care by **[Saumya Bisht](https://github.com/SaumyaBish-t)**
</div>
