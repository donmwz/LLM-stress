import json
from typing import Optional
from .base import BaseProvider


class GeminiProvider(BaseProvider):
    """
    Google Gemini API (generateContent / streamGenerateContent).
    API key query param olarak gönderilir.
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def build_request(self, prompt: str, stream: bool) -> tuple[str, dict, dict]:
        method = "streamGenerateContent" if stream else "generateContent"
        alt = "&alt=sse" if stream else ""
        url = f"{self.BASE_URL}/{self.model}:{method}?key={self.api_key}{alt}"
        headers = {"Content-Type": "application/json"}
        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}]
        }
        return url, headers, body

    def is_done_marker(self, line: bytes) -> bool:
        # Gemini SSE akışında OpenAI tarzı [DONE] yok; stream kapandığında biter.
        return False

    def parse_stream_line(self, line: bytes) -> Optional[str]:
        text = line.decode("utf-8", errors="ignore").strip()
        if not text.startswith("data:"):
            return None
        payload = text[len("data:"):].strip()
        try:
            data = json.loads(payload)
            candidates = data.get("candidates", [])
            if not candidates:
                return None
            parts = candidates[0].get("content", {}).get("parts", [])
            return "".join(p.get("text", "") for p in parts) or None
        except Exception:
            return None

    def parse_full_response(self, data: dict) -> str:
        candidates = data.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts)

    def extract_completion_tokens(self, data: dict) -> Optional[int]:
        return data.get("usageMetadata", {}).get("candidatesTokenCount")
