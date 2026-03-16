# app/core/rag_pipeline.py

import re
from collections import defaultdict
from typing import List, Optional, Tuple, Dict, Any, Union
import numpy as np
from langchain_core.prompts import PromptTemplate

from app.document.loader import DocumentLoader
from app.document.parser import DocumentParser
from app.document.splitter import TextSplitter
from app.embedding.embedder import Embedder
from app.vectorstore.base import VectorStore
from app.vectorstore import create_vector_store
from app.llm.base import LLM
from app.llm import create_llm
from app.utils.logger import logger
from app.config import EMBEDDING_MODEL_NAME

# 可选：如果安装了 sentence-transformers，可以启用 CrossEncoder
try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False
    logger.warning("sentence-transformers 未安装，CrossEncoder 功能不可用")


class RAGPipeline:
    """
    RAG 流程编排器，支持多个向量存储（多知识库检索）
    增强版：支持法律领域检测、CrossEncoder 重排序、答案验证
    （查询扩展功能已移除）
    """

    def __init__(
        self,
        doc_paths: Optional[List[str]] = None,
        vector_store: Optional[VectorStore] = None,
        vector_stores: Optional[List[VectorStore]] = None,
        llm: Optional[LLM] = None,
        embedder: Optional[Embedder] = None,
        # 以下参数已弃用（保留仅用于兼容）
        use_query_expansion: bool = False,
        use_cross_encoder: bool = True,
        cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        use_few_shot: bool = False,
    ):
        logger.info("Initializing RAGPipeline...")

        # ---------- 初始化 Embedder（所有模式都需要）----------
        self.embedder = embedder or Embedder(model_name=EMBEDDING_MODEL_NAME)

        # ---------- 模式1：从文档构建索引 ----------
        if doc_paths is not None:
            logger.info("Mode: Build from documents")
            loader = DocumentLoader()
            parser = DocumentParser()
            splitter = TextSplitter()
            file_data = loader.load_files(doc_paths)
            cleaned_docs = []
            for fname, raw_text in file_data:
                cleaned = parser.parse(raw_text)
                cleaned_docs.append((fname, cleaned))
            chunk_tuples = splitter.split_documents(cleaned_docs)
            texts = [chunk_text for _, _, chunk_text in chunk_tuples]
            metadatas = [
                {"text": chunk_text, "source": doc_name, "chunk_index": idx}
                for doc_name, idx, chunk_text in chunk_tuples
            ]
            vectors = self.embedder.encode(texts)
            self.vectorstores = [create_vector_store()]
            self.vectorstores[0].add_vectors(vectors, metadatas)
            self.vectorstores[0].save()
            logger.info(f"Built new vectorstore with {len(texts)} chunks")
            self.llm = llm or create_llm()

        # ---------- 模式2：直接使用已有组件 ----------
        elif vector_stores is not None and llm is not None:
            logger.info("Mode: Use existing vectorstores and LLM")
            self.vectorstores = vector_stores
            self.llm = llm
        elif vector_store is not None and llm is not None:
            logger.info("Mode: Use existing vectorstore and LLM (single store)")
            self.vectorstores = [vector_store]
            self.llm = llm
        else:
            raise ValueError(
                "必须提供 doc_paths（构建模式）或提供 vector_stores/vector_store 和 llm（复用模式）"
            )

        # ---------- 法律领域关键词映射（关键词 -> 编名）----------
        self.area_keywords = {
            "总则": ["基本原则", "自然人", "法人", "民事权利", "法律行为", "代理", "民事责任", "诉讼时效", "期间", "出生", "死亡", "住所"],
            "物权": ["所有权", "用益物权", "担保物权", "占有", "抵押", "质押", "留置", "相邻", "共有", "善意取得", "宅基地", "居住权"],
            "合同": ["合同", "协议", "违约", "缔约", "格式条款", "买卖合同", "租赁合同", "借款合同", "赠与", "定金", "保证", "承揽", "建设工程", "运输", "技术合同", "中介", "合伙"],
            "人格权": ["人格权", "生命权", "身体权", "健康权", "姓名权", "肖像权", "名誉权", "荣誉权", "隐私权", "个人信息", "声音"],
            "婚姻家庭": ["婚姻", "离婚", "结婚", "家庭", "夫妻", "抚养", "收养", "亲属", "子女", "父母", "配偶", "分居", "家暴", "出轨", "重婚"],
            "继承": ["继承", "遗嘱", "遗产", "继承人", "遗赠", "扶养协议", "法定继承", "代位继承", "丧失继承权"],
            "侵权责任": ["侵权", "损害", "赔偿", "过错", "无过错", "共同侵权", "责任主体", "产品责任", "机动车", "医疗损害", "环境污染", "高度危险", "饲养动物", "建筑物", "高空抛物"],
        }

        # ---------- 法律名称映射（原有的，可保留用于过滤 law_type）----------
        self.law_keywords = {
            "民法典": "《中华人民共和国民法典》",
            "刑法": "《中华人民共和国刑法》",
            "劳动合同法": "《中华人民共和国劳动合同法》",
            "工伤保险条例": "《工伤保险条例》",
        }

        # ---------- 高级检索配置 ----------
        # 查询扩展已移除，忽略 use_query_expansion
        self.use_cross_encoder = use_cross_encoder and CROSS_ENCODER_AVAILABLE
        if self.use_cross_encoder:
            self.cross_encoder = CrossEncoder(cross_encoder_model)
            logger.info(f"CrossEncoder 已加载: {cross_encoder_model}")
        else:
            self.cross_encoder = None
            if use_cross_encoder and not CROSS_ENCODER_AVAILABLE:
                logger.warning("CrossEncoder 不可用，已禁用")

        # ---------- 默认提示模板（优化版）----------
        self.default_prompt_template = PromptTemplate(
            template="""你是一位精通中国法律的专家助手。请根据以下【参考资料】中的法律条文回答用户问题。

        【参考资料】
        {context}

        【用户问题】
        {question}

        回答要求：
        1. 仔细阅读参考资料，找出与问题相关的法律条款。
        2. 基于参考资料中的条款进行推理和解释。即使参考资料不能直接给出问题的完整答案，也请结合相关法律原则给出最可能的情况分析，并说明是根据哪些条款推断的。
        3. 优先使用参考资料中的信息，如果涉及多个条款，可以综合说明。
        4. 答案应清晰、准确，直接针对用户问题，可以适当举例或分情况说明。

        请给出最终答案：""",
            input_variables=["context", "question"],
        )

        logger.info("RAGPipeline ready.")

    # -------------------- 法律领域检测 --------------------
    def _detect_law_area(self, question: str) -> Optional[str]:
        """通过关键词匹配检测问题所属的法律领域（编名）"""
        question_lower = question.lower()
        for area, keywords in self.area_keywords.items():
            for kw in keywords:
                if kw.lower() in question_lower:
                    logger.debug(f"检测到法律领域: {area} (关键词: {kw})")
                    return area
        return None

    # -------------------- 法律名称检测（原有的）--------------------
    def _detect_law_type(self, question: str) -> Optional[str]:
        """检测问题中是否提及特定法律名称，返回标准名称"""
        for keyword, full_name in self.law_keywords.items():
            if keyword in question:
                return full_name
        return None

    # -------------------- 查询扩展（已移除，仅返回原始问题）--------------------
    def _expand_query(self, question: str, law_area: Optional[str] = None) -> List[str]:
        """
        返回原始问题列表（查询扩展已移除）
        """
        return [question]

    # -------------------- 构建混合检索候选池 --------------------
    def _hybrid_retrieve(
            self,
            question: str,
            law_area: Optional[str],
            top_k: int,
            filters: Optional[Dict] = None
    ) -> List[Tuple[Dict, float]]:
        """
        使用 RRF 融合向量检索和 BM25 检索结果
        """
        query_variants = self._expand_query(question, law_area)  # 只返回原始问题
        v_results = []  # 向量结果
        b_results = []  # BM25 结果

        for q_var in query_variants:
            # 向量检索
            q_vec = self.embedder.encode([q_var])[0]
            for vs in self.vectorstores:
                v_res = vs.search(q_vec, top_k=top_k * 5, where=filters)
                v_results.extend(v_res)

            # BM25 检索
            for vs in self.vectorstores:
                b_res = vs.bm25_search(q_var, top_k=top_k * 5, filters=filters)
                b_results.extend(b_res)

        # RRF 融合参数
        K = 30
        scores = defaultdict(float)

        # 向量结果按得分排序，赋予排名
        v_sorted = sorted(v_results, key=lambda x: x[1], reverse=True)
        for rank, (meta, _) in enumerate(v_sorted):
            scores[meta['text']] += 1 / (K + rank + 1)

        # BM25 结果按得分排序，赋予排名
        b_sorted = sorted(b_results, key=lambda x: x[1], reverse=True)
        for rank, (meta, _) in enumerate(b_sorted):
            scores[meta['text']] += 1 / (K + rank + 1)

        # 按 RRF 得分排序，并找回对应的 metadata
        candidates = []
        for text, rrf_score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            # 从任一结果中取出该文本的 metadata（两者都有）
            for meta, _ in v_results + b_results:
                if meta['text'] == text:
                    candidates.append((meta, rrf_score))
                    break
        return candidates[:top_k * 5]  # 返回扩大后的候选集

    # -------------------- CrossEncoder 重排序 --------------------
    def _rerank_with_cross_encoder(
        self,
        question: str,
        candidates: List[Tuple[Dict, float]],
        top_k: int
    ) -> List[Tuple[Dict, float]]:
        """使用 CrossEncoder 对候选段落重排序"""
        if not self.cross_encoder or not candidates:
            return candidates[:top_k]

        # 如果候选集太大，可先取前N个进行重排序（例如 top_k * 10）
        if len(candidates) > top_k * 10:
            candidates = candidates[:top_k * 10]

        pairs = [(question, meta['text']) for meta, _ in candidates]
        scores = self.cross_encoder.predict(pairs)
        # 按得分降序排序
        sorted_idx = np.argsort(scores)[::-1][:top_k]
        results = [(candidates[i][0], scores[i]) for i in sorted_idx]
        logger.info(f"CrossEncoder 重排序完成，前 {top_k} 个得分: {[scores[i] for i in sorted_idx]}")
        return results

    # -------------------- 构建上下文和来源 --------------------
    def _build_context(self, results: List[Tuple[Dict, float]]) -> Tuple[str, List[Dict]]:
        context_parts = []
        sources = []
        for meta, score in results:
            if meta.get("text"):
                context_parts.append(meta["text"])
                source_item = {
                    "doc_name": meta.get("source", "未知"),
                    "chunk_text": meta["text"],
                    "score": float(score),
                    "chunk_index": meta.get("chunk_index"),
                    "article_number": meta.get("article_number"),
                    "part": meta.get("part"),
                    "chapter": meta.get("chapter"),
                    "section": meta.get("section"),
                    "area": meta.get("area"),
                }
                sources.append(source_item)
        context = "\n\n".join(context_parts)
        return context, sources

    # -------------------- 答案验证（引用检查）--------------------
    def _verify_citation(self, answer: str, sources: List[Dict]) -> Tuple[str, bool]:
        """
        验证答案中的引用是否都在 sources 中。
        返回 (修正后的答案, 是否合规)
        """
        cited_articles = re.findall(r'第一千[零一二三四五六七八九十百千万\d]+条', answer)
        available_articles = set()
        for src in sources:
            if 'article_number' in src:
                available_articles.add(src['article_number'])
        missing = [art for art in cited_articles if art not in available_articles]
        if missing:
            logger.warning(f"答案引用了未提供的条款: {missing}")
            return answer, False
        return answer, True

    # -------------------- 主要 ask 接口 --------------------
    def ask(
        self,
        question: str,
        top_k: int = 5,
        similarity_threshold: float = 0.0,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        max_tokens: Optional[int] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        logger.info(f"ASK: {question}, top_k={top_k}, threshold={similarity_threshold}")

        # ---------- 1. 检测法律领域和法律名称 ----------
        law_area = self._detect_law_area(question)
        law_type = self._detect_law_type(question)

        # 构造过滤条件：只使用 law_type
        filters = {}
        if law_type:
            filters["law_type"] = law_type
        if not filters:
            filters = None

        # ---------- 2. 混合检索（向量 + BM25）----------
        candidates = self._hybrid_retrieve(question, law_area, top_k, filters)

        if not candidates:
            logger.warning("未检索到任何相关文档")
            return "根据现有资料无法确定。", []

        # ---------- 3. CrossEncoder 重排序（可选）----------
        if self.use_cross_encoder:
            results = self._rerank_with_cross_encoder(question, candidates, top_k)
        else:
            results = candidates[:top_k]

        # ---------- 4. 构建上下文和来源 ----------
        context, sources = self._build_context(results)

        # ---------- 5. 构建历史文本 ----------
        history_text = ""
        if history:
            for msg in history:
                role = "用户" if msg["role"] == "user" else "助手"
                history_text += f"{role}：{msg['content']}\n"

        # ---------- 6. 构建提示词（注入领域信息）----------
        if law_area:
            system_prefix = f"你是一位精通中国法律中【{law_area}】领域的专家助手。"
        else:
            system_prefix = "你是一位精通中国法律的专家助手。"

        if system_prompt:
            try:
                prompt = system_prompt.replace("{history}", history_text).format(context=context, question=question)
            except KeyError as e:
                logger.error(f"自定义提示词缺少必要占位符: {e}")
                # 使用默认模板时，注意模板中只有 context 和 question，history 会被忽略
                prompt = self.default_prompt_template.format(context=context, question=question)
        else:
            prompt = self.default_prompt_template.format(context=context, question=question)

        prompt = system_prefix + "\n\n" + prompt

        # ---------- 7. 调用 LLM 生成答案 ----------
        if temperature is None:
            temperature = 0.0
        if max_tokens is None:
            max_tokens = 1024

        answer = self.llm.generate(
            prompt,
            temperature=temperature,
            top_p=top_p,
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
            max_tokens=max_tokens,
        )

        # ---------- 8. 验证引用（可选）----------
        # 修复点：正确解包返回值
        answer, _ = self._verify_citation(answer, sources)

        return answer, sources

