"""Provider-agnostic LLM interface.

Business logic never imports a vendor SDK; it asks the configured provider for
JSON and validates the result itself.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass


class AIError(RuntimeError):
    """The provider could not be reached or returned an unusable response."""


@dataclass(slots=True)
class AIRequest:
    system_prompt: str
    user_prompt: str
    max_output_tokens: int = 1500


class AIProvider(abc.ABC):
    """Returns raw model text; parsing and validation happen upstream."""

    name: str

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    @abc.abstractmethod
    async def complete(self, request: AIRequest) -> str:
        """Return the model's raw response text for a JSON-only prompt."""
