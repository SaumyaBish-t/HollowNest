from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models import Session, Message
from app.schemas import SessionCreate, SessionUpdate, SessionOut, SessionDetailOut
from app.config import PROVIDERS
from app.auth import require_user

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionOut)
async def create_session(
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_user),
):
    model = body.model or PROVIDERS[body.provider]["models"][0]
    session = Session(provider=body.provider, model=model, user_id=user_id)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("", response_model=list[SessionOut])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_user),
):
    result = await db.execute(
        select(Session)
        .where(Session.user_id == user_id)
        .order_by(Session.updated_at.desc())
        .limit(50)
    )
    return result.scalars().all()


@router.get("/{session_id}", response_model=SessionDetailOut)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_user),
):
    result = await db.execute(
        select(Session)
        .options(
            selectinload(Session.messages).selectinload(Message.tool_calls)
        )
        .where(Session.id == session_id, Session.user_id == user_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.patch("/{session_id}", response_model=SessionOut)
async def update_session(
    session_id: str,
    body: SessionUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_user),
):
    result = await db.execute(
        select(Session).where(Session.id == session_id, Session.user_id == user_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if body.title is not None:
        session.title = body.title
    await db.commit()
    await db.refresh(session)
    return session


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_user),
):
    await db.execute(
        delete(Session).where(Session.id == session_id, Session.user_id == user_id)
    )
    await db.commit()
    return {"deleted": session_id}
