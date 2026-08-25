from app.config import Settings
from app.services.ai.anthropic_provider import AnthropicProvider
from app.services.ai.base import AIError, AIProvider, AIRequest
from app.services.ai.mock_provider import MockProvider
from app.services.ai.openai_provider import OpenAIProvider

PROVIDERS: dict[str, type[AIProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "mock": MockProvider,
}


def build_provider(settings: Settings) -> AIProvider:
    """Instantiate the configured provider. Swapping models never touches
    business logic - only AI_PROVIDER and AI_MODEL."""
    try:
        provider_cls = PROVIDERS[settings.ai_provider.lower()]
    except KeyError:
        raise AIError(
            f"unknown AI_PROVIDER {settings.ai_provider!r}; "
            f"expected one of {sorted(PROVIDERS)}"
        ) from None
    if provider_cls is not MockProvider and not settings.ai_model:
        raise AIError(f"AI_MODEL must be set for provider {settings.ai_provider}")
    return provider_cls(settings.ai_api_key, settings.ai_model or "mock")


__all__ = ["AIError", "AIProvider", "AIRequest", "build_provider", "PROVIDERS"]
