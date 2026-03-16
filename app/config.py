from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

STORAGE_DIR = PROJECT_ROOT / "storage"
DOC_DIR = STORAGE_DIR / "documents"
CHROMA_PERSIST_DIR = STORAGE_DIR / "chroma_data"
BM25_DIR = STORAGE_DIR / "bm25"

# ---------- 向量存储引擎选择 ----------
VECTOR_STORE_TYPE = "chroma"

# Embedding 模型配置
EMBEDDING_MODEL_NAME = "BAAI/bge-large-zh-v1.5"   # 维度将由模型自动获取

# ---------- ChromaDB 配置 ----------
CHROMA_PERSIST_DIR = STORAGE_DIR / "chroma_data"   # 持久化目录
CHROMA_COLLECTION_NAME = "knowledge_base"          # 集合名称

# ---------- LLM 类型选择 ----------
LLM_TYPE = "ollama"   # 可选 "ollama" 或 "hf"

# ---------- Ollama 配置 ----------
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:1.5b"

# ---------- Hugging Face 模型配置 ----------
HF_MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"   # 可更换为其他模型
HF_USE_FP16 = True                              # 是否使用半精度（仅 GPU 有效）
HF_LOAD_IN_8BIT = False                          # 8-bit 量化（需要 bitsandbytes）
HF_LOAD_IN_4BIT = True                           # 4-bit 量化（需要 bitsandbytes）
HF_MAX_NEW_TOKENS = 512
HF_TEMPERATURE = 0.1

# 检索与切片参数
TOP_K = 3
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

