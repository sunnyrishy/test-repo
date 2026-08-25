from __future__ import annotations

import httpx

from app.services.ai.base import AIError, AIProvider, AIRequest

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"


class AnthropicProvider(AIProvider):
    name = "anthropic"

    async def complete(self, request: AIRequest) -> str:
        if not self.api_key:
            raise AIError("anthropic: AI_API_KEY is not set")
        payload = {
            "model": self.model,
            "max_tokens": request.max_output_tokens,
            "system": request.system_prompt,
            "messages": [{"role": "user", "content": request.user_prompt}],
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    API_URL,
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": API_VERSION,
                    },
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
            except httpx.HTTPError as exc:
                raise AIError(f"anthropic: {exc}") from exc
        try:
            return "".join(
                block["text"] for block in body["content"] if block.get("type") == "text"
            )
        except (KeyError, TypeError) as exc:
            raise AIError(f"anthropic: unexpected response shape: {body}") from exc
