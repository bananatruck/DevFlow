"""LLM Router for model selection and fallback logic.

Strategy:
- Plan/Checklist: Use cheaper model (DeepSeek-chat)
- Execute/Repair: Use reasoning model (DeepSeek-reasoner or Kimi)
- On failure: Fallback to alternate provider
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from src.config import get_settings
from src.schemas import LLMMessage, LLMResponse, StepName
from src.llm.base import LLMAdapter
from src.llm.deepseek import DeepSeekAdapter
from src.llm.kimi import KimiAdapter


logger = logging.getLogger(__name__)


class ModelRouter:
    """Routes LLM requests to appropriate providers with fallback logic."""
    
    # Step-to-model mapping (what model should be used for each step)
    STEP_MODEL_MAP: dict[str, str] = {
        StepName.PLAN.value: "fast",       # Use fast model for planning
        StepName.CHECKLIST.value: "fast",  # Use fast model for checklist
        StepName.EXECUTE.value: "reasoning",  # Use reasoning for code
        StepName.VALIDATE.value: "fast",   # Use fast for validation
        StepName.SUMMARY.value: "fast",    # Use fast for summary
    }
    
    def __init__(self):
        settings = get_settings()
        self.primary_provider = settings.primary_provider
        self.fallback_provider = settings.fallback_provider
        
        # Initialize adapters lazily
        self._adapters: dict[str, LLMAdapter] = {}
        self._settings = settings
    
    def _get_adapter(self, provider: str) -> LLMAdapter:
        """Get or create an adapter for a provider."""
        if provider not in self._adapters:
            if provider == "deepseek":
                self._adapters["deepseek"] = DeepSeekAdapter()
            elif provider == "kimi":
                self._adapters["kimi"] = KimiAdapter()
            else:
                raise ValueError(f"Unknown provider: {provider}")
        return self._adapters[provider]
    
    def _get_model_for_step(
        self,
        step: str,
        model_type: Literal["fast", "reasoning"] | None = None,
    ) -> tuple[str, str]:
        """Get provider and model name for a step.
        
        Returns:
            Tuple of (provider, model_name)
        """
        # Determine model type from step if not specified
        if model_type is None:
            model_type = self.STEP_MODEL_MAP.get(step, "fast")
        
        # Get model based on primary provider
        if self.primary_provider == "deepseek":
            if model_type == "reasoning":
                return ("deepseek", self._settings.deepseek_model_reasoner)
            return ("deepseek", self._settings.deepseek_model_chat)
        else:  # kimi
            return ("kimi", self._settings.kimi_model)
    
    async def chat_completion(
        self,
        messages: list[LLMMessage],
        step: str = "EXECUTE",
        model_type: Literal["fast", "reasoning"] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, str] | None = None,
        allow_fallback: bool = True,
    ) -> tuple[LLMResponse, str, str]:
        """Route a chat completion request with fallback.
        
        Args:
            messages: Conversation messages
            step: Current workflow step
            model_type: Override for model type selection
            temperature: Sampling temperature
            max_tokens: Max response tokens
            tools: Tool definitions
            response_format: Response format config
            allow_fallback: Whether to try fallback on failure
            
        Returns:
            Tuple of (response, provider_used, model_used)
        """
        provider, model = self._get_model_for_step(step, model_type)
        
        logger.info(f"Routing {step} to {provider}/{model}")
        
        try:
            adapter = self._get_adapter(provider)
            response = await adapter.chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                response_format=response_format,
            )
            
            # Check if request failed
            if response.finish_reason == "error" and allow_fallback:
                logger.warning(f"Primary provider {provider} failed, trying fallback")
                return await self._try_fallback(
                    messages=messages,
                    step=step,
                    model_type=model_type,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=tools,
                    response_format=response_format,
                )
            
            return (response, provider, model)
            
        except Exception as e:
            logger.error(f"Error with {provider}: {e}")
            if allow_fallback:
                return await self._try_fallback(
                    messages=messages,
                    step=step,
                    model_type=model_type,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=tools,
                    response_format=response_format,
                )
            raise
    
    async def _try_fallback(
        self,
        messages: list[LLMMessage],
        step: str,
        model_type: Literal["fast", "reasoning"] | None,
        temperature: float,
        max_tokens: int,
        tools: list[dict[str, Any]] | None,
        response_format: dict[str, str] | None,
    ) -> tuple[LLMResponse, str, str]:
        """Try the fallback provider."""
        fallback_provider = self.fallback_provider
        
        # Get model for fallback provider
        if fallback_provider == "deepseek":
            if model_type == "reasoning":
                model = self._settings.deepseek_model_reasoner
            else:
                model = self._settings.deepseek_model_chat
        else:
            model = self._settings.kimi_model
        
        logger.info(f"Falling back to {fallback_provider}/{model}")
        
        adapter = self._get_adapter(fallback_provider)
        response = await adapter.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            response_format=response_format,
        )
        
        return (response, fallback_provider, model)
    
    async def close(self) -> None:
        """Close all adapters."""
        for adapter in self._adapters.values():
            await adapter.close()


# Singleton instance
_router: ModelRouter | None = None


def get_router() -> ModelRouter:
    """Get the global model router instance."""
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
