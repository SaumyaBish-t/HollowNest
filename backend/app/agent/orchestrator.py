import asyncio
import json
from typing import AsyncGenerator, Callable, Optional
from app.agent.llm_client import stream_llm_response
from app.agent.mcp_client import MCP_TOOLS, execute_tool


SYSTEM_PROMPT = """You are an expert AI coding agent with access to tools that let \
you read files, write files, run shell commands, and fetch web content.

When given a task:
1. Start by exploring the workspace with list_files or read_file to understand context.
2. Break the task into clear steps and execute them one by one using tools.
3. After writing or modifying code, always verify with run_command (run tests, lint, etc).
4. Briefly explain your reasoning before each tool call so the user can follow along.
5. When finished, give a concise summary of every change you made and why.
6. If the user asks you to send an email, draft the subject and body yourself from
   the user's prompt and conversation context unless they explicitly provide exact
   wording. Match requested styles such as professional, friendly, concise,
   collaboration, follow-up, apology, sales, support, status update, or summary.
   Ask only for missing required delivery details such as the recipient address.
7. If the user asks you to scan code and create a GitHub issue, make the issue
   specific and actionable. Include the affected file path, line number or nearest
   function/component when available, evidence from the code, why it matters,
   and a suggested fix. Do not create vague issues.

Rules:
- Be precise. Never make changes unrelated to the task.
- If a command fails, read the error carefully and try to fix it before giving up.
- Never ask the user to run something yourself — use run_command to do it directly."""


async def run_agent(
    user_message: str,
    session_history: list,
    provider: str,
    model: str,
    api_key: str,
    user_keys: dict = None,
    on_tool_call: Optional[Callable] = None,
    tools: list = None,
    workspace_path: str = None,
    attachments: list = None,
) -> AsyncGenerator[dict, None]:
    """
    Core agentic loop. Streams events back to the API route.

    Yielded event types:
      {type: "text",         content: str}         LLM response tokens
      {type: "tool_start",   name: str, args: dict} Tool about to execute
      {type: "tool_result",  name: str, result: str} Tool output (truncated for UI)
      {type: "done"}                                 Agent finished
      {type: "error",        message: str}           Something went wrong
    """
    # Use provided tools list (filtered) or fall back to all tools
    active_tools = tools if tools is not None else MCP_TOOLS

    user_msg_dict = {"role": "user", "content": user_message}
    if attachments:
        user_msg_dict["attachments"] = attachments

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *session_history,
        user_msg_dict,
    ]

    MAX_ITERATIONS = 10
    iteration = 0

    while iteration < MAX_ITERATIONS:
        iteration += 1
        assistant_text = ""
        tool_calls_this_turn = []

        # Extract all keys for this provider to enable rotation
        key_pool = []
        # Support multiple keys in both user_keys (frontend) and api_key (env fallback)
        raw_keys = ""
        if user_keys and user_keys.get(provider):
            raw_keys = user_keys[provider]
        elif api_key:
            raw_keys = api_key
            
        if raw_keys:
            # Handle both newline and comma separation
            key_pool = [k.strip() for k in raw_keys.replace(",", "\n").split("\n") if k.strip()]

        async for event in stream_llm_response(
            provider=provider,
            model=model,
            messages=messages,
            tools=active_tools,
            api_key=api_key,
            key_pool=key_pool,
        ):
            if event["type"] == "text":
                assistant_text += event["content"]
                yield event

            elif event["type"] == "tool_call":
                tool_calls_this_turn.append(event)

            elif event["type"] == "done":
                pass  # handled after the stream ends

        # ── No tool calls → agent is done ─────────────────────────────────
        if not tool_calls_this_turn:
            messages.append({"role": "assistant", "content": assistant_text})
            yield {"type": "done"}
            return

        # ── Append assistant turn (with tool calls) to message history ─────
        messages.append({
            "role": "assistant",
            "content": assistant_text,
            "tool_calls": [
                {
                    "id": tc["tool_call_id"],
                    "type": "function",
                    "function": {
                        "name": tc["tool_name"],
                        "arguments": json.dumps(tc["tool_args"]),
                    },
                }
                for tc in tool_calls_this_turn
            ],
        })

            # ── Execute each tool and stream result back ───────────────────────
        for tc in tool_calls_this_turn:
            yield {
                "type": "tool_start",
                "name": tc["tool_name"],
                "args": tc["tool_args"],
            }

            # --- Special Tool: run_parallel_subtasks ---
            if tc["tool_name"] == "run_parallel_subtasks":
                subtasks = tc["tool_args"].get("subtasks", [])
                if not subtasks:
                    result = "Error: No subtasks provided."
                else:
                    yield {
                        "type": "text",
                        "content": f"\n\n🚀 **Spawning {len(subtasks)} parallel workers...**"
                    }
                    
                    # Launch sub-agents in parallel
                    async def run_sub_agent(sub_task: str, sub_key: str):
                        # Simple helper to consume the generator and return final text
                        final_res = ""
                        async for event in run_agent(
                            user_message=f"Independent Subtask: {sub_task}\nPlease complete this and provide a brief summary of what you did.",
                            session_history=[], # Fresh session for each subtask
                            provider=provider,
                            model=model,
                            api_key=sub_key,
                            user_keys=user_keys,
                            workspace_path=workspace_path
                        ):
                            if event["type"] == "text":
                                final_res += event["content"]
                        return f"Subtask '{sub_task}' result:\n{final_res}"

                    # Use the key_pool to distribute tasks
                    results_list = []
                    tasks = []
                    for i, st in enumerate(subtasks):
                        # Use a different key for each if available
                        skey = key_pool[i % len(key_pool)] if key_pool else api_key
                        tasks.append(run_sub_agent(st, skey))
                    
                    results_list = await asyncio.gather(*tasks)
                    result = "\n\n".join(results_list)
                    
            else:
                result = await execute_tool(tc["tool_name"], tc["tool_args"], user_keys, workspace_path=workspace_path)

            # --- Incremental Indexing ---
            # If a file was written, update its semantic index immediately.
            # FAISS and the embeddings HTTP call are blocking/CPU-bound, so run
            # them in a worker thread — otherwise they freeze the whole event
            # loop, stalling every other request (chat, session switch) meanwhile.
            if tc["tool_name"] == "write_file" and "Success" in result:
                try:
                    from app.services.code_search import CodeSearchService
                    api_keys = []
                    if user_keys and user_keys.get("gemini"):
                        api_keys = [k.strip() for k in user_keys["gemini"].split("\n") if k.strip()]

                    written_path = tc["tool_args"]["path"]

                    def _reindex():
                        service = CodeSearchService(workspace_path or "", api_keys=api_keys)
                        service.update_file_index(written_path)

                    await asyncio.to_thread(_reindex)
                except Exception as e:
                    print(f"Error during incremental indexing: {e}")

            # Truncate for UI display — full result still goes to the model
            yield {
                "type": "tool_result",
                "name": tc["tool_name"],
                "result": result[:500],
            }

            # Persist to DB if callback provided
            if on_tool_call:
                await on_tool_call(tc["tool_name"], tc["tool_args"], result)

            # Full result goes into the message history for the model
            messages.append({
                "role": "tool",
                "tool_call_id": tc["tool_call_id"],
                "content": result,
            })

            if tc["tool_name"] == "screenshot_url":
                if result.startswith("Screenshot saved successfully."):
                    yield {
                        "type": "text",
                        "content": "\n\nThe screenshot has been saved successfully. You can find the exact path in the tool output.",
                    }
                else:
                    yield {
                        "type": "text",
                        "content": f"\n\nScreenshot failed: {result}",
                    }
                yield {"type": "done"}
                return

    yield {
        "type": "error",
        "message": "Reached maximum iterations. The task may be too complex — try breaking it into smaller steps.",
    }
