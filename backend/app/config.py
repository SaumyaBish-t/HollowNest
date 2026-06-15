import json
from fastapi import Request
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    dashscope_api_key: str = ""
    groq_api_key: str = ""
    gemini_api_key: str = ""
    mistral_api_key: str = ""
    openrouter_api_key: str = ""
    nvidia_api_key: str = ""
    cerebras_api_key: str = ""
    ollama_api_key: str = ""
    database_url: str = ""
    workspace_dir: str = "/tmp/agent_workspace"
    tavily_api_key: str = ""
    github_token: str = ""
    brevo_api_key: str = ""
    brevo_sender_email: str = ""
    brevo_sender_name: str = "NexusAI Agent"
    notion_api_key: str = ""
    slack_webhook_url: str = ""
    default_provider: str = "qwen"
    # Clerk auth. CLERK_JWT_ISSUER is the Frontend API URL of the Clerk
    # instance (e.g. https://your-app.clerk.accounts.dev). The backend
    # fetches {issuer}/.well-known/jwks.json to verify the JWT on every
    # protected request. CLERK_DISABLE_AUTH is a local-dev opt-out so the
    # backend can run without a Clerk app configured.
    clerk_jwt_issuer: str = ""
    clerk_disable_auth: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()


PROVIDERS = {
    "groq": {
        "label": "Groq",
        "models": [
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "llama-3.3-70b-versatile",
        ],
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "groq_api_key",
        "free": True,
        "free_note": "Generous daily limits; gpt-oss best for tool calls",
    },
    "cerebras": {
        "label": "Cerebras",
        "models": [
            "gpt-oss-120b",
            "qwen-3-coder-480b",
            "zai-glm-4.7",
        ],
        "base_url": "https://api.cerebras.ai/v1",
        "api_key_env": "cerebras_api_key",
        "free": True,
        "free_note": "Generous free tier, fastest inference available",
    },
    "nvidia": {
        "label": "NVIDIA NIM",
        "models": [
            "openai/gpt-oss-120b",                        # tool calling
            "minimaxai/minimax-m2.7",                     # coding
            "qwen/qwen3-coder-480b-a35b-instruct",        # coding
            "stepfun-ai/step-3.5-flash",                  # fast agentic
        ],
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key_env": "nvidia_api_key",
        "free": True,
        "free_note": "Free DGX-Cloud endpoints; no credit card",
        "strategy": {
            "primary": "openai/gpt-oss-120b",
            "fallback": "stepfun-ai/step-3.5-flash",
            "backup": "qwen/qwen3-coder-480b-a35b-instruct",
        },
    },
    "openrouter": {
        "label": "OpenRouter",
        "models": [
            "anthropic/claude-sonnet-4-5",
            "openai/gpt-5",
            "qwen/qwen3-coder",
        ],
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "openrouter_api_key",
        "free": True,
        "free_note": "Unified gateway across providers; pricing per-model",
    },
    "openai": {
        "label": "OpenAI",
        "models": ["gpt-5", "gpt-5-mini", "gpt-4o"],
        "base_url": None,
        "api_key_env": "openai_api_key",
        "free": False,
        "free_note": "$5 credit on signup, expires in 3 months",
    },
    "anthropic": {
        "label": "Anthropic Claude",
        "models": ["claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-4-5"],
        "base_url": None,
        "api_key_env": "anthropic_api_key",
        "free": False,
        "free_note": "Pay-as-you-go after phone verification",
    },
    "qwen": {
        "label": "Qwen (DashScope)",
        "models": ["qwen3-coder-plus", "qwen-max", "qwen-plus"],
        "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        "api_key_env": "dashscope_api_key",
        "free": False,
        "free_note": "Free tokens on signup, then paid",
    },
    "ollama": {
        "label": "Ollama Cloud",
        "models": [
            "gpt-oss:120b-cloud",
            "gpt-oss:20b-cloud",
            "deepseek-v3.1:671b-cloud",
            "qwen3-coder:480b-cloud",
            "kimi-k2:1t-cloud",
        ],
        "base_url": "https://ollama.com/v1",
        "api_key_env": "ollama_api_key",
        "free": True,
        "free_note": "Free hourly/daily Cloud quotas with Ollama account; OpenAI-compatible",
    },
}


def get_user_keys(request: Request) -> dict:
    """
    Extract user-provided API keys from the X-API-Keys request header.
    Falls back to server .env keys if the user hasn't provided one.
    This lets the app work for solo dev use (your own .env)
    and for all public users (their own keys, stored in their browser).
    """
    raw = request.headers.get("X-API-Keys", "{}")
    try:
        user_keys = json.loads(raw)
    except Exception:
        user_keys = {}
    return user_keys
