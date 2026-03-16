from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# 导入配置
from app.config import DOC_DIR

from app.utils.logger import logger

from app.api import kb
from app.api import session   # 新增导入会话管理路由


# ---------- FastAPI 应用 ----------
app = FastAPI(
    title="LocalRAG-QA",
    description="基于开源大模型的本地知识库问答系统",
    version="1.0.0"
)

# =========================
# 注册 API 路由（全部走 /api 前缀）
# =========================
from app.api import health, document, chat
app.include_router(health.router, prefix="/api")
app.include_router(document.router, prefix="/api/docs")
app.include_router(chat.router, prefix="/api")
app.include_router(kb.router)
app.include_router(session.router)  # 注册会话管理路由（已在内部定义前缀 /api/sessions）

# =========================
# API 入口说明
# =========================

@app.get("/api")
def api_root():
    return {
        "message": "LocalRAG-QA Backend Running",
        "docs": "/docs",
        "health": "/api/health"
    }

# =========================
# 挂载前端（必须挂载到 "/"）
# =========================
BASE_DIR = Path(__file__).parent.parent  # LocalRAG-QA 根目录
STATIC_DIR = BASE_DIR / "web"

if STATIC_DIR.exists():
    # 关键：挂载到 "/"，并启用 html=True 才会自动加载 index.html
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")
    logger.info(f"前端静态文件已挂载: {STATIC_DIR}")
else:
    logger.warning(f"未找到前端目录: {STATIC_DIR}")

# =========================
# 启动初始化
# =========================
@app.on_event("startup")
def startup():
    """应用启动时初始化"""
    try:
        DOC_DIR.mkdir(parents=True, exist_ok=True)

        logger.info("=" * 50)
        logger.info("LocalRAG-QA FastAPI 服务器启动成功")
        logger.info(f"文档存储目录: {DOC_DIR}")
        logger.info(f"前端目录: {STATIC_DIR}")
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"启动时创建目录失败: {e}")
        raise

@app.on_event("shutdown")
def shutdown():
    logger.info("LocalRAG-QA 服务器正在关闭...")