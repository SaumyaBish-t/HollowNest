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

// ── User-scoped localStorage ─────────────────────────────────────────────────
// All keys, tool credentials, connected-tool lists, and workspace paths are
// stored under a per-Clerk-user prefix so two users sharing the same browser
// cannot see each other's keys.
//
// Scope is installed by NexusApp on mount once Clerk loads the current user.
// When no user is signed in (and before the scope is installed), every getter
// returns empty and every setter is a no-op — protected routes are already
// gated by Clerk middleware, so this is purely defense in depth.

let _userScope: string | null = null

export function setKeyUserScope(userId: string | null): void {
  _userScope = userId || null
}

function scopedKey(name: string): string | null {
  if (!_userScope) return null
  return `u:${_userScope}:${name}`
}

function readScoped(name: string): string | null {
  if (typeof window === "undefined") return null
  const k = scopedKey(name)
  if (!k) return null
  return localStorage.getItem(k)
}

function writeScoped(name: string, value: string | null): void {
  if (typeof window === "undefined") return
  const k = scopedKey(name)
  if (!k) return
  if (value === null) {
    localStorage.removeItem(k)
  } else {
    localStorage.setItem(k, value)
  }
}

// ── API key storage ──────────────────────────────────────────────────────────

export function saveKey(provider: string, key: string): void {
  const trimmed = key.trim()
  writeScoped(`apikey_${provider}`, trimmed ? trimmed : null)
}

export function getKey(provider: string): string {
  return readScoped(`apikey_${provider}`) || ""
}

export function hasKey(provider: string): boolean {
  return getKey(provider).length > 0
}

export function getAllKeys(): Record<string, string> {
  if (typeof window === "undefined" || !_userScope) return {}
  const keys: Record<string, string> = {}

  // Provider keys
  Object.keys(PROVIDER_LABELS).forEach((p) => {
    const k = getKey(p)
    if (k) keys[p] = k
  })

  // Tool credential keys
  let toolCredKeys: string[] = []
  try {
    toolCredKeys = JSON.parse(readScoped("tool_credential_keys") || "[]") as string[]
  } catch (e) {
    console.warn("Failed to parse tool_credential_keys", e)
  }

  toolCredKeys.forEach((credKey) => {
    const val = readScoped(`apikey_${credKey}`)
    if (val) keys[credKey] = val
  })

  return keys
}

export function getKeyHeader(): string {
  return JSON.stringify(getAllKeys())
}

// ── Tool connection tracking ─────────────────────────────────────────────────

export function getConnectedTools(): string[] {
  if (typeof window === "undefined" || !_userScope) return []
  try {
    return JSON.parse(readScoped("connected_tools") || "[]")
  } catch {
    return []
  }
}

export function connectTool(toolId: string): void {
  if (typeof window === "undefined" || !_userScope) return
  const tools = getConnectedTools()
  if (!tools.includes(toolId)) {
    tools.push(toolId)
    writeScoped("connected_tools", JSON.stringify(tools))
  }
}

export function disconnectTool(toolId: string): void {
  if (typeof window === "undefined" || !_userScope) return
  const tools = getConnectedTools().filter((t) => t !== toolId)
  writeScoped("connected_tools", JSON.stringify(tools))
}

export function isToolConnected(toolId: string): boolean {
  return getConnectedTools().includes(toolId)
}

/**
 * Save a tool credential key and track it for the X-API-Keys header.
 */
export function saveToolCredential(credentialKey: string, value: string): void {
  if (typeof window === "undefined" || !_userScope) return
  saveKey(credentialKey, value)

  let tracked: string[] = []
  try {
    tracked = JSON.parse(readScoped("tool_credential_keys") || "[]") as string[]
  } catch (e) {
    console.warn("Failed to parse tool_credential_keys for tracking", e)
  }

  if (!tracked.includes(credentialKey)) {
    tracked.push(credentialKey)
    writeScoped("tool_credential_keys", JSON.stringify(tracked))
  }
}

export function getToolCredential(credentialKey: string): string {
  return getKey(credentialKey)
}

// ── Workspace path persistence ───────────────────────────────────────────────

export function saveWorkspacePath(path: string): void {
  const trimmed = path.trim()
  writeScoped("workspace_path", trimmed ? trimmed : null)
}

export function getWorkspacePath(): string {
  return readScoped("workspace_path") || ""
}

// ── One-time migration of legacy un-scoped entries ───────────────────────────
// Old builds wrote `apikey_<provider>`, `connected_tools`, etc. directly to
// localStorage. The first time a Clerk user signs in on this browser we copy
// those un-scoped values into the user's scope, then delete the originals.
//
// Returns the number of entries migrated.

const LEGACY_PROVIDER_PREFIX = "apikey_"
const LEGACY_FLAT_KEYS = [
  "connected_tools",
  "tool_credential_keys",
  "workspace_path",
]

export function migrateLegacyKeysIntoScope(): number {
  if (typeof window === "undefined" || !_userScope) return 0
  let moved = 0

  // Move any apikey_* values that aren't already scoped (no "u:" prefix).
  for (let i = localStorage.length - 1; i >= 0; i--) {
    const rawKey = localStorage.key(i)
    if (!rawKey) continue
    if (rawKey.startsWith("u:")) continue
    if (!rawKey.startsWith(LEGACY_PROVIDER_PREFIX) && !LEGACY_FLAT_KEYS.includes(rawKey)) {
      continue
    }
    const value = localStorage.getItem(rawKey)
    if (value === null) continue

    const scoped = `u:${_userScope}:${rawKey}`
    // Don't overwrite a value the user already has in their scope.
    if (localStorage.getItem(scoped) === null) {
      localStorage.setItem(scoped, value)
      moved += 1
    }
    localStorage.removeItem(rawKey)
  }
  return moved
}
