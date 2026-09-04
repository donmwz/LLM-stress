import json
from typing import Optional
from .base import BaseProvider


class OpenAIProvider(BaseProvider):
    """OpenAI Chat Completions API (/v1/chat/completions)."""

    BASE_URL = "https://api.openai.com/v1/chat/completions"

    def build_request(self, prompt: str, stream: bool) -> tuple[str, dict, dict]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": stream,
        }
        return self.BASE_URL, headers, body

    def is_done_marker(self, line: bytes) -> bool:
        return line.strip() == b"data: [DONE]"

    def parse_stream_line(self, line: bytes) -> Optional[str]:
        text = line.decode("utf-8", errors="ignore").strip()
        if not text.startswith("data:"):
            return None
        payload = text[len("data:"):].strip()
        if payload == "[DONE]":
            return None
        try:
            data = json.loads(payload)
            return data["choices"][0]["delta"].get("content")
        except Exception:
            return None

    def parse_full_response(self, data: dict) -> str:
        return data["choices"][0]["message"]["content"]

    def extract_completion_tokens(self, data: dict) -> Optional[int]:
        return data.get("usage", {}).get("completion_tokens")


class GrokProvider(OpenAIProvider):
    """xAI Grok - OpenAI-uyumlu Chat Completions API."""

    BASE_URL = "https://api.x.ai/v1/chat/completions"


class OpenRouterProvider(OpenAIProvider):
    """OpenRouter'ın OpenAI-uyumlu Chat Completions API adaptörü."""

    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def build_request(self, prompt: str, stream: bool) -> tuple[str, dict, dict]:
        url, headers, body = super().build_request(prompt, stream)
        headers.update({
            "HTTP-Referer": "http://localhost:8501",
            "X-OpenRouter-Title": "LLM Stress Lab",
        })
        return url, headers, body
