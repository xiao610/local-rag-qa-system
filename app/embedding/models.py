from sentence_transformers import SentenceTransformer
from app.utils.logger import logger

# 支持多模型配置（key → 默认路径）
AVAILABLE_MODELS = {
    "bge-small-zh": "BAAI/bge-small-zh",
    "text2vec-base": "shibing624/text2vec-base-chinese",
}


def load_model(model_name: str = "bge-small-zh") -> SentenceTransformer:
    """
    返回 SentenceTransformer 模型实例
    支持：
    1. 简短 key（如 'bge-small-zh'）
    2. Hugging Face 全路径（如 'BAAI/bge-small-zh-v1.5'）
    """
    # 如果 model_name 是已知 key
    if model_name in AVAILABLE_MODELS:
        model_path = AVAILABLE_MODELS[model_name]
    else:
        # 否则直接当作 Hugging Face 路径
        model_path = model_name
        logger.warning(f"使用未在 AVAILABLE_MODELS 列表中的模型路径: {model_path}")

    logger.info(f"Loading embedding model: {model_name} -> {model_path}")
    model = SentenceTransformer(model_path)
    return model
