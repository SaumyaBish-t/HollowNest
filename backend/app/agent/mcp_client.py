import httpx
import asyncio
import subprocess
import os
import json
import sys
from pathlib import Path
from app.config import settings


# ── Tool metadata for the frontend Tool Store ─────────────────────────────────
if sys.platform == "win32" and hasattr(asyncio, "WindowsProactorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


TOOL_METADATA = {
    "read_file": {
        "name": "File Reader",
        "description": "Read the contents of any file in the workspace.",
        "category": "builtin",
        "icon": "file-text",
        "credentials": [],
    },
    "write_file": {
        "name": "File Writer",
        "description": "Create and edit files in the workspace.",
        "category": "builtin",
        "icon": "file-plus",
        "credentials": [],
    },
    "list_files": {
        "name": "Directory Browser",
        "description": "List files and folders in the workspace.",
        "category": "builtin",
        "icon": "folder",
        "credentials": [],
    },
    "run_command": {
        "name": "Shell Terminal",
        "description": "Run shell commands (npm, pip, git, etc.).",
        "category": "builtin",
        "icon": "terminal",
        "credentials": [],
    },
    "fetch_url": {
        "name": "URL Fetcher",
        "description": "Fetch the text content of any web page or API.",
        "category": "builtin",
        "icon": "globe",
        "credentials": [],
    },
    "screenshot_url": {
        "name": "Screenshot URL",
        "description": "Take a screenshot of a web page or locally running app and save it to the workspace.",
        "category": "builtin",
        "icon": "image",
        "credentials": [],
    },
    "web_search": {
        "name": "Web Search",
        "description": "Search the web for current information, docs, and answers. Uses Tavily when a key is provided; falls back to DuckDuckGo for keyless search.",
        "category": "external",
        "icon": "search",
        "credentials": [
            {"key": "tavily", "label": "Tavily API Key (optional)", "placeholder": "tvly-... — leave blank to use DuckDuckGo", "link": "https://app.tavily.com/home"}
        ],
    },
    "github_tool": {
        "name": "GitHub",
        "description": "List repos, read/write files, manage PRs and issues on GitHub.",
        "category": "external",
        "icon": "github",
        "credentials": [
            {"key": "github", "label": "Personal Access Token", "placeholder": "ghp_... or github_pat_...", "link": "https://github.com/settings/tokens"}
        ],
    },
    "query_database": {
        "name": "Database Query",
        "description": "Run read-only SQL SELECT queries against any PostgreSQL database.",
        "category": "external",
        "icon": "database",
        "credentials": [
            {"key": "db_connection", "label": "PostgreSQL Connection String", "placeholder": "postgresql://user:pass@host/db", "link": ""}
        ],
    },
    "send_email": {
        "name": "Email Sender",
        "description": "Send task completion reports, test results, build summaries, or important agent output by email.",
        "category": "external",
        "icon": "mail",
        "credentials": [
            {"key": "brevo", "label": "Brevo API Key", "placeholder": "xkeysib-...", "link": "https://app.brevo.com/settings/keys/api"},
            {"key": "brevo_sender_email", "label": "Brevo Sender Email", "placeholder": "agent@yourdomain.com", "link": "https://app.brevo.com/senders"},
            {"key": "brevo_sender_name", "label": "Brevo Sender Name", "placeholder": "NexusAI Agent", "link": ""}
        ],
    },
    "semantic_search": {
        "name": "Semantic Search",
        "description": "Search the project code by meaning and context using a local embedding model. No API key required.",
        "category": "builtin",
        "icon": "zap",
        "credentials": [],
    },
    "index_workspace": {
        "name": "Index Project",
        "description": "Scan and index all project files for semantic search using a local embedding model. No API key required.",
        "category": "builtin",
        "icon": "refresh-cw",
        "credentials": [],
    },
    "run_parallel_subtasks": {
        "name": "Parallel Subtasks",
        "description": "Run multiple independent subtasks concurrently using different API keys.",
        "category": "builtin",
        "icon": "layers",
        "credentials": [],
    },
    "edit_file": {
        "name": "Edit File",
        "description": "Surgical find-and-replace edits — much cheaper than rewriting a file.",
        "category": "builtin",
        "icon": "file-text",
        "credentials": [],
    },
    "get_file_tree": {
        "name": "File Tree",
        "description": "Show an ASCII tree of the workspace structure.",
        "category": "builtin",
        "icon": "folder",
        "credentials": [],
    },
    "regex_search": {
        "name": "Regex Search",
        "description": "Search file contents across the workspace with a regular expression.",
        "category": "builtin",
        "icon": "search",
        "credentials": [],
    },
    "plan_tool": {
        "name": "Plan",
        "description": "Track a TODO plan for the current task (set / add / complete / get).",
        "category": "builtin",
        "icon": "layers",
        "credentials": [],
    },
    "notion_tool": {
        "name": "Notion",
        "description": "Search Notion, read pages, or create new pages in your workspace.",
        "category": "external",
        "icon": "file-text",
        "credentials": [
            {"key": "notion", "label": "Notion Integration Token", "placeholder": "secret_...", "link": "https://www.notion.so/profile/integrations"}
        ],
    },
    "slack_tool": {
        "name": "Slack",
        "description": "Post a message to a Slack channel via an incoming webhook.",
        "category": "external",
        "icon": "globe",
        "credentials": [
            {"key": "slack_webhook", "label": "Slack Incoming Webhook URL", "placeholder": "https://hooks.slack.com/services/...", "link": "https://api.slack.com/messaging/webhooks"}
        ],
    },
}


# All builtin tool names — these are always available, no key needed
BUILTIN_TOOLS = [k for k, v in TOOL_METADATA.items() if v["category"] == "builtin"]


def get_filtered_tools(enabled_tool_names: list[str] | None) -> list[dict]:
    """
    Return only the MCP_TOOLS entries whose function name is in enabled_tool_names.
    Built-in tools are always included. If enabled_tool_names is None, return ALL tools.
    """
    if enabled_tool_names is None:
        return MCP_TOOLS

    # Always include builtins + whatever externals the user has connected
    allowed = set(BUILTIN_TOOLS) | set(enabled_tool_names)
    return [t for t in MCP_TOOLS if t["function"]["name"] in allowed]


# MCP tool definitions sent to the LLM
MCP_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file in the user's project workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write or overwrite a file in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and folders in the workspace directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Subdirectory to list (empty = root)",
                        "default": "",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command in the workspace (e.g. npm test, pytest). Returns stdout and stderr.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to run"},
                    "timeout": {
                        "type": "integer",
                        "description": "Max seconds to wait",
                        "default": 30,
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "Fetch the text content of a web page or API docs URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "screenshot_url",
            "description": "Take a screenshot of a web page or locally running app (e.g. http://localhost:3000) and save it to the workspace. Use this to visually verify that a frontend you built renders correctly. Returns the saved file path so the user can view the screenshot.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to screenshot e.g. http://localhost:3000"
                    },
                    "filename": {
                        "type": "string",
                        "description": "Output filename (default: screenshot.png)",
                        "default": "screenshot.png"
                    },
                    "full_page": {
                        "type": ["boolean", "string"],
                        "description": "Whether to capture the full scrollable page height. Use false/true or 'false'/'true'. Default false.",
                        "default": False
                    },
                    "wait_ms": {
                        "type": ["integer", "string"],
                        "description": "Milliseconds to wait after page load before screenshot. Use 1000 or '1000'. Useful for pages with animations. Default 1000.",
                        "default": 1000
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information, library docs, Stack Overflow answers, GitHub issues, or any topic. Use this before writing code that depends on external libraries to get the latest API.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query string"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Max results to return. Default 5.",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_tool",
            "description": "Interact with GitHub. Create a new repository, list repos, read/create/update files, list or read pull requests and issues, get commit history, and create issues and PRs. Use when the user wants to work with their GitHub repositories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "list_repos",
                            "create_repo",
                            "read_file",
                            "create_file",
                            "update_file",
                            "list_pull_requests",
                            "read_pull_request",
                            "list_issues",
                            "read_issue",
                            "get_commits",
                            "create_issue",
                            "create_pull_request"
                        ],
                        "description": "The GitHub action to perform"
                    },
                    "repo": {
                        "type": "string",
                        "description": "Repository as owner/repo e.g. SaumyaBish-t/nexusai"
                    },
                    "path": {
                        "type": "string",
                        "description": "File path inside the repo for file actions"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content of the file to create or update"
                    },
                    "message": {
                        "type": "string",
                        "description": "Commit message for creating or updating a file"
                    },
                    "number": {
                        "type": "integer",
                        "description": "PR or issue number for read_pull_request and read_issue"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max items to return for list actions. Default 10.",
                        "default": 10
                    },
                    "title": {
                        "type": "string",
                        "description": "Title for the new issue or pull request"
                    },
                    "body": {
                        "type": "string",
                        "description": "Body/description for the new issue or pull request. For create_issue from a code scan, include affected file path, line number or nearest function/component, evidence, impact, and suggested fix."
                    },
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of label names to apply to the issue e.g. ['bug', 'help wanted']",
                        "default": []
                    },
                    "head_branch": {
                        "type": "string",
                        "description": "The branch with changes for create_pull_request (e.g. feature/my-fix)"
                    },
                    "base_branch": {
                        "type": "string",
                        "description": "The target branch to merge into for create_pull_request (e.g. main)",
                        "default": "main"
                    },
                    "name": {
                        "type": "string",
                        "description": "Name of the new repository for the create_repo action"
                    },
                    "description": {
                        "type": "string",
                        "description": "Short description for the new repository (create_repo action)"
                    },
                    "private": {
                        "type": "boolean",
                        "description": "Whether the new repository is private. Default false (public).",
                        "default": False
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_database",
            "description": "Run a read-only SELECT query against the application Postgres database to inspect sessions, messages, tool_calls tables. Use this to debug data issues or understand current DB state. Only SELECT statements are permitted.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "A valid SELECT SQL statement. Must begin with SELECT."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max rows to return. Default 20, hard cap 100.",
                        "default": 20
                    }
                },
                "required": ["sql"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send an email. Draft the subject and body from the user's prompt and conversation context when exact wording is not provided. Match requested tones such as professional, friendly, concise, collaboration, follow-up, apology, sales, support, status update, or summary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "Recipient email address"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject line. Draft this if the user only describes the goal of the email."
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body in plain text or simple HTML. Draft this from the user's prompt, requested tone, and conversation context if the user does not provide exact body text."
                    }
                },
                "required": ["to", "subject", "body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "semantic_search",
            "description": "Search the workspace code for snippets that are semantically relevant to the query. Use this to find where specific logic is implemented, even if you don't know the exact keywords.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The natural language query or task description"},
                    "top_k": {"type": "integer", "description": "Number of results to return", "default": 5}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "index_workspace",
            "description": "Manually trigger a full re-indexing of the project workspace. Use this if the project structure has changed significantly.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_parallel_subtasks",
            "description": "Execute a list of independent subtasks concurrently. Use this for large projects where different files can be worked on at the same time. Each subtask will run on its own agent instance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subtasks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of clear, independent tasks to run in parallel"
                    }
                },
                "required": ["subtasks"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Make a surgical find-and-replace edit to a file. The 'find' string must appear EXACTLY ONCE in the file — include enough surrounding context to make it unique. Use this instead of write_file when modifying an existing file — it is far cheaper in tokens.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path inside the workspace."},
                    "find": {"type": "string", "description": "Exact text to find. Must appear once in the file."},
                    "replace": {"type": "string", "description": "Text to replace it with."},
                },
                "required": ["path", "find", "replace"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_tree",
            "description": "Return an ASCII tree of the workspace directory structure. Use this at the start of a task to understand the project layout in one call instead of many list_files calls.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Subpath to start from (defaults to workspace root).", "default": "."},
                    "max_depth": {"type": "integer", "description": "How many directory levels deep to descend.", "default": 4},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "regex_search",
            "description": "Search file contents across the workspace using a regular expression. Returns matching lines with file path and line number. Use this for exact-text or pattern matches; use semantic_search for meaning-based queries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Python regular expression to search for."},
                    "glob": {"type": "string", "description": "Optional filename glob filter such as '*.py' or '*.tsx'.", "default": ""},
                    "path": {"type": "string", "description": "Subpath to limit the search to.", "default": "."},
                    "max_results": {"type": "integer", "description": "Maximum matching lines to return.", "default": 50},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "plan_tool",
            "description": "Track a TODO plan for the current task. Use action='set' with a list of tasks at the start, action='complete' with a task_id as you finish each step, action='add' to append new tasks, and action='get' to read the current plan. The plan persists for the session in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["set", "add", "complete", "get"]},
                    "tasks": {"type": "array", "items": {"type": "string"}, "description": "Task descriptions for action='set' (replaces the plan) or action='add' (appends)."},
                    "task_id": {"type": "string", "description": "Task id to mark complete for action='complete'."},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "notion_tool",
            "description": "Interact with Notion. action='search' finds pages by query, action='read_page' returns the text of a page, action='create_page' creates a new page as a child of an existing page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["search", "read_page", "create_page"]},
                    "query": {"type": "string", "description": "Search query for action='search'."},
                    "page_id": {"type": "string", "description": "Page id for action='read_page', or the parent page id for action='create_page'."},
                    "title": {"type": "string", "description": "Title for action='create_page'."},
                    "content": {"type": "string", "description": "Body text for action='create_page'."},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "slack_tool",
            "description": "Post a message to a Slack channel via the configured incoming webhook URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "The message text to post to Slack."},
                },
                "required": ["message"],
            },
        },
    }
]


DEFAULT_WORKSPACE = Path(settings.workspace_dir).resolve()
DEFAULT_WORKSPACE.mkdir(parents=True, exist_ok=True)


def _resolve_workspace(workspace_path: str | None = None) -> Path:
    """Resolve the workspace directory — user-provided or default from .env."""
    if workspace_path:
        ws = Path(workspace_path).resolve()
        if ws.exists() and ws.is_dir():
            return ws
    return DEFAULT_WORKSPACE


def _safe_path(relative: str, workspace: Path) -> Path:
    """Prevent path traversal attacks — all paths must stay inside workspace."""
    resolved = (workspace / relative).resolve()
    if not str(resolved).startswith(str(workspace)):
        raise ValueError("Path traversal not allowed")
    return resolved


async def execute_tool(tool_name: str, tool_args: dict, user_keys: dict = None, workspace_path: str = None) -> str:
    """Execute an MCP tool and return result as string."""
    workspace = _resolve_workspace(workspace_path)

    try:
        if tool_name == "read_file":
            p = _safe_path(tool_args["path"], workspace)
            if not p.exists():
                return f"Error: File '{tool_args['path']}' not found in {workspace}."
            return p.read_text(encoding="utf-8")

        elif tool_name == "write_file":
            p = _safe_path(tool_args["path"], workspace)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(tool_args["content"], encoding="utf-8")
            return f"Successfully wrote {len(tool_args['content'])} chars to '{tool_args['path']}' (in {workspace})."

        elif tool_name == "list_files":
            directory = tool_args.get("directory", "")
            p = _safe_path(directory, workspace) if directory else workspace
            if not p.exists():
                return f"Directory '{directory}' not found in {workspace}."
            items = []
            for item in sorted(p.iterdir()):
                prefix = "📁" if item.is_dir() else "📄"
                items.append(f"{prefix} {item.name}")
            return "\n".join(items) or "Empty directory."

        elif tool_name == "run_command":
            command = tool_args["command"]
            timeout = tool_args.get("timeout", 30)
            # Hardened blocklist for run_command. shell=True is required so
            # the agent can run real dev workflows (npm test, pip install,
            # pytest -k foo, git status, etc.), so we lean on pattern
            # rejection rather than full sandboxing.
            lowered = command.lower()
            blocked_patterns = [
                "rm -rf /", "rm -rf /*", "rm -rf ~", "rm -rf $home",
                "sudo ", "doas ",
                "curl | sh", "curl | bash", "wget | sh", "wget | bash",
                "curl -s | sh", "curl -fssl | sh",
                ":(){ :|:& };:",          # fork bomb
                "mkfs", "dd if=", " of=/dev/",
                "chmod -r 777 /", "chown -r ",
                "shutdown", "reboot", "halt", "poweroff",
                "/etc/passwd", "/etc/shadow",
                "$(curl", "`curl", "$(wget", "`wget",
            ]
            for pattern in blocked_patterns:
                if pattern in lowered:
                    return f"Error: Command blocked for safety: matched '{pattern}'"
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(workspace),
            )
            output = ""
            if result.stdout:
                output += f"stdout:\n{result.stdout}"
            if result.stderr:
                output += f"\nstderr:\n{result.stderr}"
            output += f"\nExit code: {result.returncode}"
            return output.strip()

        elif tool_name == "fetch_url":
            url = tool_args["url"]
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url, follow_redirects=True)
                # Return first 4000 chars to avoid context overflow
                return resp.text[:4000]

        elif tool_name == "screenshot_url":
            url = tool_args["url"]
            filename = tool_args.get("filename", "screenshot.png")
            full_page = tool_args.get("full_page", False)
            wait_ms = tool_args.get("wait_ms", 1000)

            if isinstance(full_page, str):
                full_page = full_page.strip().lower() in ("true", "1", "yes")
            try:
                wait_ms = int(wait_ms)
            except (TypeError, ValueError):
                wait_ms = 1000

            if not filename.endswith(".png"):
                filename = filename + ".png"

            output_path = _safe_path(filename, workspace)

            try:
                capture_script = r"""
import asyncio
import json
import sys
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

if sys.platform == "win32" and hasattr(asyncio, "WindowsProactorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

params = json.loads(sys.argv[1])
with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox"],
    )
    try:
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        try:
            page.goto(params["url"], wait_until="networkidle", timeout=30000)
        except PlaywrightTimeoutError:
            page.goto(params["url"], wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(params["wait_ms"])
        page.screenshot(
            path=params["output_path"],
            full_page=params["full_page"],
        )
    finally:
        browser.close()
"""
                params = {
                    "url": url,
                    "output_path": str(output_path),
                    "full_page": full_page,
                    "wait_ms": wait_ms,
                }
                result = subprocess.run(
                    [sys.executable, "-c", capture_script, json.dumps(params)],
                    capture_output=True,
                    text=True,
                    timeout=45,
                )
                if result.returncode != 0:
                    error = (result.stderr or result.stdout).strip()
                    return f"screenshot_url error: {error or 'Playwright capture failed.'}"

                file_size_kb = output_path.stat().st_size // 1024
                return (
                    f"Screenshot saved successfully.\n"
                    f"File: {filename}\n"
                    f"Path: {str(output_path)}\n"
                    f"Size: {file_size_kb}KB\n"
                    f"URL captured: {url}\n"
                    f"Full page: {full_page}"
                )

            except Exception as e:
                return f"screenshot_url error: {str(e)}"

        elif tool_name == "web_search":
            from app.config import settings

            query = tool_args["query"]
            max_results = int(tool_args.get("max_results", 5) or 5)
            tavily_key = (user_keys or {}).get("tavily") or settings.tavily_api_key

            # Preferred path: Tavily when a key is present.
            if tavily_key:
                try:
                    from tavily import TavilyClient
                    client = TavilyClient(api_key=tavily_key)
                    response = client.search(
                        query=query,
                        max_results=max_results,
                        include_raw_content=False,
                    )
                    results = response.get("results", [])
                    if results:
                        lines = [f"Search results for: {query}\n"]
                        for i, r in enumerate(results, 1):
                            lines.append(f"{i}. {r.get('title', 'No title')}")
                            lines.append(f"   URL: {r.get('url', '')}")
                            snippet = (r.get("content", "") or "")[:300]
                            lines.append(f"   {snippet}\n")
                        return "\n".join(lines)
                    # Fall through to DDG if Tavily returned nothing
                except Exception as e:
                    print(f"[web_search] Tavily failed, falling back to DuckDuckGo: {e}")

            # Fallback: DuckDuckGo — no key needed.
            try:
                try:
                    from ddgs import DDGS
                except ImportError:
                    from duckduckgo_search import DDGS  # legacy package name

                def _ddg_search():
                    with DDGS() as ddgs:
                        return list(ddgs.text(query, max_results=max_results))

                results = await asyncio.to_thread(_ddg_search)
                if not results:
                    return "No results found for that query."

                lines = [f"Search results for: {query} (via DuckDuckGo)\n"]
                for i, r in enumerate(results, 1):
                    title = r.get("title") or r.get("heading") or "No title"
                    url = r.get("href") or r.get("url") or ""
                    snippet = (r.get("body") or r.get("snippet") or "")[:300]
                    lines.append(f"{i}. {title}")
                    lines.append(f"   URL: {url}")
                    lines.append(f"   {snippet}\n")
                return "\n".join(lines)
            except ImportError:
                return (
                    "web_search needs either a Tavily key or the 'ddgs' package "
                    "installed for DuckDuckGo fallback."
                )
            except Exception as e:
                return f"web_search error (DuckDuckGo): {str(e)}"

        elif tool_name == "github_tool":
            from github import Github, GithubException
            from app.config import settings

            github_token = (user_keys or {}).get("github", "")

            if not github_token:
                return (
                    "GitHub tool not configured. "
                    "Please add your GitHub PAT in the Settings."
                )

            try:
                g = Github(github_token)
                action = tool_args["action"]
                limit = int(tool_args.get("limit", 10))

                if action == "list_repos":
                    user = g.get_user()
                    repos = list(user.get_repos())[:limit]
                    lines = [f"Repos for {user.login}:\n"]
                    for r in repos:
                        lines.append(
                            f"- {r.full_name} | "
                            f"⭐ {r.stargazers_count} | "
                            f"{r.description or 'No description'} | "
                            f"{r.html_url}"
                        )
                    return "\n".join(lines)

                elif action == "read_file":
                    repo = g.get_repo(tool_args["repo"])
                    file = repo.get_contents(tool_args["path"])
                    content = file.decoded_content.decode("utf-8")
                    return content[:4000]

                elif action == "create_file":
                    repo = g.get_repo(tool_args["repo"])
                    content = tool_args.get("content", "")
                    message = tool_args.get("message", f"Create {tool_args['path']}")
                    repo.create_file(tool_args["path"], message, content)
                    return f"Successfully created {tool_args['path']}"

                elif action == "update_file":
                    repo = g.get_repo(tool_args["repo"])
                    file = repo.get_contents(tool_args["path"])
                    content = tool_args.get("content", "")
                    message = tool_args.get("message", f"Update {tool_args['path']}")
                    repo.update_file(tool_args["path"], message, content, file.sha)
                    return f"Successfully updated {tool_args['path']}"

                elif action == "list_pull_requests":
                    repo = g.get_repo(tool_args["repo"])
                    prs = list(repo.get_pulls(state="open"))[:limit]
                    if not prs:
                        return "No open pull requests found."
                    lines = [f"Open PRs in {tool_args['repo']}:\n"]
                    for pr in prs:
                        lines.append(
                            f"#{pr.number} {pr.title} "
                            f"by {pr.user.login} | "
                            f"{pr.html_url}"
                        )
                    return "\n".join(lines)

                elif action == "read_pull_request":
                    repo = g.get_repo(tool_args["repo"])
                    pr = repo.get_pull(tool_args["number"])
                    files_changed = [f.filename for f in pr.get_files()]
                    return (
                        f"PR #{pr.number}: {pr.title}\n"
                        f"Author: {pr.user.login}\n"
                        f"State: {pr.state}\n"
                        f"Base: {pr.base.ref} ← Head: {pr.head.ref}\n"
                        f"Files changed: {', '.join(files_changed)}\n\n"
                        f"Description:\n{pr.body or 'No description'}"
                    )

                elif action == "list_issues":
                    repo = g.get_repo(tool_args["repo"])
                    issues = list(repo.get_issues(state="open"))[:limit]
                    if not issues:
                        return "No open issues found."
                    lines = [f"Open issues in {tool_args['repo']}:\n"]
                    for issue in issues:
                        labels = ", ".join([l.name for l in issue.labels]) or "none"
                        lines.append(
                            f"#{issue.number} {issue.title} "
                            f"[{labels}] | "
                            f"{issue.html_url}"
                        )
                    return "\n".join(lines)

                elif action == "read_issue":
                    repo = g.get_repo(tool_args["repo"])
                    issue = repo.get_issue(tool_args["number"])
                    labels = ", ".join([l.name for l in issue.labels]) or "none"
                    return (
                        f"Issue #{issue.number}: {issue.title}\n"
                        f"State: {issue.state}\n"
                        f"Labels: {labels}\n"
                        f"Comments: {issue.comments}\n\n"
                        f"Body:\n{issue.body or 'No description'}"
                    )

                elif action == "get_commits":
                    repo = g.get_repo(tool_args["repo"])
                    commits = list(repo.get_commits())[:limit]
                    lines = [f"Recent commits in {tool_args['repo']}:\n"]
                    for c in commits:
                        lines.append(
                            f"{c.sha[:7]} — {c.commit.message.splitlines()[0]} "
                            f"({c.commit.author.name}, {c.commit.author.date.date()})"
                        )
                    return "\n".join(lines)

                elif action == "create_issue":
                    repo = g.get_repo(tool_args["repo"])
                    labels_input = tool_args.get("labels", [])

                    # Get existing label objects; skip labels that do not exist.
                    label_objects = []
                    for label_name in labels_input:
                        try:
                            label_objects.append(repo.get_label(label_name))
                        except Exception:
                            pass

                    issue = repo.create_issue(
                        title=tool_args["title"],
                        body=tool_args.get("body", ""),
                        labels=label_objects,
                    )
                    return (
                        f"Issue created successfully.\n"
                        f"#{issue.number}: {issue.title}\n"
                        f"Labels: {', '.join([l.name for l in label_objects]) or 'none'}\n"
                        f"URL: {issue.html_url}"
                    )

                elif action == "create_pull_request":
                    repo = g.get_repo(tool_args["repo"])

                    if "head_branch" not in tool_args:
                        return (
                            "create_pull_request requires 'head_branch' parameter. "
                            "This is the branch that has your changes."
                        )

                    pr = repo.create_pull(
                        title=tool_args["title"],
                        body=tool_args.get("body", ""),
                        head=tool_args["head_branch"],
                        base=tool_args.get("base_branch", "main"),
                    )
                    return (
                        f"Pull request created successfully.\n"
                        f"#{pr.number}: {pr.title}\n"
                        f"{pr.head.ref} -> {pr.base.ref}\n"
                        f"URL: {pr.html_url}"
                    )

                elif action == "create_repo":
                    repo_arg = tool_args.get("repo", "") or ""
                    name = tool_args.get("name") or (
                        repo_arg.split("/")[-1] if repo_arg else ""
                    )
                    if not name:
                        return "create_repo requires a 'name' for the new repository."

                    auth_user = g.get_user()
                    owner = repo_arg.split("/")[0] if "/" in repo_arg else ""
                    private = bool(tool_args.get("private", False))
                    description = tool_args.get("description", "") or ""

                    # If an org owner is specified, create under the org;
                    # otherwise create under the authenticated user's account.
                    if owner and owner.lower() != auth_user.login.lower():
                        target = g.get_organization(owner)
                    else:
                        target = auth_user

                    new_repo = target.create_repo(
                        name=name,
                        description=description,
                        private=private,
                        auto_init=True,
                    )
                    return (
                        f"Repository created successfully.\n"
                        f"{new_repo.full_name} "
                        f"({'private' if private else 'public'})\n"
                        f"URL: {new_repo.html_url}\n"
                        f"Clone URL: {new_repo.clone_url}"
                    )

                else:
                    return f"Unknown github_tool action: {action}"

            except GithubException as e:
                return f"GitHub API error: {e.data.get('message', str(e))}"
            except Exception as e:
                return f"github_tool error: {str(e)}"

        elif tool_name == "query_database":
            import sqlalchemy
            from sqlalchemy import text
            from app.database import engine

            sql = tool_args.get("sql", "").strip()
            limit = min(tool_args.get("limit", 20), 100)

            # Safety: only allow SELECT statements
            if not sql.upper().startswith("SELECT"):
                return (
                    "Only SELECT statements are allowed. "
                    f"Your query started with: {sql[:30]}"
                )

            # Inject LIMIT if not present to prevent huge result sets
            sql_upper = sql.upper()
            if "LIMIT" not in sql_upper:
                sql = f"{sql} LIMIT {limit}"

            try:
                # Use user_provided db_connection if available, else standard engine
                db_conn_str = (user_keys or {}).get("db_connection")
                if db_conn_str:
                    from sqlalchemy import create_engine
                    # Fallback sync wrapper for external DBs in simple query (can also use async but sync ensures broad dbapi support)
                    temp_engine = create_engine(db_conn_str.replace("postgresql+asyncpg://", "postgresql://"))
                    with temp_engine.connect() as conn:
                        result = conn.execute(text(sql))
                        rows = result.fetchall()
                        columns = list(result.keys())
                else:
                    async with engine.connect() as conn:
                        result = await conn.execute(text(sql))
                        rows = result.fetchall()
                        columns = list(result.keys())

                    if not rows:
                        return "Query returned 0 rows."

                    # Format as a readable table
                    lines = [" | ".join(columns)]
                    lines.append("-" * len(lines[0]))
                    for row in rows:
                        lines.append(" | ".join(str(v)[:50] for v in row))
                    lines.append(f"\n{len(rows)} row(s) returned.")
                    return "\n".join(lines)

            except Exception as e:
                return f"Database query error: {str(e)}"

        elif tool_name == "send_email":
            from app.config import settings

            brevo_api_key = (user_keys or {}).get("brevo") or settings.brevo_api_key
            sender_email = (user_keys or {}).get("brevo_sender_email") or settings.brevo_sender_email
            sender_name = (user_keys or {}).get("brevo_sender_name") or settings.brevo_sender_name

            if not brevo_api_key:
                return (
                    "send_email is not configured. "
                    "Add BREVO_API_KEY to your .env file. "
                    "Create a Brevo API key at https://app.brevo.com/settings/keys/api."
                )

            if not sender_email:
                return (
                    "send_email is not configured. "
                    "Add BREVO_SENDER_EMAIL to your .env file. "
                    "Use a sender email registered in Brevo."
                )

            try:
                # Wrap plain text body in minimal HTML for better rendering
                html_body = tool_args["body"].replace("\n", "<br>")
                html_body = f"""
        <div style="font-family: monospace; max-width: 600px; padding: 24px;">
            <h2 style="color: #6366F1;">NexusAI Agent Report</h2>
            <hr style="border-color: #252525;">
            <div style="margin-top: 16px; line-height: 1.6;">
                {html_body}
            </div>
            <hr style="border-color: #252525; margin-top: 24px;">
            <p style="color: #71717A; font-size: 12px;">
                Sent by NexusAI Agent
            </p>
        </div>
        """

                payload = {
                    "sender": {
                        "name": sender_name,
                        "email": sender_email,
                    },
                    "to": [{"email": tool_args["to"]}],
                    "subject": tool_args["subject"],
                    "htmlContent": html_body,
                    "textContent": tool_args["body"],
                }

                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.post(
                        "https://api.brevo.com/v3/smtp/email",
                        headers={
                            "accept": "application/json",
                            "api-key": brevo_api_key,
                            "content-type": "application/json",
                        },
                        json=payload,
                    )
                    if response.is_error:
                        return f"send_email error: {response.status_code} {response.text}"
                    data = response.json()

                return (
                    f"Email sent successfully. "
                    f"Message ID: {data.get('messageId', 'unknown')} | "
                    f"To: {tool_args['to']} | "
                    f"Subject: {tool_args['subject']}"
                )

            except Exception as e:
                return f"send_email error: {str(e)}"

        elif tool_name == "semantic_search":
            from app.services.code_search import CodeSearchService
            search_service = CodeSearchService(str(workspace))
            return search_service.search(tool_args["query"], tool_args.get("top_k", 5))

        elif tool_name == "index_workspace":
            from app.services.code_search import CodeSearchService
            search_service = CodeSearchService(str(workspace))
            return search_service.index_workspace()

        elif tool_name == "edit_file":
            p = _safe_path(tool_args["path"], workspace)
            if not p.exists():
                return f"Error: File '{tool_args['path']}' not found in {workspace}."
            content = p.read_text(encoding="utf-8")
            find_str = tool_args["find"]
            replace_str = tool_args["replace"]
            count = content.count(find_str)
            if count == 0:
                return (
                    f"Error: 'find' string was not found in '{tool_args['path']}'. "
                    "Include more surrounding context so it matches exactly."
                )
            if count > 1:
                return (
                    f"Error: 'find' string appears {count} times in '{tool_args['path']}'. "
                    "Add surrounding context so it is unique."
                )
            new_content = content.replace(find_str, replace_str, 1)
            p.write_text(new_content, encoding="utf-8")
            return f"Successfully edited '{tool_args['path']}' (1 replacement)."

        elif tool_name == "get_file_tree":
            root = _safe_path(tool_args.get("path", "."), workspace)
            if not root.exists():
                return f"Error: Path '{tool_args.get('path', '.')}' not found."
            max_depth = int(tool_args.get("max_depth", 4))
            ignore_set = {
                ".git", "node_modules", "venv", "__pycache__", ".nexus",
                ".next", "dist", "build", "target", ".cache", ".pytest_cache",
            }
            lines = [f"{root.name}/"]

            def _walk(d, depth, prefix=""):
                if depth >= max_depth:
                    return
                try:
                    entries = sorted(
                        [e for e in d.iterdir() if e.name not in ignore_set],
                        key=lambda e: (not e.is_dir(), e.name.lower()),
                    )
                except PermissionError:
                    return
                for i, e in enumerate(entries):
                    is_last = i == len(entries) - 1
                    branch = "└── " if is_last else "├── "
                    lines.append(f"{prefix}{branch}{e.name}{'/' if e.is_dir() else ''}")
                    if len(lines) > 600:
                        return
                    if e.is_dir():
                        _walk(e, depth + 1, prefix + ("    " if is_last else "│   "))

            _walk(root, 0)
            if len(lines) > 600:
                lines = lines[:600] + ["… (truncated)"]
            return "\n".join(lines)

        elif tool_name == "regex_search":
            import re
            import fnmatch
            try:
                pattern = re.compile(tool_args["pattern"])
            except re.error as e:
                return f"Invalid regex: {e}"
            glob_pat = tool_args.get("glob", "")
            root = _safe_path(tool_args.get("path", "."), workspace)
            max_results = int(tool_args.get("max_results", 50))
            ignore_set = {
                ".git", "node_modules", "venv", "__pycache__", ".nexus",
                ".next", "dist", "build", "target", ".cache",
            }
            results = []
            for r, dirs, files in os.walk(root):
                dirs[:] = [d for d in dirs if d not in ignore_set]
                for f in files:
                    if glob_pat and not fnmatch.fnmatch(f, glob_pat):
                        continue
                    fp = Path(r) / f
                    try:
                        with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                            for lineno, line in enumerate(fh, 1):
                                if pattern.search(line):
                                    rel = fp.relative_to(workspace)
                                    results.append(f"{rel}:{lineno}: {line.rstrip()[:200]}")
                                    if len(results) >= max_results:
                                        return "\n".join(results)
                    except Exception:
                        continue
            return "\n".join(results) if results else "No matches."

        elif tool_name == "plan_tool":
            action = tool_args.get("action", "get")
            plan_file = workspace / ".nexus" / "plan.json"
            plan_file.parent.mkdir(parents=True, exist_ok=True)
            plan = []
            if plan_file.exists():
                try:
                    plan = json.loads(plan_file.read_text(encoding="utf-8"))
                except Exception:
                    plan = []

            def _fmt(p):
                if not p:
                    return "(plan is empty)"
                return "\n".join(
                    f"[{'x' if t.get('done') else ' '}] {t['id']}. {t['task']}" for t in p
                )

            if action == "get":
                return _fmt(plan)
            if action == "set":
                tasks = tool_args.get("tasks") or []
                plan = [{"id": str(i + 1), "task": str(t), "done": False} for i, t in enumerate(tasks)]
                plan_file.write_text(json.dumps(plan, indent=2))
                return f"Plan set with {len(plan)} task(s):\n{_fmt(plan)}"
            if action == "add":
                tasks = tool_args.get("tasks") or []
                next_id = max([int(t["id"]) for t in plan], default=0) + 1
                for t in tasks:
                    plan.append({"id": str(next_id), "task": str(t), "done": False})
                    next_id += 1
                plan_file.write_text(json.dumps(plan, indent=2))
                return f"Added {len(tasks)} task(s):\n{_fmt(plan)}"
            if action == "complete":
                task_id = str(tool_args.get("task_id", ""))
                hit = False
                for t in plan:
                    if t["id"] == task_id:
                        t["done"] = True
                        hit = True
                plan_file.write_text(json.dumps(plan, indent=2))
                return f"Marked task {task_id} done.\n{_fmt(plan)}" if hit else f"No task with id '{task_id}'."
            return f"Unknown plan action: {action}"

        elif tool_name == "notion_tool":
            # Calls Notion's REST API directly via httpx — no extra deps needed.
            token = (user_keys or {}).get("notion", "")
            if not token:
                return "Notion not configured. Add NOTION_API_KEY in .env or paste a token in the Tool Store."
            headers = {
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json",
            }
            base = "https://api.notion.com/v1"
            action = tool_args["action"]

            async with httpx.AsyncClient(timeout=20.0) as hc:
                if action == "search":
                    r = await hc.post(
                        f"{base}/search",
                        headers=headers,
                        json={"query": tool_args.get("query", ""), "page_size": 10},
                    )
                    if r.status_code != 200:
                        return f"Notion API error {r.status_code}: {r.text}"
                    items = r.json().get("results", []) or []
                    if not items:
                        return "No results."
                    lines = []
                    for it in items:
                        title = "(untitled)"
                        for pv in (it.get("properties") or {}).values():
                            if pv.get("type") == "title" and pv["title"]:
                                title = pv["title"][0].get("plain_text", title)
                                break
                        lines.append(
                            f"{it.get('object')} | {it.get('id')} | {title} | {it.get('url', '')}"
                        )
                    return "\n".join(lines)

                if action == "read_page":
                    pid = tool_args["page_id"]
                    r = await hc.get(f"{base}/blocks/{pid}/children", headers=headers)
                    if r.status_code != 200:
                        return f"Notion API error {r.status_code}: {r.text}"
                    blocks = r.json().get("results", []) or []
                    texts = []
                    for b in blocks:
                        btype = b.get("type")
                        bd = b.get(btype) or {}
                        rich = bd.get("rich_text", []) if isinstance(bd, dict) else []
                        line = "".join(rt.get("plain_text", "") for rt in rich)
                        if line:
                            texts.append(line)
                    return "\n".join(texts) if texts else "(page has no text blocks)"

                if action == "create_page":
                    parent_id = tool_args["page_id"]
                    title = tool_args.get("title", "Untitled")
                    body = tool_args.get("content", "")
                    children = []
                    if body:
                        children = [{
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {"rich_text": [{"type": "text", "text": {"content": body}}]},
                        }]
                    payload = {
                        "parent": {"page_id": parent_id},
                        "properties": {
                            "title": {"title": [{"type": "text", "text": {"content": title}}]}
                        },
                        "children": children,
                    }
                    r = await hc.post(f"{base}/pages", headers=headers, json=payload)
                    if r.status_code != 200:
                        return f"Notion API error {r.status_code}: {r.text}"
                    page = r.json()
                    return f"Created Notion page: {page.get('url', page.get('id'))}"

            return f"Unknown notion action: {action}"

        elif tool_name == "slack_tool":
            webhook = (user_keys or {}).get("slack_webhook", "")
            if not webhook:
                return "Slack not configured. Add SLACK_WEBHOOK_URL in .env or paste a webhook in the Tool Store."
            message = tool_args.get("message", "")
            if not message:
                return "Provide a 'message' to post."
            async with httpx.AsyncClient() as hc:
                r = await hc.post(webhook, json={"text": message}, timeout=15.0)
            if r.status_code == 200 and r.text.strip() == "ok":
                return "Posted to Slack."
            return f"Slack post failed: {r.status_code} {r.text}"

        else:
            return f"Error: Unknown tool '{tool_name}'."

    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {tool_args.get('timeout', 30)}s."
    except Exception as e:
        return f"Error executing '{tool_name}': {str(e)}"
