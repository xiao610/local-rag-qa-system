# app/api/session.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import uuid
from datetime import datetime
from sqlalchemy.orm import Session as DbSession

from app.database.models import Session as SessionModel, Message as MessageModel
from app.database.models import SessionLocal

router = APIRouter(prefix="/api/sessions", tags=["会话管理"])

# 依赖：获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class SessionCreate(BaseModel):
    name: Optional[str] = "新对话"
    kb_id: Optional[str] = None

class SessionResponse(BaseModel):
    id: str
    name: str
    kb_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    message_count: int

class MessageResponse(BaseModel):
    role: str
    content: str
    timestamp: datetime

@router.post("", response_model=SessionResponse, summary="创建新会话")
def create_session(req: SessionCreate, db: DbSession = Depends(get_db)):
    session_id = str(uuid.uuid4())
    session = SessionModel(
        id=session_id,
        name=req.name,
        kb_id=req.kb_id
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {
        "id": session.id,
        "name": session.name,
        "kb_id": session.kb_id,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "message_count": 0
    }

@router.get("", response_model=List[SessionResponse], summary="获取所有会话列表")
def list_sessions(db: DbSession = Depends(get_db)):
    sessions = db.query(SessionModel).order_by(SessionModel.updated_at.desc()).all()
    result = []
    for s in sessions:
        result.append({
            "id": s.id,
            "name": s.name,
            "kb_id": s.kb_id,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
            "message_count": len(s.messages)
        })
    return result

@router.delete("/{session_id}", summary="删除指定会话")
def delete_session(session_id: str, db: DbSession = Depends(get_db)):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(404, "会话不存在")
    db.delete(session)
    db.commit()
    return {"message": "删除成功"}

@router.get("/{session_id}/history", response_model=List[MessageResponse], summary="获取会话历史消息")
def get_history(session_id: str, db: DbSession = Depends(get_db)):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(404, "会话不存在")
    messages = db.query(MessageModel).filter(MessageModel.session_id == session_id).order_by(MessageModel.timestamp).all()
    return [{"role": m.role, "content": m.content, "timestamp": m.timestamp} for m in messages]