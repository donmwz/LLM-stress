from typing import Optional

try:
    import tiktoken
    _encoder = tiktoken.get_encoding("cl100k_base")
except Exception:
    _encoder = None


def count_tokens(text: Optional[str]) -> int:
    """Metnin YAKLAŞIK token sayısını döndürür (kesin usage verisi yoksa kullan)."""
    if not text:
        return 0
    if _encoder is not None:
        try:
            return len(_encoder.encode(text))
        except Exception:
            pass
    # Kaba fallback: ortalama ~4 karakter/token
    return max(1, len(text) // 4)
