from app.config import LLM_TYPE

def create_llm():
    if LLM_TYPE == "ollama":
        from .ollama import OllamaLLM
        return OllamaLLM()
    elif LLM_TYPE == "hf":
        from .hf_model import HFModel
        from app.config import (
            HF_MODEL_NAME, HF_USE_FP16,
            HF_LOAD_IN_8BIT, HF_LOAD_IN_4BIT,
            HF_MAX_NEW_TOKENS, HF_TEMPERATURE
        )
        return HFModel(
            model_name=HF_MODEL_NAME,
            use_fp16=HF_USE_FP16,
            load_in_8bit=HF_LOAD_IN_8BIT,
            load_in_4bit=HF_LOAD_IN_4BIT,
            max_new_tokens=HF_MAX_NEW_TOKENS,
            temperature=HF_TEMPERATURE,
        )
    else:
        raise ValueError(f"Unknown LLM type: {LLM_TYPE}")