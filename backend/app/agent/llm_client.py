import google.generativeai as genai
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from app.config import PROVIDERS
from typing import AsyncGenerator
import json
import asyncio


# google.generativeai stores the API key in process-global state. Two
# concurrent /agent/run requests using different Gemini keys could race
# and leak each other's keys. Serialize configure + model construction
# behind this async lock so only one Gemini request configures the SDK
# at a time.
_gemini_configure_lock = asyncio.Lock()


# ── Schema for known integer/number fields per tool (used for Gemini arg coercion) ──
# Gemini's protobuf Struct returns all values as strings or floats.
# This map tells us which fields need to be cast to int or bool.
_TOOL_INT_FIELDS = {
    "github_tool": {"limit", "number"},
    "web_search": {"max_results"},
    "list_files": {"max_depth"},
}

def _coerce_tool_args(tool_name: str, args: dict) -> dict:
    """Coerce tool arguments to correct types based on schema expectations.
    Gemini's protobuf Struct often returns integers as strings or floats."""
    int_fields = _TOOL_INT_FIELDS.get(tool_name, set())
    coerced = {}
    for k, v in args.items():
        if k in int_fields and v is not None:
            try:
                coerced[k] = int(v)
            except (ValueError, TypeError):
                coerced[k] = v
        elif isinstance(v, float) and v == int(v):
            # Protobuf Structs represent ints as floats (e.g., 10.0 -> 10)
            coerced[k] = int(v)
        else:
            coerced[k] = v
    return coerced


def get_openai_compatible_client(provider: str, api_key: str) -> AsyncOpenAI:
    """Returns an AsyncOpenAI client pointed at the right base_url for the provider."""
    cfg = PROVIDERS[provider]
    return AsyncOpenAI(
        api_key=api_key or "dummy",
        base_url=cfg["base_url"],
    )


async def stream_llm_response(
    provider: str,
    model: str,
    messages: list,
    tools: list,
    api_key: str,
    key_pool: list[str] = None,
) -> AsyncGenerator[dict, None]:
    """
    Unified streaming interface for all providers.
    Yields dicts: {type: "text"|"tool_call"|"done", ...}
    Now uses Native SDKs for Gemini and Anthropic.
    """
    # Ensure pool is a flat list of stripped keys
    pool = key_pool if key_pool else []
    
    # If the primary api_key is multiline (from UI), split it too
    if api_key:
        passed_keys = [k.strip() for k in api_key.replace(",", "\n").split("\n") if k.strip()]
        for pk in passed_keys:
            if pk not in pool:
                pool.insert(0, pk)
    
    if not pool:
        pool = ["dummy"]

    if provider == "gemini":
        async for event in _stream_gemini_native(model, messages, tools, pool):
            yield event
    elif provider == "anthropic":
        async for event in _stream_anthropic(model, messages, tools, pool):
            yield event
    else:
        async for event in _stream_openai_compatible(
            provider, model, messages, tools, pool
        ):
            yield event


async def _stream_gemini_native(
    model_name: str,
    messages: list,
    tools: list,
    api_key_pool: list[str],
) -> AsyncGenerator[dict, None]:
    current_key_idx = 0
    
    while current_key_idx < len(api_key_pool):
        api_key = api_key_pool[current_key_idx].strip()

        # Prepare messages
        system_instruction = None
        gemini_history = []
        
        for m in messages:
            role = m["role"]
            content = m.get("content", "")
            
            if role == "system":
                system_instruction = content
                continue

            # Map roles: assistant -> model, everything else -> user
            gemini_role = "model" if role == "assistant" else "user"
            
            # Determine parts
            parts = []
            if role == "assistant" and m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    # Ensure arguments is a dict
                    args = tc["function"]["arguments"]
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except:
                            args = {}
                    parts.append({"function_call": {"name": tc["function"]["name"], "args": args}})
            elif role == "tool":
                # Handle tool response
                # Wrap response in a dict if it's a string
                resp_val = content
                try:
                    resp_val = json.loads(content)
                except:
                    resp_val = {"result": content}
                
                parts.append({"function_response": {"name": m.get("name", "unknown"), "response": resp_val}})
            else:
                if content:
                    parts.append({"text": content})
                if m.get("attachments"):
                    import os
                    for att in m["attachments"]:
                        path = att.get("path")
                        if path and os.path.exists(path):
                            print(f"[Gemini] Uploading attachment: {path}")
                            try:
                                gem_file = await asyncio.to_thread(genai.upload_file, path)
                                
                                # Wait for processing if it's a video/large file
                                while gem_file.state.name == "PROCESSING":
                                    print(f"[Gemini] Waiting for {path} to process...")
                                    await asyncio.sleep(2)
                                    gem_file = await asyncio.to_thread(genai.get_file, gem_file.name)
                                    
                                if gem_file.state.name == "FAILED":
                                    print(f"[Gemini] Failed to process {path}")
                                    continue
                                    
                                parts.append(gem_file)
                            except Exception as e:
                                print(f"[Gemini] Failed to attach {path}: {e}")

            # Gemini requires alternating roles. Merge consecutive same-roles.
            if gemini_history and gemini_history[-1]["role"] == gemini_role:
                gemini_history[-1]["parts"].extend(parts)
            else:
                gemini_history.append({"role": gemini_role, "parts": parts})

        # The native SDK generate_content_async expects non-empty history/content
        if not gemini_history:
            gemini_history = [{"role": "user", "parts": [{"text": "hi"}]}]
        
        contents = gemini_history

        # Convert tools to Gemini format
        def sanitize_schema(schema):
            """Gemini native SDK doesn't like 'default' fields or certain formats."""
            if not isinstance(schema, dict):
                return schema
            new_schema = {k: sanitize_schema(v) for k, v in schema.items() if k != "default"}
            return new_schema

        native_tools = []
        if tools:
            functions = []
            for t in tools:
                f = t["function"]
                functions.append({
                    "name": f["name"],
                    "description": f.get("description", ""),
                    "parameters": sanitize_schema(f.get("parameters", {"type": "object", "properties": {}}))
                })
            native_tools = [{"function_declarations": functions}]

        try:
            # Ensure model name has the required 'models/' prefix
            full_model_name = model_name if model_name.startswith("models/") else f"models/{model_name}"
            
            # Use full HARM_CATEGORY_ names required by the SDK
            safety_settings = [
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]

            # Hold the global Gemini key + model construction inside an async
            # lock so a concurrent /agent/run with a different key cannot swap
            # genai's module-level state mid-call.
            async with _gemini_configure_lock:
                genai.configure(api_key=api_key, transport='rest')
                model = genai.GenerativeModel(
                    model_name=full_model_name,
                    system_instruction=system_instruction,
                    safety_settings=safety_settings
                )

                gen_task = model.generate_content_async(
                    contents=contents,
                    tools=native_tools if native_tools else None,
                    stream=True
                )
            
            # SDK inconsistency: some versions return a coroutine, some return the iterator directly.
            if asyncio.iscoroutine(gen_task):
                response = await gen_task
            else:
                response = gen_task

            async for chunk in response:
                if not chunk.candidates:
                    continue
                candidate = chunk.candidates[0]
                
                # Check for blocked/failed responses
                if candidate.finish_reason and candidate.finish_reason not in (0, 1):
                    # finish_reason: 0=UNSPECIFIED, 1=STOP, 2=MAX_TOKENS, 3=SAFETY, 4=RECITATION, 5=OTHER
                    if candidate.finish_reason == 3:
                        yield {"type": "text", "content": "\n\n⚠️ Response blocked by safety filters. Trying again..."}
                        yield {"type": "done"}
                        return
                
                if hasattr(candidate, 'content') and candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, 'text') and part.text:
                            yield {"type": "text", "content": part.text}
                        if hasattr(part, 'function_call') and part.function_call:
                            raw_args = dict(part.function_call.args)
                            coerced_args = _coerce_tool_args(part.function_call.name, raw_args)
                            yield {
                                "type": "tool_call",
                                "tool_call_id": f"call_{current_key_idx}_{id(part)}",
                                "tool_name": part.function_call.name,
                                "tool_args": coerced_args
                            }
                
                if candidate.finish_reason == 1:  # STOP
                    yield {"type": "done"}
                    break
            
            # Success!
            return

        except Exception as e:
            error_str = str(e)
            is_rate_limit = "429" in error_str or "Unknown error trying to retrieve streaming" in error_str or "quota" in error_str.lower()
            is_suspended = "403" in error_str or "suspended" in error_str.lower() or "CONSUMER_SUSPENDED" in error_str
            is_failed_gen = "failed_generation" in error_str.lower() or "failed to call a function" in error_str.lower()
            
            if (is_rate_limit or is_suspended) and current_key_idx < len(api_key_pool) - 1:
                reason = "rate-limited" if is_rate_limit else "suspended"
                current_key_idx += 1
                print(f"[Gemini] Key {current_key_idx-1} {reason}. Rotating to key {current_key_idx}...")
                continue
            
            # Failed tool call — retry without tools so model can still respond
            if is_failed_gen and native_tools:
                print("[Gemini] Tool calling failed, retrying without tools...")
                try:
                    gen_task = model.generate_content_async(
                        contents=contents,
                        tools=None,
                        stream=True
                    )
                    if asyncio.iscoroutine(gen_task):
                        response = await gen_task
                    else:
                        response = gen_task
                        
                    async for chunk in response:
                        if not chunk.candidates:
                            continue
                        candidate = chunk.candidates[0]
                        if hasattr(candidate, 'content') and candidate.content and candidate.content.parts:
                            for part in candidate.content.parts:
                                if hasattr(part, 'text') and part.text:
                                    yield {"type": "text", "content": part.text}
                    yield {"type": "done"}
                    return
                except Exception:
                    pass  # Fall through to error message
            
            # All keys exhausted or non-recoverable error
            if is_rate_limit:
                yield {"type": "text", "content": f"\n\n⚠️ **Gemini Rate Limit**: All {len(api_key_pool)} API key(s) have hit their daily quota. Quotas reset automatically. You can:\n- Wait ~60 seconds and retry\n- Switch to **Groq** provider (it's also free!)\n- Add fresh API keys in the Integrations Hub"}
            elif is_suspended:
                yield {"type": "text", "content": f"\n\n⚠️ **Gemini Key Suspended**: Your API key has been suspended by Google. Please generate a new key at https://aistudio.google.com/apikey"}
            elif is_failed_gen:
                yield {"type": "text", "content": f"\n\n⚠️ **Gemini Tool Error**: The model failed to generate a valid tool call. Please rephrase your request or try again."}
            else:
                yield {"type": "text", "content": f"\n\n🚨 **Gemini API Error**: `{error_str}`\n*Check your API keys in the Integrations Hub.*"}
            yield {"type": "done"}
            return


# NVIDIA NIM fallback chain: primary → fast fallback → backup
_NVIDIA_STRATEGY = [
    "openai/gpt-oss-120b",                       # tool-calling primary
    "stepfun-ai/step-3.5-flash",                 # fast agentic fallback
    "minimaxai/minimax-m2.7",                    # coding fallback
    "qwen/qwen3-coder-480b-a35b-instruct",       # coder backup
]


async def _stream_openai_compatible(
    provider: str,
    model: str,
    messages: list,
    tools: list,
    api_key_pool: list[str],
) -> AsyncGenerator[dict, None]:
    # Build model chain for NVIDIA strategy models
    if provider == "nvidia" and model in _NVIDIA_STRATEGY:
        start = _NVIDIA_STRATEGY.index(model)
        model_chain = _NVIDIA_STRATEGY[start:]
    else:
        model_chain = [model]

    for current_model in model_chain:
        success = False
        async for event in _try_openai_model(provider, current_model, messages, tools, api_key_pool):
            if event.get("_fallback"):
                break
            yield event
            if event["type"] == "done":
                success = True
        if success:
            return
        if current_model != model_chain[-1]:
            label = {
                _NVIDIA_STRATEGY[0]: "Primary",
                _NVIDIA_STRATEGY[1]: "Fast Fallback",
                _NVIDIA_STRATEGY[2]: "Backup",
            }.get(current_model, current_model)
            next_label = {
                _NVIDIA_STRATEGY[0]: "Fast Fallback",
                _NVIDIA_STRATEGY[1]: "Backup",
            }.get(current_model, "next model")
            yield {"type": "text", "content": f"\n\n⚡ **{label}** model unavailable, switching to **{next_label}**...\n"}
    return


async def _try_openai_model(
    provider: str,
    model: str,
    messages: list,
    tools: list,
    api_key_pool: list[str],
) -> AsyncGenerator[dict, None]:
    current_key_idx = 0
    tool_fail_count = 0
    toolless_notified = False
    MAX_TOOL_RETRIES = 2

    while current_key_idx < len(api_key_pool):
        api_key = api_key_pool[current_key_idx]
        client = get_openai_compatible_client(provider, api_key)

        # Qwen: disable thinking mode for faster, more reliable tool calling
        extra_body = {}
        if provider == "qwen":
            extra_body = {"enable_thinking": False}

        # OpenAI schema does not support our custom "attachments" field
        sanitized_messages = []
        for m in messages:
            msg_copy = dict(m)
            if "attachments" in msg_copy:
                if msg_copy["attachments"] and msg_copy.get("role") == "user":
                    extraction_notes = []
                    has_unsupported_files = False
                    
                    for att in msg_copy["attachments"]:
                        mime = att.get("mime_type", "")
                        path = att.get("path")
                        name = att.get("original_name", "file")
                        
                        if path and mime == "application/pdf":
                            try:
                                import pypdf
                                reader = pypdf.PdfReader(path)
                                extracted_text = ""
                                for page in reader.pages:
                                    extracted_text += page.extract_text() + "\n"
                                
                                # Hard limit of 45,000 chars to prevent 429 Token Rate Limits
                                if len(extracted_text) > 45000:
                                    extracted_text = extracted_text[:45000] + "\n...[TRUNCATED TO PREVENT RATE LIMITS]..."
                                    
                                if extracted_text.strip():
                                    extraction_notes.append(f"\n[Attached Document: {name}]\n================\n{extracted_text.strip()}\n================\n")
                                else:
                                    has_unsupported_files = True # Blank/Scanned PDF
                            except Exception as e:
                                print(f"[PDF Extraction] Error extracting {path}: {e}")
                                has_unsupported_files = True
                        elif path and mime.startswith("text/"):
                            try:
                                with open(path, "r", encoding="utf-8") as f:
                                    text = f.read()
                                    if len(text) > 45000:
                                        text = text[:45000] + "\n...[TRUNCATED]..."
                                    extraction_notes.append(f"\n[Attached Text File: {name}]\n================\n{text.strip()}\n================\n")
                            except Exception:
                                has_unsupported_files = True
                        else:
                            # Not a PDF or text (e.g. image, video)
                            has_unsupported_files = True
                    
                    if extraction_notes:
                        msg_copy["content"] = str(msg_copy.get("content", "")) + "\n" + "".join(extraction_notes)
                    
                    if has_unsupported_files:
                        msg_copy["content"] = str(msg_copy.get("content", "")) + "\n\n[System Note: You attached some files (like images, videos, or scanned PDFs) that this specific AI provider does not support reading natively. Those files were ignored.]"
                        
                del msg_copy["attachments"]

            # Some providers (notably Ollama Cloud) reject messages whose
            # `content` is null. OpenAI's spec allows null for assistant
            # messages that only carry tool_calls, but we coerce to "" here
            # so every provider receives a string.
            if msg_copy.get("content") is None:
                msg_copy["content"] = ""

            sanitized_messages.append(msg_copy)

        # After repeated malformed tool calls, stop sending tools so the
        # model can at least answer in plain text instead of hard-erroring.
        send_tools = tools if (tools and tool_fail_count < MAX_TOOL_RETRIES) else None
        if tools and not send_tools and not toolless_notified:
            toolless_notified = True
            yield {
                "type": "text",
                "content": (
                    "\n\n⚠️ The model kept producing invalid tool calls, so "
                    "I'm answering this turn without tools. Try rephrasing, or "
                    "switch to **Gemini** for more reliable tool use.\n\n"
                ),
            }

        try:
            stream = await client.chat.completions.create(
                model=model,
                messages=sanitized_messages,
                tools=send_tools,
                tool_choice="auto" if send_tools else None,
                stream=True,
                extra_body=extra_body or None,
            )

            current_tool_calls = {}

            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if not delta:
                    continue

                if delta.content:
                    yield {"type": "text", "content": delta.content}

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in current_tool_calls:
                            current_tool_calls[idx] = {
                                "id": tc.id or "",
                                "name": tc.function.name or "" if tc.function else "",
                                "arguments": "",
                            }
                        if tc.id:
                            current_tool_calls[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                current_tool_calls[idx]["name"] = tc.function.name
                            if tc.function.arguments:
                                current_tool_calls[idx]["arguments"] += tc.function.arguments

                finish = chunk.choices[0].finish_reason

                if finish == "tool_calls":
                    for tc in current_tool_calls.values():
                        try:
                            args = json.loads(tc["arguments"])
                        except Exception:
                            args = {}
                        yield {
                            "type": "tool_call",
                            "tool_call_id": tc["id"],
                            "tool_name": tc["name"],
                            "tool_args": args,
                        }
                    current_tool_calls = {}

                if finish == "stop":
                    yield {"type": "done"}
            
            # If we completed the stream successfully, we are done with the while loop
            break

        except Exception as e:
            error_str = str(e)
            if "429" in error_str and current_key_idx < len(api_key_pool) - 1:
                current_key_idx += 1
                print(f"🔄 LLM Rate limit on key {current_key_idx-1}. Rotating to next key in pool...")
                continue

            # Groq & other OpenAI-compatible providers return a 400
            # ('tool_use_failed' / 'failed_generation') when the model emits a
            # malformed tool call. It's a stochastic failure — retry a couple
            # of times; once retries are spent the loop above drops tools for
            # a clean text fallback instead of showing a raw error.
            is_tool_fail = (
                "failed_generation" in error_str
                or "tool_use_failed" in error_str
                or "Failed to call a function" in error_str
            )
            if is_tool_fail and tool_fail_count < MAX_TOOL_RETRIES:
                tool_fail_count += 1
                print(f"[{provider}] Malformed tool call — retry {tool_fail_count}/{MAX_TOOL_RETRIES}")
                continue

            # For NVIDIA strategy models, signal fallback instead of hard error
            is_unavailable = any(code in error_str for code in ["429", "503", "502", "404", "overloaded", "unavailable"])
            if provider == "nvidia" and is_unavailable:
                yield {"_fallback": True, "type": "_fallback"}
                return

            yield {"type": "text", "content": f"\n\n🚨 **API Error**: `{error_str}`\n*Recommendation: If you have multiple keys, ensure they are entered in the Settings to enable automatic rotation!*"}
            yield {"type": "done"}
            break


async def _stream_anthropic(
    model: str,
    messages: list,
    tools: list,
    api_key_pool: list[str],
) -> AsyncGenerator[dict, None]:
    current_key_idx = 0
    
    while current_key_idx < len(api_key_pool):
        api_key = api_key_pool[current_key_idx]
        client = AsyncAnthropic(api_key=api_key)

        # Convert OpenAI-style tool schema to Anthropic format
        anthropic_tools = [
            {
                "name": t["function"]["name"],
                "description": t["function"].get("description", ""),
                "input_schema": t["function"].get("parameters", {}),
            }
            for t in (tools or [])
        ]

        # Anthropic separates system message from the conversation array
        system = ""
        conv_messages = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                conv_messages.append(m)

        try:
            async with client.messages.stream(
                model=model,
                max_tokens=4096,
                system=system,
                messages=conv_messages,
                tools=anthropic_tools if anthropic_tools else [],
            ) as stream:
                async for event in stream:
                    if event.type == "content_block_delta":
                        if hasattr(event.delta, "text"):
                            yield {"type": "text", "content": event.delta.text}

                    if event.type == "message_delta":
                        if event.delta.stop_reason == "tool_use":
                            msg = await stream.get_final_message()
                            for block in msg.content:
                                if block.type == "tool_use":
                                    yield {
                                        "type": "tool_call",
                                        "tool_call_id": block.id,
                                        "tool_name": block.name,
                                        "tool_args": block.input,
                                    }
                            yield {"type": "done"}
                            return

                    if event.type == "message_stop":
                        yield {"type": "done"}
            return
        except Exception as e:
            error_str = str(e)
            if "429" in error_str and current_key_idx < len(api_key_pool) - 1:
                current_key_idx += 1
                continue
            yield {"type": "text", "content": f"\n\n🚨 **Anthropic API Error**: `{error_str}`"}
            yield {"type": "done"}
            return