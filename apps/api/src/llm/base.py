"""Abstract base class for LLM adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.schemas import LLMMessage, LLMRequest, LLMResponse


class LLMAdapter(ABC):
    """Abstract base class for LLM provider adapters.
    
    All LLM providers (DeepSeek, Kimi, etc.) implement this interface
    to ensure consistent behavior across providers.
    """
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'deepseek', 'kimi')."""
        ...
    
    @property
    @abstractmethod
    def available_models(self) -> list[str]:
        """Return list of available model names for this provider."""
        ...
    
    @abstractmethod
    async def chat_completion(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, str] | None = None,
    ) -> LLMResponse:
        """Send a chat completion request.
        
        Args:
            messages: List of conversation messages
            model: Model name (uses default if None)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            tools: Optional list of tool definitions for function calling
            response_format: Optional response format (e.g., {"type": "json_object"})
            
        Returns:
            LLMResponse with content and/or tool calls
        """
        ...
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider API is accessible.
        
        Returns:
            True if API is accessible, False otherwise
        """
        ...
    
    def _build_request(
        self,
        messages: list[LLMMessage],
        model: str,
        temperature: float,
        max_tokens: int,
        tools: list[dict[str, Any]] | None,
        response_format: dict[str, str] | None,
    ) -> dict[str, Any]:
        """Build the API request payload.
        
        This is a helper method that subclasses can use or override.
        """
        payload: dict[str, Any] = {
            "model": model,
            "messages": [m.model_dump(exclude_none=True) for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if tools:
            payload["tools"] = tools
            
        if response_format:
            payload["response_format"] = response_format
            
        return payload
