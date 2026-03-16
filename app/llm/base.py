# app/llm/base.py

from abc import ABC, abstractmethod

class LLM(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        根据 prompt 生成文本
        """
        pass
