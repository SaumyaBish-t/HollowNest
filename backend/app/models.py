from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid


def gen_uuid():
    return str(uuid.uuid4())


class Session(Base):
    __tablename__ = "sessions"
    # Sessions are listed for a single user at a time, sorted by recency,
    # so an index on (user_id, updated_at) keeps the dashboard query cheap.
    __table_args__ = (
        Index("ix_sessions_user_updated", "user_id", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    # Clerk user id (the `sub` claim from the session JWT). Every read,
    # update, and delete query filters on this so users only ever see their
    # own sessions.
    user_id: Mapped[str] = mapped_column(String(100), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(200), default="New session")
    provider: Mapped[str] = mapped_column(String(50), default="qwen")
    model: Mapped[str] = mapped_column(String(100), default="qwen3-coder-next")
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="session", order_by="Message.created_at"
    )


class Message(Base):
    __tablename__ = "messages"
    # Loading a session filters by session_id and sorts by created_at —
    # without this index Postgres does a full scan + sort every time.
    __table_args__ = (
        Index("ix_messages_session_created", "session_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    session_id: Mapped[str] = mapped_column(String, ForeignKey("sessions.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(20))       # user | assistant | tool
    content: Mapped[str] = mapped_column(Text, nullable=True)
    # Stores tool_calls array for assistant messages that invoked tools
    tool_calls_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    tool_call_id: Mapped[str] = mapped_column(String(100), nullable=True)
    attachments: Mapped[list] = mapped_column(JSON, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped["Session"] = relationship("Session", back_populates="messages")
    tool_calls: Mapped[list["ToolCall"]] = relationship("ToolCall", back_populates="message")


class ToolCall(Base):
    __tablename__ = "tool_calls"
    # tool_calls are loaded per-message via selectinload (WHERE message_id IN ...).
    __table_args__ = (
        Index("ix_tool_calls_message_id", "message_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    message_id: Mapped[str] = mapped_column(String, ForeignKey("messages.id", ondelete="CASCADE"))
    tool_name: Mapped[str] = mapped_column(String(100))
    tool_input: Mapped[dict] = mapped_column(JSON, nullable=True)
    tool_output: Mapped[str] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    message: Mapped["Message"] = relationship("Message", back_populates="tool_calls")