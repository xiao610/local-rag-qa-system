import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from typing import Optional
from app.llm.base import LLM
from app.utils.logger import logger

class HFModel(LLM):
    def __init__(
        self,
        model_name: str = "Qwen/Qwen2.5-1.5B-Instruct",
        device: str = "cuda",
        use_fp16: bool = True,
        load_in_8bit: bool = False,
        load_in_4bit: bool = False,
        max_new_tokens: int = 512,
        temperature: float = 0.1,
    ):
        self.device = device if torch.cuda.is_available() and device == "cuda" else "cpu"
        self.use_fp16 = use_fp16 and self.device == "cuda"
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature

        # 量化配置
        quantization_config = None
        if load_in_8bit and self.device == "cuda":
            quantization_config = BitsAndBytesConfig(load_in_8bit=True)
        elif load_in_4bit and self.device == "cuda":
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )

        logger.info(f"Loading model {model_name} on {self.device}...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            device_map="auto" if self.device == "cuda" else None,
            torch_dtype=torch.float16 if self.use_fp16 else torch.float32,
            quantization_config=quantization_config,
            trust_remote_code=True,
        )
        if self.device == "cpu":
            self.model = self.model.to("cpu")
        self.model.eval()
        logger.info("Model loaded successfully.")

    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens or self.max_new_tokens,
                temperature=temperature or self.temperature,
                do_sample=(temperature or self.temperature) > 0,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        answer = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        # 去除输入部分（保留生成部分）
        if answer.startswith(prompt):
            answer = answer[len(prompt):].lstrip()
        return answer