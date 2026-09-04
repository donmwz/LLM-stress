
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List


class RequestStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"


@dataclass
class TestConfig:
    """Bir yük testi koşusu için tüm parametreler."""

    provider: str                  # "openrouter" | "openai" | "anthropic" | "gemini" | "grok"
    api_key: str
    model: str                     # örn: "gpt-4o", "claude-sonnet-4-6", "gemini-1.5-pro", "grok-2"
    prompt: str                    # sabit test prompt'u
    prompts: Optional[List[str]] = None  # verilirse round-robin kullanılır, prompt alanı yok sayılır

    concurrency: int = 5           # aynı anda kaç istek
    total_requests: int = 20       # toplam istek sayısı

    stream: bool = True            # streaming (TTFT ölçümü için önerilir)
    timeout: float = 60.0          # saniye

    ramp_up: bool = False          # True ise istekler kademeli başlatılır
    ramp_up_delay: float = 0.5     # ramp_up=True iken istekler arası gecikme (sn)

    save_responses: bool = False   # LLM çıktı metinlerini sonuçlara dahil et


@dataclass
class RequestResult:
    """Tek bir isteğin ham zamanlama ve sonuç verisi (metrik hesaplama FAZ 2'de)."""

    request_id: int
    status: RequestStatus = RequestStatus.ERROR

    t0: Optional[float] = None     # istek gönderim anı (perf_counter)
    t1: Optional[float] = None     # ilk token/byte alınma anı
    t2: Optional[float] = None     # yanıt tamamlanma anı

    status_code: Optional[int] = None
    error_message: Optional[str] = None

    output_text: Optional[str] = None      # save_responses=True ise dolu
    token_count: Optional[int] = None      # kaba tahmin (FAZ 2'de gerçek tokenizer eklenecek)

    @property
    def ttft_ms(self) -> Optional[float]:
        if self.t0 is None or self.t1 is None:
            return None
        return (self.t1 - self.t0) * 1000

    @property
    def total_ms(self) -> Optional[float]:
        if self.t0 is None or self.t2 is None:
            return None
        return (self.t2 - self.t0) * 1000
