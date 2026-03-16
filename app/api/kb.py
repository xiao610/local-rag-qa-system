# app/api/kb.py
from fastapi import APIRouter, HTTPException, Query
from chromadb import PersistentClient
from app.config import CHROMA_PERSIST_DIR
from app.vectorstore import create_vector_store
from app.utils.kb_utils import safe_collection_name

router = APIRouter(prefix="/api/kb", tags=["知识库管理"])

@router.post("/create", summary="创建知识库")
def create_kb(kb_id: str = Query(..., description="知识库ID（支持中文）")):
    """
    创建新知识库（实际是创建空集合）。
    传入的 kb_id 可以是中文，内部自动转换为合法的 ChromaDB 集合名，
    并将原始名称存入集合的 metadata 中。
    """
    collection_name = safe_collection_name(kb_id)
    try:
        store = create_vector_store(collection_name=collection_name)
        # 触发生效并设置元数据（原始名称）
        store.collection.modify(metadata={"display_name": kb_id})
        # 调用 count 确保集合被创建（可选）
        store.collection.count()
        return {
            "message": f"知识库 {kb_id} 创建成功",
            "kb_id": kb_id,
            "collection_name": collection_name
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{kb_id}", summary="删除知识库")
def delete_kb(kb_id: str):
    """
    删除知识库（删除集合）。
    传入的 kb_id 可以是中文，内部自动转换为合法的集合名。
    """
    collection_name = safe_collection_name(kb_id)
    client = PersistentClient(path=str(CHROMA_PERSIST_DIR))
    try:
        client.delete_collection(collection_name)
        return {"message": f"知识库 {kb_id} 已删除"}
    except ValueError:
        raise HTTPException(status_code=404, detail="知识库不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list", summary="查看已创建知识库")
def list_kb():
    """
    列出所有知识库，返回每个知识库的原始名称（display_name）和内部集合名。
    若集合没有 display_name 元数据，则使用集合名本身作为后备。
    """
    client = PersistentClient(path=str(CHROMA_PERSIST_DIR))
    collections = client.list_collections()
    result = []
    for col in collections:
        metadata = col.metadata
        display_name = metadata.get("display_name", col.name) if metadata else col.name
        result.append({
            "collection_name": col.name,
            "display_name": display_name
        })
    return {"kb_list": result}