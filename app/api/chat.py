# app/api/chat.py
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from sqlalchemy.orm import Session as DbSession
import uuid

from app.vectorstore import create_vector_store
from app.embedding.embedder import Embedder
from app.llm import create_llm
from app.core.rag_pipeline import RAGPipeline
from app.utils.logger import logger
from app.database.models import Session as SessionModel, Message as MessageModel
from app.database.models import SessionLocal
from app.utils.kb_utils import safe_collection_name

router = APIRouter()

# 全局单例
embedder = Embedder()
llm = create_llm()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class QueryRequest(BaseModel):
    query: str
    kb_id: Union[str, List[str]] = "default"
    session_id: Optional[str] = None
    top_k: int = 5
    similarity_threshold: float = 0.2
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    max_tokens: Optional[int] = None


class QueryResponse(BaseModel):
    answer: str
    sources: Optional[List[Dict[str, Any]]] = None
    session_id: Optional[str] = None


def generate_session_title(question: str, session_id: str):
    """
    后台任务：根据用户第一个问题生成会话标题（独立数据库会话）
    """
    db = SessionLocal()
    try:
        # 构造 prompt，让 LLM 生成简短的标题
        prompt = f"请根据以下用户问题，生成一个简短的会话标题（不超过15个字）：\n\n{question}"
        title = llm.generate(prompt, temperature=0.3, max_tokens=20).strip()
        # 去除可能的引号
        title = title.strip('"').strip("'").strip()
        if not title:
            title = "新对话"

        # 更新会话名称
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if session:
            session.name = title
            db.commit()
            logger.info(f"会话 {session_id} 标题已更新为: {title}")
    except Exception as e:
        logger.error(f"生成会话标题失败: {e}")
        # 如果生成失败，设置一个默认标题
        try:
            session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
            if session and session.name == "新对话":
                session.name = "新对话"
                db.commit()
        except:
            pass
    finally:
        db.close()


@router.post("/chat", summary="聊天接口", response_model=QueryResponse)
def chat(req: QueryRequest, background_tasks: BackgroundTasks, db: DbSession = Depends(get_db)):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query不能为空")

    # 处理会话逻辑
    session_id = req.session_id
    is_new_session = False

    if session_id:
        # 已有会话，检查是否存在
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        # 如果会话未绑定知识库，则绑定第一个（如果有多个则取第一个）
        if session.kb_id is None:
            first_kb = req.kb_id[0] if isinstance(req.kb_id, list) else req.kb_id
            session.kb_id = first_kb
            db.commit()
    else:
        # 新会话：创建一个
        is_new_session = True
        session_id = str(uuid.uuid4())
        # 临时名称，稍后后台任务会更新
        session = SessionModel(
            id=session_id,
            name="新对话",  # 临时名称
            kb_id=req.kb_id[0] if isinstance(req.kb_id, list) else req.kb_id
        )
        db.add(session)
        db.commit()
        logger.info(f"创建新会话: {session_id}")

    # 获取历史消息（最多10条）
    recent_msgs = db.query(MessageModel).filter(MessageModel.session_id == session_id) \
        .order_by(MessageModel.timestamp.desc()).limit(10).all()
    history = [{"role": m.role, "content": m.content} for m in reversed(recent_msgs)]

    # 判断是否为第一条消息（必须在保存用户消息前判断）
    msg_count = db.query(MessageModel).filter(MessageModel.session_id == session_id).count()
    is_first_message = msg_count == 0

    # 保存用户消息
    user_msg = MessageModel(session_id=session_id, role="user", content=req.query)
    db.add(user_msg)
    db.commit()

    # 如果是第一条消息，添加后台任务生成标题
    if is_first_message:
        # 注意：这里传入 session_id 和 question，后台任务会自行创建数据库会话
        background_tasks.add_task(generate_session_title, req.query, session_id)

    try:
        # 创建向量存储列表
        if isinstance(req.kb_id, str):
            kb_ids = [req.kb_id]
        else:
            kb_ids = req.kb_id
        collection_names = [safe_collection_name(kb) for kb in kb_ids]
        vector_stores = [create_vector_store(collection_name=name) for name in collection_names]

        rag = RAGPipeline(
            vector_stores=vector_stores,
            llm=llm,
            embedder=embedder
        )

        answer, sources = rag.ask(
            question=req.query,
            top_k=req.top_k,
            similarity_threshold=req.similarity_threshold,
            system_prompt=req.system_prompt,
            temperature=req.temperature,
            top_p=req.top_p,
            presence_penalty=req.presence_penalty,
            frequency_penalty=req.frequency_penalty,
            max_tokens=req.max_tokens,
            history=history if history else None
        )

        # 保存助手回复
        assistant_msg = MessageModel(session_id=session_id, role="assistant", content=answer)
        db.add(assistant_msg)
        # 更新会话时间
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        session.updated_at = datetime.utcnow()
        db.commit()

        return QueryResponse(answer=answer, sources=sources, session_id=session_id)

    except Exception as e:
        logger.error(f"问答处理失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"问答处理失败: {str(e)}")