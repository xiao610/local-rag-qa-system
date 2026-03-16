# app/llm/ollama.py
import requests
import re
from typing import Optional
from app.llm.base import LLM
from app.config import OLLAMA_URL, OLLAMA_MODEL

class OllamaLLM(LLM):
    def __init__(self, model_name: str = OLLAMA_MODEL):
        self.model_name = model_name
        self.api_url = f"{OLLAMA_URL}/api/generate"

    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        max_tokens: Optional[int] = None,
        extract_answer: bool = False,   # 是否提取最终答案（用于推理模型）
        format_json: bool = False,       # 是否要求返回 JSON 格式
    ) -> str:
        """
        调用 Ollama 生成回答，支持传递生成参数。
        - extract_answer: 如果为 True，尝试从响应中提取 <think> 标签之外的最终答案。
        - format_json: 如果为 True，在请求中设置 format: json，强制模型输出 JSON 格式。
        """
        # 构建 options 字典
        options = {}
        if temperature is not None:
            options["temperature"] = temperature
        if top_p is not None:
            options["top_p"] = top_p
        if presence_penalty is not None:
            options["presence_penalty"] = presence_penalty
        if frequency_penalty is not None:
            options["frequency_penalty"] = frequency_penalty
        if max_tokens is not None:
            options["num_predict"] = max_tokens  # Ollama 字段名为 num_predict

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
        }
        if options:
            payload["options"] = options
        if format_json:
            payload["format"] = "json"  # 要求返回 JSON

        try:
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            data = response.json()
            full_response = data.get("response", "").strip()

            # 如果需要提取最终答案，则尝试去除 <think> 标签
            if extract_answer:
                # 匹配最后一个 </think> 之后的内容
                match = re.search(r'</think>\s*(.*?)$', full_response, re.DOTALL)
                if match:
                    answer = match.group(1).strip()
                    return answer if answer else full_response
                else:
                    return full_response
            else:
                return full_response
        except Exception as e:
            print(f"LLM request failed: {e}")
            return "对不起，回答生成失败。"