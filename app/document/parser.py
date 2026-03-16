import re
from typing import List
from app.utils.logger import logger


class DocumentParser:
    """
    文本解析与清洗模块（RAG 友好版本）
    只去噪，不破坏语义结构
    """

    def __init__(self):
        logger.info("DocumentParser initialized")

    def parse(self, text: str) -> str:
        # 1️⃣ 统一换行符（Windows / PDF 常见问题）
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 2️⃣ 去掉 PDF 解析产生的奇怪空字符
        text = re.sub(r"[ \t]+", " ", text)

        # 3️⃣ 修复“被错误断开的句子”
        # 例如：
        # 本合同的订立\n应当遵守 → 合并
        text = re.sub(r"(?<!\n)\n(?!\n)", "", text)

        # 4️⃣ 保留段落（连续两个换行才视为段落）
        text = re.sub(r"\n{3,}", "\n\n", text)

        # 5️⃣ 去掉不可见控制字符（但保留换行）
        text = "".join(c for c in text if c.isprintable() or c == "\n")

        # 6️⃣ 去除首尾空白
        text = text.strip()

        return text

    def parse_list(self, texts: List[str]) -> List[str]:
        return [self.parse(t) for t in texts]
