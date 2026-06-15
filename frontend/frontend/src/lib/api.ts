import { getKeyHeader } from "./keys";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Clerk token plumbing ─────────────────────────────────────────────────────
// The hosted frontend (Vercel) and the API (Railway) are cross-origin, so the
// Clerk session cookie is not sent automatically. The app sets a token getter
// once on mount via setAuthTokenGetter and every fetch attaches the JWT as a
// Bearer token. The backend verifies it with Clerk's JWKS.
type TokenGetter = () => Promise<string | null>;
let _tokenGetter: TokenGetter | null = null;

export function setAuthTokenGetter(fn: TokenGetter | null): void {
  _tokenGetter = fn;
}

async function authHeader(): Promise<Record<string, string>> {
  if (!_tokenGetter) return {};
  try {
    const token = await _tokenGetter();
    return token ? { Authorization: `Bearer ${token}` } : {};
  } catch {
    return {};
  }
}

async function authedFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const auth = await authHeader();
  return fetch(input, {
    ...init,
    headers: { ...(init.headers || {}), ...auth },
  });
}

export interface Session {
  id: string;
  title: string;
  provider: string;
  model: string;
  created_at: string;
  updated_at: string;
  messages?: Message[];
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "tool";
  content?: string;
  tool_call_id?: string;
  created_at: string;
  tool_calls: ToolCall[];
  attachments?: any[];
}

export interface ToolCall {
  id: string;
  tool_name: string;
  tool_input?: any;
  tool_output?: string;
  duration_ms?: number;
  created_at: string;
}

// ── Tool Store types ─────────────────────────────────────────────────────────
export interface ToolCredential {
  key: string;
  label: string;
  placeholder: string;
  link: string;
}

export interface ToolMetadata {
  name: string;
  description: string;
  category: "builtin" | "external";
  icon: string;
  credentials: ToolCredential[];
}

// ── API calls ────────────────────────────────────────────────────────────────

export async function getProviders(): Promise<Record<string, { label: string; models: string[]; has_env_key?: boolean }>> {
  const res = await authedFetch(`${API_BASE}/agent/providers`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch providers");
  return res.json();
}

export async function getToolsMetadata(): Promise<Record<string, ToolMetadata>> {
  const res = await authedFetch(`${API_BASE}/agent/tools`);
  if (!res.ok) throw new Error("Failed to fetch tools");
  return res.json();
}

export async function createSession(provider: string, model?: string): Promise<Session> {
  const res = await authedFetch(`${API_BASE}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider, model }),
  });
  if (!res.ok) throw new Error("Failed to create session");
  return res.json();
}

export async function getSessions(): Promise<Session[]> {
  const res = await authedFetch(`${API_BASE}/sessions`);
  if (!res.ok) throw new Error("Failed to fetch sessions");
  return res.json();
}

export async function getSession(id: string): Promise<Session> {
  const res = await authedFetch(`${API_BASE}/sessions/${id}`);
  if (!res.ok) throw new Error("Failed to fetch session");
  return res.json();
}

export async function deleteSession(id: string): Promise<void> {
  const res = await authedFetch(`${API_BASE}/sessions/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete session");
}

export async function updateSessionTitle(id: string, title: string): Promise<Session> {
  const res = await authedFetch(`${API_BASE}/sessions/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error("Failed to update session");
  return res.json();
}

export async function uploadFiles(files: File[]): Promise<{ files: any[] }> {
  const formData = new FormData();
  files.forEach(f => formData.append("files", f));
  
  const res = await authedFetch(`${API_BASE}/uploads`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error("Failed to upload files");
  return res.json();
}

export async function uploadCurrentScreenScreenshot(
  blob: Blob,
  filename = "current-screen.png"
): Promise<{ file: string; path: string; size_bytes: number }> {
  const formData = new FormData();
  formData.append("file", blob, filename);

  const res = await fetch(
    `${API_BASE}/uploads/current-screen?filename=${encodeURIComponent(filename)}`,
    {
      method: "POST",
      body: formData,
    }
  );
  if (!res.ok) throw new Error("Failed to upload current screen screenshot");
  return res.json();
}

export type AgentEvent =
  | { type: "session_id"; session_id: string }
  | { type: "text"; content: string }
  | { type: "tool_start"; name: string; args: any }
  | { type: "tool_result"; name: string; result: string }
  | { type: "done" }
  | { type: "error"; message: string };

export async function* streamAgentRun(params: {
  message: string;
  session_id?: string;
  provider: string;
  model: string;
  enabled_tools?: string[];
  workspace_path?: string;
  attachments?: any[];
}): AsyncGenerator<AgentEvent, void, unknown> {
  const res = await authedFetch(`${API_BASE}/agent/run`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Keys": getKeyHeader(),
    },
    body: JSON.stringify(params),
  });

  if (!res.ok) {
    throw new Error(`Failed to run agent: ${res.statusText}`);
  }

  if (!res.body) throw new Error("Response body is null");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const dataStr = line.slice(6).trim();
        if (!dataStr) continue;
        try {
          const event = JSON.parse(dataStr) as AgentEvent;
          yield event;
        } catch (e) {
          console.error("Failed to parse event:", dataStr, e);
        }
      }
    }
  }
}
