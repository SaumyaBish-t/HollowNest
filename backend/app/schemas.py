from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SessionCreate(BaseModel):
    provider: str = "qwen"
    model: Optional[str] = None


class SessionUpdate(BaseModel):
    title: Optional[str] = None


class SessionOut(BaseModel):
    id: str
    title: str
    provider: str
    model: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ToolCallOut(BaseModel):
    id: str
    tool_name: str
    tool_input: Optional[dict]
    tool_output: Optional[str]
    duration_ms: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: str
    role: str
    content: Optional[str]
    tool_call_id: Optional[str]
    created_at: datetime
    tool_calls: list[ToolCallOut] = []
    attachments: Optional[list[dict]] = None

    model_config = {"from_attributes": True}


class SessionDetailOut(SessionOut):
    messages: list[MessageOut] = []


class RunAgentRequest(BaseModel):
    message: str
    session_id: Optional[str] = None   # None = create new session
    provider: str = "qwen"
    model: Optional[str] = None
    enabled_tools: Optional[list[str]] = None  # Only these tools are given to the LLM
    workspace_path: Optional[str] = None  # User-chosen project folder for file ops
    attachments: Optional[list[dict]] = None # Array of file info dicts returned from /uploads