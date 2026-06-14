# HollowNest Deployment Guide

Production stack: **Neon Postgres** (DB) + **Railway** (FastAPI backend, Docker) + **Vercel** (Next.js frontend).

Why this split: FastAPI streams SSE and runs Playwright — both unhappy on serverless. Railway/Render/Fly run long-lived containers. Vercel runs the frontend ideally.

---

## 0. Prerequisites

- GitHub account with this repo pushed
- Accounts: [Neon](https://neon.tech), [Railway](https://railway.app), [Vercel](https://vercel.com)
- At least one LLM provider key (Cerebras / Groq / Gemini = free tiers)

---

## 1. Database — Neon Postgres

1. neon.tech → **New Project**
2. Pick region nearest your Railway region
3. Copy the connection string. Neon gives `postgresql://...`. You must convert it to:
   ```
   postgresql+asyncpg://USER:PASS@HOST/DB?sslmode=require
   ```
   Replace `postgresql://` with `postgresql+asyncpg://`. Keep `sslmode=require`.
4. Save it — that's your `DATABASE_URL`.

---

## 2. Backend — Railway

### 2.1 Create service

1. railway.app → **New Project** → **Deploy from GitHub repo**
2. Pick `HollowNest`
3. Settings → **Root Directory** = `backend`
4. Builder auto-detects the `Dockerfile` (already wired)

### 2.2 Environment variables

Settings → **Variables** → paste from `backend/.env.example`:

| Key | Value |
|---|---|
| `DATABASE_URL` | the Neon URL from step 1 |
| `WORKSPACE_DIR` | `/tmp/agent_workspace` |
| `CORS_ORIGINS` | (leave blank for now — fill after Vercel) |
| `GROQ_API_KEY` etc. | your provider keys |
| `TAVILY_API_KEY`, `GITHUB_TOKEN`, `BREVO_API_KEY`, `NOTION_API_KEY`, `SLACK_WEBHOOK_URL` | optional |
| `DEFAULT_PROVIDER` | `qwen` (or whichever you prefer) |

Railway injects `PORT` automatically — do NOT set it.

### 2.3 Deploy

- Push to `main` → Railway builds & deploys
- First build takes ~5 min (Playwright image is fat)
- Settings → **Networking** → **Generate Domain** → copy URL (e.g. `https://hollownest-production.up.railway.app`)
- Verify: `curl https://<url>/health` → `{"status":"ok"}`
- DB tables created automatically on boot (`python init_db.py` in the start command)

---

## 3. Frontend — Vercel

### 3.1 Import project

1. vercel.com → **Add New → Project** → import the GitHub repo
2. **Root Directory** = `frontend/frontend`
3. Framework Preset: Next.js (auto-detected)
4. Build Command: `npm run build` (default)
5. Output Directory: leave blank

### 3.2 Environment variable

Settings → **Environment Variables**:

| Key | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://<your-railway-url>` (no trailing slash) |

Apply to Production + Preview + Development.

### 3.3 Deploy

- Click **Deploy**. ~2 min build.
- Copy the Vercel URL (e.g. `https://hollownest.vercel.app`)

---

## 4. Wire CORS

Vercel `*.vercel.app` is already allowed by regex in `app/main.py`. If you attach a **custom domain**:

1. Railway → backend service → Variables
2. `CORS_ORIGINS` = `https://yourdomain.com,https://www.yourdomain.com`
3. Redeploy

---

## 5. Smoke test

1. Open the Vercel URL
2. Click the model selector → paste a provider API key (or rely on server keys)
3. Send: *"list files in workspace"* → tool call streams, result shows
4. Try `screenshot_url` on `https://example.com` — confirms Playwright works
5. Open a session, refresh page → session persists (Neon working)

---

## 6. Common issues

| Symptom | Fix |
|---|---|
| `connection refused` to backend | `NEXT_PUBLIC_API_URL` wrong or missing `https://` |
| CORS error in browser console | Add Vercel domain to `CORS_ORIGINS`, redeploy backend |
| `init_db.py` errors on boot | `DATABASE_URL` missing `+asyncpg` prefix or `sslmode=require` |
| Playwright `Executable doesn't exist` | You changed Dockerfile base image — keep `mcr.microsoft.com/playwright/python` |
| SSE stream cuts at 60s | You deployed backend to Vercel/Netlify (don't) — use Railway/Render/Fly |
| Files written by agent vanish | `WORKSPACE_DIR=/tmp/...` is ephemeral; attach Railway Volume mounted at `/data` and set `WORKSPACE_DIR=/data/workspace` |

---

## 7. Alternatives

- **Render**: same Dockerfile works. New Web Service → Docker → root `backend` → add env vars. Health check `/health`.
- **Fly.io**: `fly launch` from `backend/`. Bigger image needs `[mounts]` or a paid VM tier (Playwright = >1GB).
- **Self-host VPS**: `docker build -t hollownest-api backend/ && docker run -p 8000:8000 --env-file backend/.env hollownest-api`. Frontend: `npm run build && npm start` behind nginx.

---

## 8. Cost (free tier)

- Neon: 0.5 GB free, sleeps after inactivity
- Railway: $5 free credit / month — Playwright image eats ~1.5 GB so plan for ~$5–10/mo if always-on
- Vercel: free hobby plan covers this

For zero-cost: swap Railway for **Render free tier** (sleeps after 15 min idle, slow cold start) or run backend on your own machine + tunnel via `cloudflared`.
