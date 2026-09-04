import json
from typing import Optional
from .base import BaseProvider


class AnthropicProvider(BaseProvider):
    """Anthropic Messages API (/v1/messages)."""

    BASE_URL = "https://api.anthropic.com/v1/messages"
    ANTHROPIC_VERSION = "2023-06-01"

    def build_request(self, prompt: str, stream: bool) -> tuple[str, dict, dict]:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        body = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
            "stream": stream,
        }
        return self.BASE_URL, headers, body

    def is_done_marker(self, line: bytes) -> bool:
        text = line.decode("utf-8", errors="ignore").strip()
        return text == "event: message_stop"

    def parse_stream_line(self, line: bytes) -> Optional[str]:
        text = line.decode("utf-8", errors="ignore").strip()
        if not text.startswith("data:"):
            return None
        payload = text[len("data:"):].strip()
        try:
            data = json.loads(payload)
            if data.get("type") == "content_block_delta":
                return data.get("delta", {}).get("text")
        except Exception:
            return None
        return None

    def parse_full_response(self, data: dict) -> str:
        blocks = data.get("content", [])
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")

    def extract_completion_tokens(self, data: dict) -> Optional[int]:
        return data.get("usage", {}).get("output_tokens")
