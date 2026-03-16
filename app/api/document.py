from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Form, Query
from fastapi.responses import FileResponse
from pathlib import Path
import os
import re
import time
from typing import List, Optional

from app.document.loader import DocumentLoader
from app.document.parser import DocumentParser
from app.document.splitter import TextSplitter, UnstructuredArticleSplitter  # 新增导入
from app.embedding.embedder import Embedder
from app.vectorstore import create_vector_store
from app.utils.logger import logger
from app.config import DOC_DIR, CHUNK_SIZE, CHUNK_OVERLAP
from app.utils.kb_utils import safe_collection_name
from app.utils.bm25_index import BM25Index

router = APIRouter(tags=["文档管理"])

# 无状态组件（全局共享）
loader = DocumentLoader()
parser = DocumentParser()


def parse_separators(sep_str: Optional[str]) -> List[str]:
    """解析分隔符（代码保持不变）"""
    if not sep_str:
        return []
    separators = []
    multi_matches = re.findall(r'`([^`]+)`', sep_str)
    for m in multi_matches:
        try:
            m = m.encode().decode('unicode_escape')
        except UnicodeDecodeError:
            pass
        separators.append(m)
        sep_str = sep_str.replace(f'`{m}`', '')
    for ch in sep_str:
        if ch and ch not in separators:
            try:
                ch = ch.encode().decode('unicode_escape')
            except UnicodeDecodeError:
                pass
            separators.append(ch)
    return separators


def process_and_store_chunks(
        chunks: List[tuple],
        source_file: str,
        vector_store,
        embedder: Embedder,
        doc_path_map: dict
):
    """
    后台任务：向量化并存储，同时记录每个块对应的文件路径，并构建BM25索引。
    增强：为每个文本块添加法律领域（area）元数据。
    支持两种块格式：三元组 (doc_name, idx, chunk_text) 或四元组 (doc_name, idx, chunk_text, metadata)
    """
    try:
        if not chunks:
            logger.warning(f"文件 {source_file} 没有生成有效的文本块")
            return 0

        chunk_texts = []
        metadatas = []
        current_time = int(time.time())

        # 预编译正则表达式用于提取法律条款信息
        article_pattern = re.compile(r'第[零一二三四五六七八九十百千万\d]+条')
        part_pattern = re.compile(r'第[零一二三四五六七八九十百千万\d]+编')
        chapter_pattern = re.compile(r'第[零一二三四五六七八九十百千万\d]+章')
        section_pattern = re.compile(r'第[零一二三四五六七八九十百千万\d]+节')

        # 法律领域关键词映射（用于自动标注 area）
        area_keywords = {
            "婚姻家庭": ["婚姻", "离婚", "家庭", "夫妻", "抚养", "收养", "亲属", "子女", "父母", "配偶", "分居", "家暴", "出轨", "重婚"],
            "继承": ["继承", "遗嘱", "遗产", "继承人", "遗赠", "扶养协议", "法定继承", "代位继承", "丧失继承权"],
            "合同": ["合同", "协议", "违约", "缔约", "格式条款", "买卖", "租赁", "借款", "赠与", "定金", "保证", "承揽", "建设工程", "运输", "技术合同", "中介", "合伙"],
            "物权": ["所有权", "用益物权", "担保物权", "占有", "抵押", "质押", "留置", "相邻", "共有", "善意取得", "宅基地", "居住权"],
            "侵权责任": ["侵权", "损害", "赔偿", "过错", "无过错", "共同侵权", "责任主体", "产品责任", "机动车", "医疗损害", "环境污染", "高度危险", "饲养动物", "建筑物", "高空抛物"],
            "总则": ["基本原则", "自然人", "法人", "民事权利", "法律行为", "代理", "民事责任", "诉讼时效", "期间", "出生", "死亡", "住所"],
            "人格权": ["人格权", "生命权", "身体权", "健康权", "姓名权", "肖像权", "名誉权", "荣誉权", "隐私权", "个人信息", "声音"],
        }

        for chunk in chunks:
            if len(chunk) == 3:
                doc_name, idx, chunk_text = chunk
                metadata = {}
            elif len(chunk) == 4:
                doc_name, idx, chunk_text, metadata = chunk
            else:
                continue

            chunk_texts.append(chunk_text)

            file_path = doc_path_map.get(doc_name, "")
            base_meta = {
                "text": chunk_text,
                "source": doc_name,
                "chunk_index": idx,
                "file_path": file_path,
                "upload_time": current_time
            }
            # 合并从分块器传递来的元数据（如标题路径、条款号等）
            base_meta.update(metadata)

            # 根据文件名推断法律类型（如民法典、刑法等）
            lower_name = doc_name.lower()
            if "民法典" in lower_name:
                law_type = "《中华人民共和国民法典》"
            elif "刑法" in lower_name:
                law_type = "《中华人民共和国刑法》"
            elif "劳动合同法" in lower_name:
                law_type = "《中华人民共和国劳动合同法》"
            elif "工伤保险条例" in lower_name:
                law_type = "《工伤保险条例》"
            else:
                law_type = "unknown"
            base_meta["law_type"] = law_type

            # 提取条款号（如果还没有）
            if "article_number" not in base_meta:
                article_match = article_pattern.search(chunk_text)
                if article_match:
                    base_meta["article_number"] = article_match.group()

            # 提取编、章、节信息（如果有）
            part_match = part_pattern.search(chunk_text)
            if part_match:
                base_meta["part"] = part_match.group()
            chapter_match = chapter_pattern.search(chunk_text)
            if chapter_match:
                base_meta["chapter"] = chapter_match.group()
            section_match = section_pattern.search(chunk_text)
            if section_match:
                base_meta["section"] = section_match.group()

            # 自动标注法律领域（area）
            chunk_lower = chunk_text.lower()
            area = "unknown"
            for area_name, keywords in area_keywords.items():
                if any(kw in chunk_lower for kw in keywords):
                    area = area_name
                    break
            base_meta["area"] = area

            metadatas.append(base_meta)

        vectors = embedder.encode(chunk_texts)
        vector_store.add_vectors(vectors, metadatas)
        vector_store.save()
        logger.info(f"成功处理并存储了 {len(chunks)} 个文本块，其中包含条款信息的块数：{sum(1 for m in metadatas if 'article_number' in m)}")

        # ---------- 构建 BM25 索引 ----------
        try:
            bm25_dir = Path("app/storage/bm25")
            bm25_indexer = BM25Index(bm25_dir)
            collection_name = vector_store.collection_name
            bm25_indexer.build_index(
                kb_id=collection_name,
                texts=chunk_texts,
                metadatas=metadatas
            )
            logger.info(f"BM25索引构建完成，知识库: {collection_name}")
        except Exception as e:
            logger.error(f"BM25索引构建失败: {e}")

        return len(chunks)
    except Exception as e:
        logger.error(f"处理并存储文本块时出错: {e}")
        raise


@router.post("/upload", summary="上传文档")
async def upload_files(
        background_tasks: BackgroundTasks,
        files: List[UploadFile] = File(..., description="支持 PDF、TXT、DOCX 格式"),
        chunk_size: Optional[int] = Form(None, description="文本块大小（字符）"),
        chunk_overlap: Optional[int] = Form(None, description="块重叠（字符）"),
        separators: Optional[str] = Form(None, description="自定义分隔符（若传入则忽略 chunk_mode）"),
        chunk_mode: str = Form("default", description="切分模式: default（通用） / article（法律条款，基于Unstructured）"),
        kb_id: str = Form("default", description="知识库ID（集合名称）")
):
    """上传文档并后台处理向量化"""
    if not files:
        raise HTTPException(status_code=400, detail="请至少上传一个文件")

    # ---------- 处理分块参数 ----------
    if chunk_size is None:
        from app.config import CHUNK_SIZE
        chunk_size = CHUNK_SIZE
    if chunk_overlap is None:
        from app.config import CHUNK_OVERLAP
        chunk_overlap = CHUNK_OVERLAP

    if chunk_size < 50:
        raise HTTPException(status_code=400, detail="chunk_size 不能小于50")
    if chunk_overlap < 0:
        raise HTTPException(status_code=400, detail="chunk_overlap 不能为负数")
    if chunk_overlap >= chunk_size:
        raise HTTPException(status_code=400, detail="chunk_overlap 必须小于 chunk_size")

    # ---------- 保存上传的文件，并记录路径映射 ----------
    saved_paths = []
    failed_files = []
    doc_path_map = {}

    for file in files:
        try:
            ext = Path(file.filename).suffix.lower()
            if ext not in loader.SUPPORTED_EXT:
                failed_files.append((file.filename, f"不支持的文件类型: {ext}"))
                continue

            safe_filename = "".join(c for c in file.filename if c.isalnum() or c in '._- ').strip()
            if not safe_filename:
                safe_filename = f"file_{len(saved_paths)}"

            file_path = DOC_DIR / safe_filename
            counter = 1
            while file_path.exists():
                name_stem = Path(safe_filename).stem
                ext = Path(safe_filename).suffix
                file_path = DOC_DIR / f"{name_stem}_{counter}{ext}"
                counter += 1

            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)

            saved_paths.append(str(file_path))
            doc_path_map[file.filename] = str(file_path)
            logger.info(f"文件保存成功: {file.filename} -> {file_path}")

        except Exception as e:
            logger.error(f"保存文件失败 {file.filename}: {e}")
            failed_files.append((file.filename, str(e)))

    if not saved_paths:
        raise HTTPException(
            status_code=400,
            detail=f"所有文件上传失败: {failed_files}"
        )

    # ---------- 根据模式选择处理路径 ----------
    try:
        if chunk_mode == "article":
            # 法律条款模式：使用元素加载器和基于 Unstructured 的分块器
            loaded_docs = loader.load_files_as_elements(saved_paths)
            if not loaded_docs:
                raise HTTPException(status_code=400, detail="未能加载任何文档内容")

            splitter = UnstructuredArticleSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            chunks = splitter.split_documents(loaded_docs)  # 返回四元组 (name, idx, text, metadata)
        else:
            # 默认模式：原有基于文本的加载和递归分块
            loaded_docs = loader.load_files(saved_paths)
            if not loaded_docs:
                raise HTTPException(status_code=400, detail="未能加载任何文档内容")

            parsed_docs = []
            for name, text in loaded_docs:
                if text and text.strip():
                    cleaned_text = parser.parse(text)
                    if cleaned_text:
                        parsed_docs.append((name, cleaned_text))
            if not parsed_docs:
                raise HTTPException(status_code=400, detail="文档清洗后无有效内容")

            # 决定分隔符列表
            if separators:
                sep_list = parse_separators(separators)
                logger.info(f"📝 使用自定义分隔符: {sep_list}")
            else:
                sep_list = None
                logger.info("📄 使用默认通用切分模式")

            splitter = TextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=sep_list
            )
            chunks = splitter.split_documents(parsed_docs)  # 返回三元组 (name, idx, text)
            # 转换为统一格式（带空元数据）
            chunks = [(doc_name, idx, text, {}) for doc_name, idx, text in chunks]

        logger.info(f"生成了 {len(chunks)} 个文本块")

        # ---------- 创建向量存储和嵌入器 ----------
        collection_name = safe_collection_name(kb_id)
        vector_store = create_vector_store(collection_name=collection_name)
        embedder = Embedder()

        # ---------- 异步向量化存储 ----------
        background_tasks.add_task(
            process_and_store_chunks,
            chunks,
            ", ".join([f.filename for f in files]),
            vector_store,
            embedder,
            doc_path_map
        )

        response = {
            "uploaded_files": [Path(p).name for p in saved_paths],
            "chunks_generated": len(chunks),
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "chunk_mode": chunk_mode,
            "separators": separators or "预设",
            "kb_id": kb_id,
            "message": f"成功上传 {len(saved_paths)} 个文件至知识库 [{kb_id}]，生成 {len(chunks)} 个文本块，向量化处理将在后台进行",
            "total_vectors_in_store": vector_store.count()
        }

        if failed_files:
            response["failed_files"] = failed_files
            response["warning"] = f"{len(failed_files)} 个文件处理失败"

        return response

    except Exception as e:
        logger.error(f"处理文档时出错: {e}")
        for file_path in saved_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"文档处理失败: {str(e)}")


@router.get("/status", summary="获取向量库状态")
def get_vector_store_status(
        kb_id: str = "default"
):
    """获取指定知识库的向量数据库状态"""
    try:
        from app.vectorstore import create_vector_store
        collection_name = safe_collection_name(kb_id)
        vector_store = create_vector_store(collection_name=collection_name)
        return {
            "status": "ok",
            "kb_id": kb_id,
            "total_vectors": vector_store.count(),
            "vector_dimension": None,
            "store_type": vector_store.__class__.__name__
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取向量库状态失败: {str(e)}")


@router.get("/list", summary="查看已入库文档")
def list_documents(
        kb_id: str = "default"
):
    """
    返回指定知识库中的文档列表（详细版）
    包含每个文档的块数、文件大小、上传时间等
    """
    try:
        from app.vectorstore import create_vector_store
        collection_name = safe_collection_name(kb_id)
        vector_store = create_vector_store(collection_name=collection_name)

        # 获取所有元数据（如果数据量极大，可分批查询，此处简化）
        all_data = vector_store.collection.get(include=["metadatas"])
        doc_map = {}

        for meta in all_data["metadatas"]:
            doc_name = meta.get("source")
            file_path = meta.get("file_path")
            if not doc_name:
                continue
            if doc_name not in doc_map:
                # 首次遇到该文档，初始化信息
                doc_info = {
                    "document": doc_name,
                    "chunks": 0,
                    "file_path": file_path,
                    "file_size": 0,
                    "upload_time": meta.get("upload_time")
                }
                # 若文件仍存在，获取大小
                if file_path and os.path.exists(file_path):
                    try:
                        doc_info["file_size"] = os.path.getsize(file_path)
                    except Exception:
                        pass
                    # 如果元数据中没有upload_time，尝试用文件创建时间作为后备
                    if doc_info["upload_time"] is None:
                        try:
                            doc_info["upload_time"] = os.path.getctime(file_path)
                        except Exception:
                            pass
                doc_map[doc_name] = doc_info
            doc_map[doc_name]["chunks"] += 1

        documents = list(doc_map.values())
        return {
            "kb_id": kb_id,
            "total_chunks": vector_store.count(),
            "documents": documents
        }
    except Exception as e:
        logger.error(f"获取文档列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete", summary="删除文档")
def delete_document(
    kb_id: str = Query(..., description="知识库ID"),
    doc_name: str = Query(..., description="文档名称（原始文件名）")
):
    """
    从指定知识库中删除文档的所有向量块，并删除对应的本地文件。
    """
    try:
        from app.vectorstore import create_vector_store
        collection_name = safe_collection_name(kb_id)
        vector_store = create_vector_store(collection_name=collection_name)

        # 1. 获取该文档的任意一个块的元数据，以得到文件路径
        result = vector_store.collection.get(
            where={"source": doc_name},
            limit=1,
            include=["metadatas"]
        )
        if not result["metadatas"]:
            raise HTTPException(status_code=404, detail="文档不存在")

        file_path = result["metadatas"][0].get("file_path")

        # 2. 删除向量库中所有属于该文档的记录
        vector_store.collection.delete(where={"source": doc_name})
        logger.info(f"已从知识库 {kb_id} 删除文档 {doc_name} 的所有向量块")

        # 3. 删除本地文件（如果存在）
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"已删除本地文件: {file_path}")
            except Exception as e:
                logger.warning(f"删除本地文件失败 {file_path}: {e}")

        return {"message": f"文档 {doc_name} 删除成功", "kb_id": kb_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


# ================== 新增下载接口 ==================
@router.get("/download", summary="下载文档")
def download_document(
        kb_id: str = Query(..., description="知识库ID"),
        doc_name: str = Query(..., description="文档名称（原始文件名）")
):
    logger.info(f"下载请求: kb_id={kb_id}, doc_name={doc_name}")
    try:
        from app.vectorstore import create_vector_store
        collection_name = safe_collection_name(kb_id)
        vector_store = create_vector_store(collection_name=collection_name)

        # 查询元数据
        result = vector_store.collection.get(
            where={"source": doc_name},
            limit=1,
            include=["metadatas"]
        )
        logger.info(f"查询条件: source={doc_name}, 结果数量={len(result['metadatas'])}")

        if result["metadatas"]:
            file_path = result["metadatas"][0].get("file_path")
            if file_path and os.path.exists(file_path):
                return FileResponse(
                    path=file_path,
                    filename=doc_name,
                    media_type="application/octet-stream"
                )
            else:
                logger.warning(f"文件路径不存在: {file_path}")

        # 后备方案：直接从文件系统查找（假设文件以原始文件名保存在 DOC_DIR）
        fallback_path = DOC_DIR / doc_name
        if fallback_path.exists():
            logger.info(f"使用后备方案找到文件: {fallback_path}")
            return FileResponse(
                path=fallback_path,
                filename=doc_name,
                media_type="application/octet-stream"
            )

        # 如果都找不到，打印所有 source 以便调试
        all_data = vector_store.collection.get(include=["metadatas"])
        all_sources = list(set(meta.get("source") for meta in all_data["metadatas"] if meta.get("source")))
        logger.warning(f"当前集合中的所有 source: {all_sources}")
        raise HTTPException(status_code=404, detail="文档不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载文档失败: {e}")
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")