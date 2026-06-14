export const PROVIDER_LABELS: Record<string, string> = {
  qwen: "Qwen (DashScope)",
  groq: "Groq",
  cerebras: "Cerebras",
  openrouter: "OpenRouter",
  openai: "OpenAI",
  anthropic: "Anthropic Claude",
  nvidia: "NVIDIA NIM",
  ollama: "Ollama Cloud",
}

export const PROVIDER_KEY_LINKS: Record<string, string> = {
  qwen: "https://dashscope.aliyuncs.com",
  groq: "https://console.groq.com/keys",
  cerebras: "https://cloud.cerebras.ai",
  openrouter: "https://openrouter.ai/keys",
  openai: "https://platform.openai.com/api-keys",
  anthropic: "https://console.anthropic.com/keys",
  nvidia: "https://build.nvidia.com",
  ollama: "https://ollama.com/settings/keys",
}

// ── API key storage ──────────────────────────────────────────────────────────

export function saveKey(provider: string, key: string): void {
  if (typeof window === "undefined") return
  if (key.trim()) {
    localStorage.setItem(`apikey_${provider}`, key.trim())
  } else {
    localStorage.removeItem(`apikey_${provider}`)
  }
}

export function getKey(provider: string): string {
  if (typeof window === "undefined") return ""
  return localStorage.getItem(`apikey_${provider}`) || ""
}

export function hasKey(provider: string): boolean {
  return getKey(provider).length > 0
}

export function getAllKeys(): Record<string, string> {
  if (typeof window === "undefined") return {}
  const keys: Record<string, string> = {}
  
  // Gather all provider keys
  Object.keys(PROVIDER_LABELS).forEach((p) => {
    const k = getKey(p)
    if (k) keys[p] = k
  })
  
  // Gather all tool credential keys
  let toolCredKeys: string[] = []
  try {
    toolCredKeys = JSON.parse(localStorage.getItem("tool_credential_keys") || "[]") as string[]
  } catch (e) {
    console.warn("Failed to parse tool_credential_keys", e)
  }

  toolCredKeys.forEach((credKey) => {
    const val = localStorage.getItem(`apikey_${credKey}`)
    if (val) keys[credKey] = val
  })

  return keys
}

export function getKeyHeader(): string {
  return JSON.stringify(getAllKeys())
}

// ── Tool connection tracking ─────────────────────────────────────────────────
// A tool is "connected" when the user has saved all required credentials for it.
// Connected tool IDs are stored in localStorage as a JSON array.

export function getConnectedTools(): string[] {
  if (typeof window === "undefined") return []
  try {
    return JSON.parse(localStorage.getItem("connected_tools") || "[]")
  } catch {
    return []
  }
}

export function connectTool(toolId: string): void {
  if (typeof window === "undefined") return
  const tools = getConnectedTools()
  if (!tools.includes(toolId)) {
    tools.push(toolId)
    localStorage.setItem("connected_tools", JSON.stringify(tools))
  }
}

export function disconnectTool(toolId: string): void {
  if (typeof window === "undefined") return
  const tools = getConnectedTools().filter((t) => t !== toolId)
  localStorage.setItem("connected_tools", JSON.stringify(tools))
}

export function isToolConnected(toolId: string): boolean {
  return getConnectedTools().includes(toolId)
}

/**
 * Save a tool credential key and track it for the X-API-Keys header.
 */
export function saveToolCredential(credentialKey: string, value: string): void {
  if (typeof window === "undefined") return
  saveKey(credentialKey, value)
  
  // Track which credential keys exist so getAllKeys can find them
  let tracked: string[] = []
  try {
    tracked = JSON.parse(localStorage.getItem("tool_credential_keys") || "[]") as string[]
  } catch (e) {
    console.warn("Failed to parse tool_credential_keys for tracking", e)
  }

  if (!tracked.includes(credentialKey)) {
    tracked.push(credentialKey)
    localStorage.setItem("tool_credential_keys", JSON.stringify(tracked))
  }
}

export function getToolCredential(credentialKey: string): string {
  return getKey(credentialKey)
}

// ── Workspace path persistence ───────────────────────────────────────────────

export function saveWorkspacePath(path: string): void {
  if (typeof window === "undefined") return
  if (path.trim()) {
    localStorage.setItem("workspace_path", path.trim())
  } else {
    localStorage.removeItem("workspace_path")
  }
}

export function getWorkspacePath(): string {
  if (typeof window === "undefined") return ""
  return localStorage.getItem("workspace_path") || ""
}