from abc import ABC, abstractmethod
from typing import List, Tuple, Any
import numpy as np

class VectorStore(ABC):
    """向量数据库抽象基类"""

    @abstractmethod
    def add_vectors(self, vectors: np.ndarray, metadatas: List[dict]):
        """增量添加向量与元数据"""
        pass

    @abstractmethod
    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[dict, float]]:
        """返回 (metadata, score) 列表，score 为距离（越小越相似）"""
        pass

    @abstractmethod
    def save(self, path: str):
        """保存索引到指定路径"""
        pass

    @abstractmethod
    def load(self, path: str):
        """从指定路径加载索引"""
        pass

    # 为简化 RAG 调用，提供可选检索器接口
    def as_retriever(self, top_k: int = 5):
        """返回一个可调用对象，接收 query: str，返回 (documents, scores)"""
        def retrieve(query: str):
            # 需要子类实现嵌入方法，此处仅定义契约
            raise NotImplementedError("子类必须实现嵌入与检索逻辑")
        return retrieve