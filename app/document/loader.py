import os
from pathlib import Path
from typing import List, Tuple

# 导入 Unstructured 相关模块（仅用于 PDF/DOCX）
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.docx import partition_docx
from unstructured.documents.elements import Element, NarrativeText

from app.config import DOC_DIR
from app.utils.logger import logger


class DocumentLoader:
    SUPPORTED_EXT = [".pdf", ".txt", ".docx"]

    def __init__(self, storage_dir: Path = DOC_DIR):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"DocumentLoader initialized, storage_dir={self.storage_dir}")

    # ---------- 原有方法：返回纯文本（用于通用模式）----------
    def load_file(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.SUPPORTED_EXT:
            raise ValueError(f"不支持的文件类型: {ext}")

        if ext == ".pdf":
            return self._load_pdf(file_path)
        elif ext == ".txt":
            return self._load_txt(file_path)
        elif ext == ".docx":
            return self._load_docx(file_path)

    def load_files(self, file_paths: List[str]) -> List[Tuple[str, str]]:
        results = []
        for f in file_paths:
            try:
                text = self.load_file(f)
                results.append((os.path.basename(f), text))
                logger.info(f"Loaded file: {f}, length={len(text)}")
            except Exception as e:
                logger.error(f"加载文件失败 {f}: {e}")
        return results

    # ---------- 新增方法：返回 Unstructured 元素列表（用于法律条款模式）----------
    def load_file_as_elements(self, file_path: str) -> List[Element]:
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.SUPPORTED_EXT:
            raise ValueError(f"不支持的文件类型: {ext}")

        if ext == ".pdf":
            return partition_pdf(filename=file_path, strategy="auto")
        elif ext == ".docx":
            return partition_docx(filename=file_path)
        elif ext == ".txt":
            # 手动处理 TXT 文件：读取文本，按段落拆分为多个 NarrativeText 元素
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            # 按两个换行符切分段落，保留段落结构
            paragraphs = text.split("\n\n")
            elements = [NarrativeText(text=p.strip()) for p in paragraphs if p.strip()]
            if not elements:
                # 如果没有段落，则整个作为一个元素
                elements = [NarrativeText(text=text)]
            return elements
        else:
            raise ValueError(f"不支持的文件类型: {ext}")

    def load_files_as_elements(self, file_paths: List[str]) -> List[Tuple[str, List[Element]]]:
        results = []
        for f in file_paths:
            try:
                elements = self.load_file_as_elements(f)
                results.append((os.path.basename(f), elements))
                logger.info(f"Loaded file as elements: {f}, {len(elements)} elements")
            except Exception as e:
                logger.error(f"加载文件失败 {f}: {e}")
        return results

    # ---------- 原有的具体解析方法（保持不变）----------
    def _load_pdf(self, file_path: str) -> str:
        elements = partition_pdf(
            filename=file_path,
            strategy="auto",
            extract_images_in_pdf=False,
            infer_table_structure=False,
        )
        return "\n\n".join([str(el) for el in elements])

    def _load_docx(self, file_path: str) -> str:
        elements = partition_docx(filename=file_path)
        return "\n\n".join([str(el) for el in elements])

    def _load_txt(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()