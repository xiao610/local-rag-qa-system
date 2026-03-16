import numpy as np
import chromadb
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path
from .base import VectorStore
import os
from app.utils.bm25_index import BM25Index
from app.config import BM25_DIR

class ChromaStore(VectorStore):
    """
    ChromaDB 向量存储实现
    约定：metadatas 中必须包含 'text' 字段，存储原始文本块
    """

    def __init__(self, persist_directory: str, collection_name: str):
        """
        初始化 ChromaDB 存储实例
        :param persist_directory: 持久化目录路径
        :param collection_name:   集合名称（每个知识库对应一个独立集合）
        """
        self.persist_directory = str(persist_directory)
        self.collection_name = collection_name

        # 初始化 ChromaDB 持久化客户端
        self.client = chromadb.PersistentClient(path=self.persist_directory)

        # 获取或创建集合（不指定 embedding 函数，完全由外部传入向量）
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={
                "hnsw:space": "cosine",
                "hnsw:construction_ef": 200,  # 构建时的搜索宽度（默认100）
                "hnsw:M": 32,  # 每个节点的最大连接数（默认16）
                "hnsw:search_ef": 100,  # 查询时的搜索深度（默认10）
            }
        )

    def add_vectors(self, vectors: np.ndarray, metadatas: List[dict]):
        """
        添加向量与元数据
        - vectors: shape (n, dim) 的 numpy 数组
        - metadatas: 每个元素必须包含 'text' 字段，存储原始文本
        """
        if len(vectors) != len(metadatas):
            raise ValueError("vectors 和 metadatas 长度不一致")

        start_id = self.collection.count()
        ids = [str(start_id + i) for i in range(len(vectors))]

        # 提取文本列表，并从元数据中移除 text（避免重复存储）
        documents = [meta.pop('text') for meta in metadatas]

        self.collection.add(
            embeddings=vectors.tolist(),
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def search(self, query_vector: np.ndarray, top_k: int = 5, where: Optional[Dict] = None) -> List[Tuple[dict, float]]:
        """
        向量检索，支持按元数据过滤
        - query_vector: shape (dim,) 的 numpy 数组
        - where: 过滤条件，如 {"law_type": "《中华人民共和国民法典》"}
        返回: [(metadata, score), ...]，score 为余弦相似度（越大越相似）
        """
        results = self.collection.query(
            query_embeddings=[query_vector.tolist()],
            n_results=top_k,
            where=where,  # 添加过滤条件
            include=["documents", "metadatas", "distances"]
        )

        formatted = []
        if results['ids'][0]:
            for i in range(len(results['ids'][0])):
                metadata = results['metadatas'][0][i] or {}
                metadata['text'] = results['documents'][0][i]
                similarity = 1 - results['distances'][0][i]
                formatted.append((metadata, similarity))
        return formatted

    def save(self, path: Optional[str] = None):
        """
        确保持久化目录存在。
        ChromaDB 自动持久化，此方法仅用于兼容性。
        - path: 若提供，则更新持久化目录并确保存在；若不提供，使用实例的 persist_directory。
        """
        if path is not None:
            self.persist_directory = str(path)
        os.makedirs(self.persist_directory, exist_ok=True)
        # 无需额外操作，ChromaDB 自动落盘

    def load(self, path: Optional[str] = None):
        """
        重新加载持久化的 ChromaDB 数据。
        - path: 若提供，则切换到该目录；若不提供，使用当前 persist_directory。
        """
        if path is not None:
            self.persist_directory = str(path)
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self.collection = self.client.get_collection(self.collection_name)

    def count(self) -> int:
        """返回当前集合中的向量总数"""
        return self.collection.count()

    # ---------- 删除集合（用于测试或知识库管理）----------
    def delete_collection(self):
        """删除当前集合，并重新创建同名空集合"""
        try:
            self.client.delete_collection(self.collection_name)
        except ValueError:
            # 集合不存在时忽略
            pass
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    # ================== BM25 检索（支持过滤）==================
    def bm25_search(self, query: str, top_k: int = 5, filters: Optional[Dict] = None) -> List[Tuple[dict, float]]:
        """
        使用 BM25 检索，返回 (metadata, score) 列表，score 为 BM25 得分
        :param filters: 过滤条件，如 {"law_type": "《中华人民共和国民法典》"}
        """
        bm25_dir = BM25_DIR
        bm25_indexer = BM25Index(bm25_dir)
        bm25, metadatas, texts = bm25_indexer.load_index(self.collection_name)
        if bm25 is None:
            return []

        tokenized_query = bm25_indexer._tokenize(query)
        scores = bm25.get_scores(tokenized_query)

        # 获取所有索引并按得分降序排序
        all_indices = list(range(len(scores)))
        all_indices.sort(key=lambda i: scores[i], reverse=True)

        results = []
        for idx in all_indices:
            # 确保索引有效
            if idx >= len(metadatas) or idx >= len(texts):
                continue

            meta = metadatas[idx].copy()
            # 应用过滤条件
            if filters:
                match = True
                for key, value in filters.items():
                    if meta.get(key) != value:
                        match = False
                        break
                if not match:
                    continue

            meta['text'] = texts[idx]
            results.append((meta, scores[idx]))
            if len(results) >= top_k:
                break

        return results