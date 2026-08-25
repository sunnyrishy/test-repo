from __future__ import annotations

import httpx

from app.services.ai.base import AIError, AIProvider, AIRequest

API_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(AIProvider):
    name = "openai"

    async def complete(self, request: AIRequest) -> str:
        if not self.api_key:
            raise AIError("openai: AI_API_KEY is not set")
        payload = {
            "model": self.model,
            "max_completion_tokens": request.max_output_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    API_URL,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
            except httpx.HTTPError as exc:
                raise AIError(f"openai: {exc}") from exc
        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIError(f"openai: unexpected response shape: {body}") from exc
