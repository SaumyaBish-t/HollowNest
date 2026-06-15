# HollowNest Deployment Guide

Production stack: **Neon Postgres** (DB) + **Railway** (FastAPI backend, Docker) + **Vercel** (Next.js frontend).

Why this split: FastAPI streams SSE and runs Playwright — both unhappy on serverless. Railway/Render/Fly run long-lived containers. Vercel runs the frontend ideally.

---

## 0. Prerequisites

- GitHub account with this repo pushed
- Accounts: [Neon](https://neon.tech), [Railway](https://railway.app), [Vercel](https://vercel.com), [Clerk](https://clerk.com)
- At least one LLM provider key (Cerebras / Groq / Gemini = free tiers)

---

## 1. Clerk — Authentication

1. [dashboard.clerk.com](https://dashboard.clerk.com) → **Create Application**. Pick the sign-in methods you want (Email, Google, GitHub, etc.).
2. **API Keys** tab → copy three values:
   - **Publishable key** → `pk_test_...` or `pk_live_...`
   - **Secret key** → `sk_test_...` or `sk_live_...`
   - **Frontend API URL** (under *Show JWT verification* → Issuer) → `https://your-app.clerk.accounts.dev`
3. Save them. They go into Vercel + Railway in the next steps.

---

## 2. Database — Neon Postgres

1. neon.tech → **New Project**
2. Pick region nearest your Railway region
3. Copy the connection string. Neon gives `postgresql://...`. You must convert it to:
   ```
   postgresql+asyncpg://USER:PASS@HOST/DB?sslmode=require
   ```
   Replace `postgresql://` with `postgresql+asyncpg://`. Keep `sslmode=require`.
4. Save it — that's your `DATABASE_URL`.

---

## 3. Backend — Railway

### 3.1 Create service

1. railway.app → **New Project** → **Deploy from GitHub repo**
2. Pick `HollowNest`
3. Settings → **Root Directory** = `backend`
4. Builder auto-detects the `Dockerfile` (already wired)

### 3.2 Environment variables

Settings → **Variables** → paste from `backend/.env.example`:

| Key | Value |
|---|---|
| `DATABASE_URL` | the Neon URL from step 2 |
| `WORKSPACE_DIR` | `/tmp/agent_workspace` |
| `CORS_ORIGINS` | (leave blank for now — fill after Vercel) |
| `CLERK_JWT_ISSUER` | Clerk Frontend API URL from step 1 |
| `TAVILY_API_KEY` (optional) | enables Tavily for `web_search`. Without it the tool falls back to DuckDuckGo (no key) |
| `BREVO_API_KEY`, `BREVO_SENDER_EMAIL` (optional) | enable the email tool |
| `DEFAULT_PROVIDER` | `qwen` (or whichever you prefer) |

> LLM provider keys (Groq, Anthropic, OpenAI, etc.) are **BYOK**. Users paste them in the UI; you do not set them server-side. Same for GitHub, Notion, Slack, Database Query — those are connected per-user from the Tool Store.

Railway injects `PORT` automatically — do NOT set it.

### 3.3 Deploy

- Push to `main` → Railway builds & deploys
- First build takes ~7 min (Playwright image + fastembed BGE model bake-in)
- Settings → **Networking** → **Generate Domain** → copy URL (e.g. `https://hollownest-production.up.railway.app`)
- Verify: `curl https://<url>/health` → `{"status":"ok"}`
- DB tables created automatically on boot (`python init_db.py` in the start command, idempotent `ALTER TABLE` migrations included)

---

## 4. Frontend — Vercel

### 4.1 Import project

1. vercel.com → **Add New → Project** → import the GitHub repo
2. **Root Directory** = `frontend/frontend`
3. Framework Preset: Next.js (auto-detected)
4. Build Command: `npm run build` (default)
5. Output Directory: leave blank

### 4.2 Environment variables

Settings → **Environment Variables**:

| Key | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://<your-railway-url>` (no trailing slash) |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Clerk publishable key from step 1 (`pk_...`) |
| `CLERK_SECRET_KEY` | Clerk secret key from step 1 (`sk_...`) |
| `NEXT_PUBLIC_CLERK_SIGN_IN_URL` | `/sign-in` |
| `NEXT_PUBLIC_CLERK_SIGN_UP_URL` | `/sign-up` |
| `NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL` | `/` |
| `NEXT_PUBLIC_CLERK_SIGN_UP_FALLBACK_REDIRECT_URL` | `/` |

Apply to Production + Preview + Development.

### 4.3 Deploy

- Click **Deploy**. ~2 min build.
- Copy the Vercel URL (e.g. `https://hollownest.vercel.app`)

---

## 5. Wire CORS + Clerk allowed origins

### 5.1 Backend CORS
Vercel `*.vercel.app` is already allowed by regex in `app/main.py`. If you attach a **custom domain**:

1. Railway → backend service → Variables
2. `CORS_ORIGINS` = `https://yourdomain.com,https://www.yourdomain.com`
3. Redeploy

### 5.2 Clerk allowed origins
Clerk's frontend SDK refuses to load from origins it doesn't know.

1. Clerk dashboard → **Configure** → **Domains**
2. Add your Vercel URL (and custom domain if any)
3. For production Clerk instance: create a separate **Production** application and swap to its `pk_live_...` / `sk_live_...` keys in Vercel + Railway

---

## 6. Smoke test

1. Open the Vercel URL → redirects to `/sign-in`
2. Sign up (or sign in with Google) → land on chat
3. Open model selector → paste a provider API key (e.g. Cerebras or Groq — both free)
4. Send: *"hi"* → short text reply, no tool storm
5. Send: *"list files in workspace"* → tool calls stream, results show on right panel
6. Open a session, refresh the page → session persists (Neon + Clerk auth survives hard refresh)
7. Sign out + sign in as a different account → previous user's keys / sessions hidden

---

## 7. Common issues

| Symptom | Fix |
|---|---|
| `connection refused` to backend | `NEXT_PUBLIC_API_URL` wrong or missing `https://` |
| `Missing Authorization: Bearer` 401 from backend | `CLERK_JWT_ISSUER` wrong on Railway. Must match the Frontend API URL of the same Clerk instance whose `pk_...` Vercel uses |
| Clerk SDK refuses to mount | Vercel URL not added to Clerk → Domains list |
| CORS error in browser console | Add Vercel / custom domain to `CORS_ORIGINS`, redeploy backend |
| `init_db.py` errors on boot | `DATABASE_URL` missing `+asyncpg` prefix or `sslmode=require` |
| `column "user_id" does not exist` on sessions | `init_db.py` didn't run — Railway start cmd already runs it on boot; if you migrated DB by hand, run `python init_db.py` once |
| Playwright `Executable doesn't exist` | You changed Dockerfile base image — keep `mcr.microsoft.com/playwright/python` |
| `web_search` says no Tavily key | Expected — falls back to DuckDuckGo automatically via `ddgs` |
| SSE stream cuts at 60s | You deployed backend to Vercel/Netlify (don't) — use Railway/Render/Fly |
| Files written by agent vanish | `WORKSPACE_DIR=/tmp/...` is ephemeral; attach Railway Volume mounted at `/data` and set `WORKSPACE_DIR=/data/workspace` |
| fastembed model re-downloads on every cold start | Confirm `HF_HOME=/tmp/hf_cache` in Dockerfile + Railway volume mounted at `/tmp` for persistence (optional, model is small) |

---

## 8. Alternatives

- **Render**: same Dockerfile works. New Web Service → Docker → root `backend` → add env vars. Health check `/health`.
- **Fly.io**: `fly launch` from `backend/`. Bigger image needs `[mounts]` or a paid VM tier (Playwright = >1GB).
- **Self-host VPS**: `docker build -t hollownest-api backend/ && docker run -p 8000:8000 --env-file backend/.env hollownest-api`. Frontend: `npm run build && npm start` behind nginx.

---

## 9. Cost (free tier)

- Neon: 0.5 GB free, sleeps after inactivity
- Railway: $5 free credit / month — Playwright image eats ~1.5 GB so plan for ~$5–10/mo if always-on
- Vercel: free hobby plan covers this
- Clerk: 10,000 monthly active users on free tier (more than enough for solo / hobby)

For zero-cost: swap Railway for **Render free tier** (sleeps after 15 min idle, slow cold start) or run backend on your own machine + tunnel via `cloudflared`.

---

## 10. Local dev quick start

```bash
# Backend
cd backend
python -m venv venv && venv\Scripts\activate    # or source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
copy .env.example .env                           # cp on macOS/Linux
# Fill DATABASE_URL + CLERK_JWT_ISSUER at minimum.
# For dev without Clerk: set CLERK_DISABLE_AUTH=true
python init_db.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Frontend (separate terminal)
cd frontend/frontend
npm install
copy .env.example .env.local                     # cp on macOS/Linux
# Fill NEXT_PUBLIC_API_URL=http://localhost:8000 + Clerk publishable/secret keys
npm run dev
```

Open http://localhost:3000.
