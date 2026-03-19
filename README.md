LocalRAG-QA
LocalRAG-QA 是一个专为法律咨询场景设计的本地化检索增强生成（RAG）系统。它支持多知识库管理、针对法律条款的精细化预处理、混合检索（Vector + BM25）以及基于会话的持久化多轮对话。

🌟 核心特性
本地化部署：基于 Ollama 或本地 Transformers，确保数据私密性。

混合检索策略：结合高维向量检索（语义）与 BM25 稀疏检索（关键词），并使用 RRF 算法进行结果融合。

法律条款适配：提供 article 切片模式，自动识别法律条、款结构，保留元数据溯源。

多知识库路由：支持在单次对话中跨多个知识库进行联合检索。

全栈架构：后端 FastAPI 异步驱动，前端 Vue 3 + Pinia 提供流畅交互。

🛠️ 技术栈
后端：Python 3.9+, FastAPI, Uvicorn, SQLAlchemy (SQLite)

向量引擎：ChromaDB (本地持久化文件)

检索算法：Rank-BM25 + Sentence-Transformers (Embedding)

文档解析：Unstructured (支持 PDF, DOCX, TXT)

前端：Vue 3, Vite, Element Plus, Pinia, Axios

🚀 快速开始
1. 环境准备
确保本地已安装并启动 Ollama，并下载默认模型：

Bash
ollama pull qwen2.5:1.5b
(注：可在 app/config.py 中修改模型名称及 API 地址)

2. 后端启动 (FastAPI)
Bash
# 进入后端目录
cd app
# 安装依赖 (建议使用虚拟环境)
pip install -r requirements.txt
# 启动服务
uvicorn main:app --reload
后端默认运行在：http://localhost:8000

3. 前端启动 (Vue 3)
Bash
# 进入前端目录
cd web
# 安装依赖
npm install
# 启动开发服务器
npm run dev
访问地址：http://localhost:5173
