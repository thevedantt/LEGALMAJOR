import requests
from backend.core.config import Config

class LLMClient:
    def __init__(self, base_url=None, model_name=None):
        self.base_url = base_url or Config.LLM_URL
        self.model_name = model_name or Config.MODEL_NAME

    def generate(self, prompt: str) -> str:
        url = self.base_url
        try:
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": Config.LLM_TEMPERATURE,
                "max_tokens": Config.MAX_TOKENS
            }
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"[LLM Error: {e}]"