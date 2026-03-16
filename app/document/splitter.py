import re
from typing import List, Tuple, Optional, Dict
from app.utils.logger import logger
from app.config import CHUNK_SIZE, CHUNK_OVERLAP

from langchain_text_splitters import RecursiveCharacterTextSplitter
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Element


class TextSplitter:
    """
    智能文本切分器，支持：
    - 通用模式：使用 LangChain 递归分割器（支持自定义分隔符、正则）
    - 法律条款专用模式：精准按“第X条”切分，再按次级分隔符细粒度切分
    """
    def __init__(
            self,
            chunk_size: int = CHUNK_SIZE,
            chunk_overlap: int = CHUNK_OVERLAP,
            separators: Optional[List[str]] = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # ---------- 检测是否为法律条款模式 ----------
        # 特征：分隔符列表包含 "第.*条" 或类似的正则条款标记
        self.is_article_mode = False
        self.article_pattern = None
        self.fallback_separators = []

        if separators and len(separators) > 0:
            # 检查第一个分隔符是否为条款正则
            first_sep = separators[0]
            # 常见法律条款正则特征：包含 "第" 和 "条"，且有正则元字符
            if ("第" in first_sep and "条" in first_sep and
                    any(c in first_sep for c in '.^$*+?{}[]\\|()')):
                self.is_article_mode = True
                self.article_pattern = first_sep
                # 剩余分隔符作为条款内部的次级切分依据
                self.fallback_separators = separators[1:] if len(separators) > 1 else []
                logger.info(f"⚖️ 启用法律条款专用切分模式")
                logger.info(f"   条款正则: {self.article_pattern}")
                logger.info(f"   次级分隔符: {self.fallback_separators}")
                return

        # ---------- 非条款模式：使用 LangChain 递归分割器 ----------
        # 默认分隔符（针对中文优化）
        default_separators = [
            "\n\n", "\n", "。", "！", "？", "；", "，", " ", ""
        ]

        if separators is None:
            # 未传入分隔符 → 使用默认分隔符
            self.splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=default_separators,
                keep_separator=False,
                is_separator_regex=False,
            )
            logger.info(f"📄 使用默认分隔符: {default_separators}")
            return

        # 自定义分隔符（非条款模式）
        # 自动补充 Windows 换行符
        if "\n" in separators and "\r\n" not in separators:
            idx = separators.index("\n")
            separators.insert(idx, "\r\n")
            logger.info("🪟 自动补充 Windows 换行符 \\r\\n")

        # 检测是否需要正则模式
        regex_chars = set('.^$*+?{}[]\\|()')
        need_regex = any(
            any(c in sep for c in regex_chars)
            for sep in separators if sep
        )

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=separators,
            keep_separator=False,
            is_separator_regex=need_regex,
        )
        logger.info(
            f"🔧 自定义分隔符（通用模式）: {separators}\n"
            f"   块大小: {chunk_size}, 重叠: {chunk_overlap}\n"
            f"   正则模式: {need_regex}"
        )

    # ---------- 法律条款专用切分方法 ----------
    def _split_articles(self, text: str) -> List[str]:
        """按法律条款切分，并控制块大小"""
        if not self.article_pattern:
            return [text]

        # 编译条款正则（非贪婪匹配，避免跨条款吞噬）
        # 例如：第[零一二三四五六七八九十百千万\d]+条
        pattern = re.compile(self.article_pattern, re.MULTILINE)

        # 查找所有条款位置
        matches = list(pattern.finditer(text))
        if not matches:
            logger.warning("未找到任何条款，回退到普通切分")
            # 回退到按换行符切分（兼容 Windows）
            return [line.strip() for line in text.splitlines() if line.strip()]

        # 按条款位置切分文本，保留条款标题
        article_parts = []
        prev_end = 0
        for match in matches:
            start, end = match.span()
            # 条款前的文本（通常是空白或无效内容）
            if start > prev_end:
                prefix = text[prev_end:start].strip()
                if prefix:
                    article_parts.append(prefix)
            # 条款本身（包含标题）
            article_parts.append(text[start:end].strip())
            prev_end = end
        # 剩余文本
        if prev_end < len(text):
            suffix = text[prev_end:].strip()
            if suffix:
                article_parts.append(suffix)

        # 将条款合并成块，控制块大小
        chunks = []
        current_chunk = ""

        for part in article_parts:
            # 如果当前块加上这一部分仍然不超过 chunk_size
            if len(current_chunk) + len(part) <= self.chunk_size:
                current_chunk += part
            else:
                # 当前块已满，保存
                if current_chunk:
                    chunks.append(current_chunk)
                # 处理超长条款（自身超过 chunk_size）
                if len(part) > self.chunk_size:
                    # 使用次级分隔符递归切分该条款
                    sub_chunks = self._split_long_text(part, self.fallback_separators)
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = part

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _split_long_text(self, text: str, separators: List[str]) -> List[str]:
        """递归切分长文本（用于超长条款）"""
        if not separators:
            # 无分隔符时，按 chunk_size 硬切
            return [text[i:i + self.chunk_size] for i in range(0, len(text), self.chunk_size - self.chunk_overlap)]

        sep = separators[0]
        parts = text.split(sep)
        result = []
        for part in parts:
            if not part.strip():
                continue
            if len(part) <= self.chunk_size:
                result.append(part.strip())
            else:
                # 递归使用下一个分隔符
                result.extend(self._split_long_text(part, separators[1:]))
        return result

    # ---------- 统一对外接口 ----------
    def split_text(self, text: str) -> List[str]:
        """切分单篇文本"""
        if self.is_article_mode:
            chunks = self._split_articles(text)
            logger.info(f"✂️ 法律条款切分: 生成 {len(chunks)} 个文本块")
            return chunks

        # 通用模式
        chunks = self.splitter.split_text(text)
        chunks = [chunk.strip() for chunk in chunks if chunk and chunk.strip()]
        logger.info(f"✂️ 通用切分: 生成 {len(chunks)} 个文本块")
        return chunks

    def split_documents(
            self, docs: List[Tuple[str, str]]
    ) -> List[Tuple[str, int, str]]:
        all_chunks = []
        for doc_name, text in docs:
            chunks = self.split_text(text)
            for idx, chunk in enumerate(chunks):
                all_chunks.append((doc_name, idx, chunk))
        logger.info(f"📚 总计 {len(all_chunks)} 个文本块（来自 {len(docs)} 个文档）")
        return all_chunks


# ========== 新增的法律条款分块器（基于Unstructured） ==========
class UnstructuredArticleSplitter:
    """
    法律条款专用分块器（基于 Unstructured）
    先用 by_title 按标题（编、章、节）切分，保留标题元数据，
    再对每个标题块按条款正则二次切分，保证条款完整性。
    输出格式：(doc_name, chunk_index, chunk_text, metadata)
    """
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        # 条款正则（用于二次切分）
        self.article_pattern = re.compile(r'第[零一二三四五六七八九十百千万\d]+条')

    def split_documents(
        self, docs: List[Tuple[str, List[Element]]]
    ) -> List[Tuple[str, int, str, Dict]]:
        all_chunks = []
        for doc_name, elements in docs:
            # 1. 按标题分块（by_title）
            title_chunks = chunk_by_title(
                elements,
                max_characters=self.chunk_size * 2,  # 适当放大，避免跨块
                overlap=self.chunk_overlap,
                combine_text_under_n_chars=self.chunk_size,
            )
            for title_chunk in title_chunks:
                # 提取标题块的元数据
                header_meta = title_chunk.metadata.to_dict() if title_chunk.metadata else {}
                # 获取合并后的文本（CompositeElement 通常有 text 属性）
                combined_text = title_chunk.text if hasattr(title_chunk, 'text') else str(title_chunk)

                # 2. 按条款正则二次切分
                matches = list(self.article_pattern.finditer(combined_text))
                if not matches:
                    # 没有条款，直接作为一个块
                    all_chunks.append((doc_name, len(all_chunks), combined_text, header_meta))
                else:
                    last_end = 0
                    for match in matches:
                        start, end = match.span()
                        # 条款前的内容
                        if start > last_end:
                            prefix = combined_text[last_end:start].strip()
                            if prefix:
                                all_chunks.append((doc_name, len(all_chunks), prefix, header_meta))
                        # 条款本身
                        article_text = combined_text[start:end].strip()
                        all_chunks.append((doc_name, len(all_chunks), article_text, header_meta))
                        last_end = end
                    # 剩余内容
                    if last_end < len(combined_text):
                        suffix = combined_text[last_end:].strip()
                        if suffix:
                            all_chunks.append((doc_name, len(all_chunks), suffix, header_meta))
        logger.info(f"UnstructuredArticleSplitter 生成 {len(all_chunks)} 个文本块")
        return all_chunks