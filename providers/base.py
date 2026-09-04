"""
Tüm LLM sağlayıcı adaptörlerinin uyması gereken ortak arayüz.
Yeni bir sağlayıcı eklemek için bu sınıfı miras alıp 3 metodu doldurmak yeterli.
"""
from abc import ABC, abstractmethod
from typing import Optional


class BaseProvider(ABC):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    @abstractmethod
    def build_request(self, prompt: str, stream: bool) -> tuple[str, dict, dict]:
        """(url, headers, json_body) döndürür."""
        raise NotImplementedError

    @abstractmethod
    def parse_stream_line(self, line: bytes) -> Optional[str]:
        """
        Streaming yanıtın tek bir satırından (SSE 'data: ...') metin
        parçasını (delta) çıkarır. İçerik yoksa None döner.
        """
        raise NotImplementedError

    @abstractmethod
    def parse_full_response(self, data: dict) -> str:
        """Streaming olmayan (tam) yanıttan asıl metni çıkarır."""
        raise NotImplementedError

    @abstractmethod
    def is_done_marker(self, line: bytes) -> bool:
        """Stream'in bittiğini belirten satır mı? (örn. OpenAI'da 'data: [DONE]')"""
        raise NotImplementedError

    def extract_completion_tokens(self, data: dict) -> Optional[int]:
        """
        Streaming olmayan tam yanıttan sağlayıcının bildirdiği KESİN
        completion/output token sayısını okur. Sağlayıcı bunu desteklemiyorsa
        veya alan yoksa None döner (bu durumda tokenizer.count_tokens ile
        yaklaşık hesaplamaya düşülür). Alt sınıflar override eder.
        """
        return None
