from .base import BaseProvider
from .openai_provider import OpenAIProvider, GrokProvider, OpenRouterProvider
from .anthropic_provider import AnthropicProvider
from .gemini_provider import GeminiProvider

_REGISTRY = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
    "grok": GrokProvider,
    "openrouter": OpenRouterProvider,
}


def get_provider(name: str, api_key: str, model: str) -> BaseProvider:
    key = name.strip().lower()
    if key not in _REGISTRY:
        raise ValueError(
            f"Bilinmeyen provider: '{name}'. Desteklenenler: {list(_REGISTRY.keys())}"
        )
    return _REGISTRY[key](api_key=api_key, model=model)
