from typing import List, Optional
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from app.utils.logger import logger
from app.config import EMBEDDING_MODEL_NAME

class Embedder:
    """文本向量化统一接口（支持GPU自动切换，单例模式）"""
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        model_name: str = EMBEDDING_MODEL_NAME,
        device: Optional[str] = None,
        use_fp16: bool = False
    ):
        """
        :param model_name: 嵌入模型名称
        :param device: 运行设备，'cuda', 'cpu' 或 None（自动检测）
        :param use_fp16: 是否使用半精度（仅GPU有效，可节省显存）
        """
        # 如果已经初始化过，直接返回
        if hasattr(self, 'model'):
            logger.debug(f"Embedder already initialized, reusing existing instance.")
            return

        self.model_name = model_name
        self.use_fp16 = use_fp16

        # ---------- 1. 自动选择设备 ----------
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device

        # ---------- 2. 加载模型到指定设备 ----------
        logger.info(f"正在加载嵌入模型 {model_name} 到设备 {self.device}...")
        self.model = SentenceTransformer(model_name, device=self.device)

        # ---------- 3. 可选：转换为半精度（需模型支持）----------
        if self.device == 'cuda' and self.use_fp16:
            self.model = self.model.half()
            logger.info("已启用 FP16 半精度推理")

        # ---------- 4. 获取向量维度 ----------
        dummy = ["测试"]
        test_emb = self.encode(dummy)
        self.dim = test_emb.shape[1]
        logger.info(f"Embedder initialized: model={model_name}, dim={self.dim}, device={self.device}")

    def encode(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        批量文本编码，返回 (n, dim) 的 float32 数组
        :param texts: 文本列表
        :param batch_size: 批处理大小（GPU时可适当调大，如64/128）
        """
        # 根据设备自动选择数据类型
        convert_to_numpy = True
        if self.device == 'cuda' and self.use_fp16:
            # 半精度模式下输出 torch tensor，再转为 numpy
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=True,
                convert_to_numpy=False,
                convert_to_tensor=True
            )
            embeddings = embeddings.float().cpu().numpy()
        else:
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=True,
                convert_to_numpy=True
            )
        return embeddings.astype(np.float32)

    def embed_query(self, text: str, batch_size: int = 32) -> np.ndarray:
        """单条查询文本编码，返回 (dim,) 数组"""
        return self.encode([text], batch_size=batch_size)[0]