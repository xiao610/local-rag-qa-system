from app.config import VECTOR_STORE_TYPE
from .base import VectorStore

def create_vector_store(collection_name: str = None) -> VectorStore:
    """
    根据配置返回对应的向量存储实例。
    若指定 collection_name，则使用该名称作为 ChromaDB 集合名；
    否则使用 config 中的默认集合名。
    """
    if VECTOR_STORE_TYPE == "chroma":
        from .chroma_store import ChromaStore
        from app.config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME

        # 若未传入集合名，则使用默认值
        if collection_name is None:
            collection_name = CHROMA_COLLECTION_NAME

        return ChromaStore(
            persist_directory=str(CHROMA_PERSIST_DIR),
            collection_name=collection_name
        )
    else:
        raise ValueError(f"Unknown vector store type: {VECTOR_STORE_TYPE}")