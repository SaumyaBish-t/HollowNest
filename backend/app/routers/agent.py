from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Session, Message, ToolCall
from app.schemas import RunAgentRequest
from app.agent.orchestrator import run_agent
from app.agent.mcp_client import TOOL_METADATA, get_filtered_tools
from app.auth import require_user
from app.config import PROVIDERS, settings, get_user_keys
import json
import uuid
import traceback

router = APIRouter(prefix="/agent", tags=["agent"])


@router.get("/providers")
def get_providers():
    """
    Returns all supported providers and their models.
    This is a BYOK deployment — users must paste their own API key for each
    provider in the model selector. The server never falls back to a shared key.
    """
    return {
        key: {
            "label": cfg["label"],
            "models": cfg["models"],
            "has_env_key": False,
        }
        for key, cfg in PROVIDERS.items()
    }


@router.get("/tools")
def get_tools():
    """
    Returns metadata for all available tools.
    The frontend uses this to render the Tool Store.
    """
    return TOOL_METADATA


@router.post("/run")
async def run_agent_endpoint(
    req: RunAgentRequest,
    request: Request,
    user_id: str = Depends(require_user),
):
    # ── 1. Extract user-provided API keys from request header ──────────────
    user_keys = get_user_keys(request)

    provider = req.provider

    # Resolve API key: user's own key first, then fall back to server .env
    cfg = PROVIDERS.get(provider)
    if not cfg:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{provider}'.")

    # BYOK only — no server-side LLM key fallback.
    api_key = user_keys.get(provider, "")

    if not api_key:
        raise HTTPException(
            status_code=400,
            detail=(
                f"API key for the provider \"{cfg['label']}\" is not set. "
                f"Open the model selector, click the key icon on the "
                f"\"{cfg['label']}\" row, and paste your API key."
            ),
        )

    # ── 2. Try to connect to DB (gracefully optional) ──────────────────────
    db_available = True
    session = None
    history = []
    session_id = req.session_id or str(uuid.uuid4())
    model = req.model or cfg["models"][0]

    try:
        async with AsyncSessionLocal() as db:
            if req.session_id:
                result = await db.execute(
                    select(Session).where(
                        Session.id == req.session_id,
                        Session.user_id == user_id,
                    )
                )
                session = result.scalar_one_or_none()
                if session:
                    session_id = session.id
                    model = req.model or session.model

            if not session:
                session = Session(provider=provider, model=model, user_id=user_id)
                db.add(session)
                await db.commit()
                await db.refresh(session)
                session_id = session.id

            # ── 3. Load existing conversation history from DB ──────────────
            result = await db.execute(
                select(Message)
                .where(Message.session_id == session.id)
                .order_by(Message.created_at)
            )
            db_messages = result.scalars().all()

            # Rebuild OpenAI-format message list
            for m in db_messages:
                if m.role == "user":
                    msg = {"role": "user", "content": m.content}
                    if m.attachments:
                        msg["attachments"] = m.attachments
                    history.append(msg)
                elif m.role == "assistant":
                    msg: dict = {"role": "assistant", "content": m.content}
                    if m.tool_calls_data:
                        msg["tool_calls"] = m.tool_calls_data
                    history.append(msg)
                elif m.role == "tool":
                    history.append({
                        "role": "tool",
                        "tool_call_id": m.tool_call_id,
                        "content": m.content,
                    })

            # ── 4. Persist the incoming user message ──────────────────────
            user_msg = Message(
                session_id=session.id,
                role="user",
                content=req.message,
                attachments=req.attachments,
            )
            db.add(user_msg)
            await db.commit()

            # ── 5. Auto-title session on first message ────────────────────
            if not db_messages:
                session.title = req.message[:60] + ("…" if len(req.message) > 60 else "")
                await db.commit()

    except Exception as e:
        print(f"[Agent] DB error during setup, continuing without persistence: {e}")
        traceback.print_exc()
        db_available = False
        history = []

    # ── 6. Filter tools based on what the user has connected ──────────────
    enabled_tools = list(req.enabled_tools or [])
    if (
        settings.brevo_api_key
        and settings.brevo_sender_email
        and "send_email" not in enabled_tools
    ):
        enabled_tools.append("send_email")
    # GitHub tool: make it available whenever a token exists (server .env or
    # user-provided), so repo/issue/PR actions work without manually
    # connecting it in the Tool Store.
    if (
        (settings.github_token or user_keys.get("github"))
        and "github_tool" not in enabled_tools
    ):
        enabled_tools.append("github_tool")
    if (
        (settings.notion_api_key or user_keys.get("notion"))
        and "notion_tool" not in enabled_tools
    ):
        enabled_tools.append("notion_tool")
    if (
        (settings.slack_webhook_url or user_keys.get("slack_webhook"))
        and "slack_tool" not in enabled_tools
    ):
        enabled_tools.append("slack_tool")
    filtered_tools = get_filtered_tools(enabled_tools)
    lower_message = req.message.lower()
    email_intent = "email" in lower_message or "mail" in lower_message
    needs_workspace_tools = any(
        word in lower_message
        for word in ("file", "code", "test", "build", "run", "debug", "workspace", "project folder")
    )
    if email_intent and not needs_workspace_tools:
        email_tools = [
            tool for tool in filtered_tools
            if tool["function"]["name"] == "send_email"
        ]
        if email_tools:
            filtered_tools = email_tools

    # ── 7. Collectors for persisting the assistant turn ───────────────────
    assistant_text_parts: list[str] = []
    tool_call_log: list[dict] = []

    async def on_tool_call(name: str, args: dict, result: str):
        tool_call_log.append({
            "id": str(uuid.uuid4()),
            "name": name,
            "args": args,
            "result": result,
        })

    # ── 8. SSE stream ─────────────────────────────────────────────────────
    async def event_stream():
        # Send session_id first so the frontend can store it for follow-up turns
        yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id})}\n\n"

        async for event in run_agent(
            user_message=req.message,
            session_history=history,
            provider=provider,
            model=model,
            api_key=api_key,
            user_keys=user_keys,
            on_tool_call=on_tool_call,
            tools=filtered_tools,
            workspace_path=req.workspace_path,
            attachments=req.attachments,
        ):
            if event["type"] == "text":
                assistant_text_parts.append(event["content"])
            yield f"data: {json.dumps(event)}\n\n"

        # ── 9. Persist assistant turn after stream ends (only if DB is up) ─
        if db_available:
            try:
                full_text = "".join(assistant_text_parts)

                async with AsyncSessionLocal() as db:
                    asst_msg = Message(
                        session_id=session_id,
                        role="assistant",
                        content=full_text if full_text else None,
                    )
                    db.add(asst_msg)
                    await db.flush()

                    for tc in tool_call_log:
                        db.add(ToolCall(
                            message_id=asst_msg.id,
                            tool_name=tc["name"],
                            tool_input=tc["args"],
                            tool_output=tc["result"][:2000],
                        ))

                    await db.commit()
            except Exception as e:
                print(f"[Agent] Failed to persist response to DB: {e}")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
