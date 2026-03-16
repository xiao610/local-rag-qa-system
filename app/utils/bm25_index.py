import pickle
import jieba
from pathlib import Path
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
from app.config import BM25_DIR

class BM25Index:
    def __init__(self, index_dir: Path = BM25_DIR):
        self.index_dir = index_dir
        self.index_dir.mkdir(parents=True, exist_ok=True)

    def build_index(self, kb_id: str, texts: List[str], metadatas: List[Dict[str, Any]]):
        tokenized_corpus = [self._tokenize(text) for text in texts]
        bm25 = BM25Okapi(tokenized_corpus)
        index_path = self.index_dir / f"{kb_id}.pkl"
        with open(index_path, 'wb') as f:
            pickle.dump({
                'bm25': bm25,
                'metadatas': metadatas,
                'texts': texts
            }, f)
        return bm25

    def load_index(self, kb_id: str):
        index_path = self.index_dir / f"{kb_id}.pkl"
        if not index_path.exists():
            return None, None, None
        with open(index_path, 'rb') as f:
            data = pickle.load(f)
        return data['bm25'], data['metadatas'], data['texts']

    def _tokenize(self, text: str):
        """
        使用 jieba 精确模式进行中文分词
        """
        return list(jieba.cut(text))