"""DeepSeek LLM adapter.

DeepSeek provides OpenAI-compatible API at https://api.deepseek.com
Models:
- deepseek-chat: Fast general-purpose model (DeepSeek V3)
- deepseek-reasoner: Reasoning model (DeepSeek R1) for complex tasks
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from src.config import get_settings
from src.schemas import LLMMessage, LLMResponse
from src.llm.base import LLMAdapter


class DeepSeekAdapter(LLMAdapter):
    """DeepSeek API adapter using OpenAI-compatible endpoint."""
    
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 120.0,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.deepseek_api_key
        self.base_url = base_url or settings.deepseek_base_url
        self.default_model = settings.deepseek_model_chat
        self.reasoner_model = settings.deepseek_model_reasoner
        self.timeout = timeout
        
        if not self.api_key:
            raise ValueError("DeepSeek API key not configured")
        
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )
    
    @property
    def provider_name(self) -> str:
        return "deepseek"
    
    @property
    def available_models(self) -> list[str]:
        return ["deepseek-chat", "deepseek-reasoner"]
    
    async def chat_completion(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, str] | None = None,
    ) -> LLMResponse:
        """Send chat completion request to DeepSeek API."""
        model = model or self.default_model
        
        payload = self._build_request(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            response_format=response_format,
        )
        
        start_time = time.perf_counter()
        
        try:
            response = await self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            return LLMResponse(
                content=None,
                model=model,
                usage={},
                finish_reason="error",
                raw_response={"error": str(e), "status_code": e.response.status_code},
            )
        except Exception as e:
            return LLMResponse(
                content=None,
                model=model,
                usage={},
                finish_reason="error",
                raw_response={"error": str(e)},
            )
        
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        
        # Parse response
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        
        return LLMResponse(
            content=message.get("content"),
            tool_calls=message.get("tool_calls"),
            model=data.get("model", model),
            usage=data.get("usage", {}),
            finish_reason=choice.get("finish_reason"),
            raw_response=data,
        )
    
    async def health_check(self) -> bool:
        """Check if DeepSeek API is accessible."""
        try:
            response = await self._client.post(
                "/chat/completions",
                json={
                    "model": self.default_model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                },
            )
            return response.status_code == 200
        except Exception:
            return False
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
