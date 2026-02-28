"""
LLM Client Abstraction

Provides unified interface for Anthropic Claude and OpenAI.
Handles provider switching and fallback.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import json
import logging

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GEMINI = "gemini"


class ModelTier(str, Enum):
    REASONING = "reasoning"  # Opus/GPT-4 - for complex analysis
    EXPLANATION = "explanation"  # Haiku/GPT-3.5 - for summaries


@dataclass
class LLMConfig:
    """Configuration for LLM client."""

    provider: LLMProvider
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    reasoning_model: str = "claude-3-opus-20240229"
    explanation_model: str = "claude-3-haiku-20240307"
    max_tokens: int = 4096
    temperature: float = 0.3


@dataclass
class LLMResponse:
    """Response from LLM."""

    content: str
    model: str
    provider: LLMProvider
    usage: dict
    raw_response: Optional[dict] = None


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model_tier: ModelTier,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[str] = None,
    ) -> LLMResponse:
        """Generate a response from the LLM."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the LLM service is accessible."""
        pass


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude client implementation."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = None

    def _get_client(self):
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            try:
                import anthropic

                self._client = anthropic.AsyncAnthropic(
                    api_key=self.config.anthropic_api_key
                )
            except ImportError:
                raise RuntimeError(
                    "anthropic package not installed. Run: pip install anthropic"
                )
        return self._client

    def _get_model(self, tier: ModelTier) -> str:
        """Get model name for tier."""
        if tier == ModelTier.REASONING:
            return self.config.reasoning_model
        return self.config.explanation_model

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model_tier: ModelTier,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[str] = None,
    ) -> LLMResponse:
        """Generate response using Claude."""
        client = self._get_client()
        model = self._get_model(model_tier)

        temp = temperature if temperature is not None else self.config.temperature
        tokens = max_tokens if max_tokens is not None else self.config.max_tokens

        try:
            response = await client.messages.create(
                model=model,
                max_tokens=tokens,
                temperature=temp,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            return LLMResponse(
                content=response.content[0].text,
                model=model,
                provider=LLMProvider.ANTHROPIC,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
                raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
            )
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise

    async def health_check(self) -> bool:
        """Check Anthropic API connectivity."""
        try:
            client = self._get_client()
            # Simple test message
            response = await client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return response is not None
        except Exception as e:
            logger.error(f"Anthropic health check failed: {e}")
            return False


class OpenAIClient(BaseLLMClient):
    """OpenAI GPT client implementation."""

    # Model mapping for OpenAI
    MODEL_MAP = {
        ModelTier.REASONING: "gpt-4-turbo-preview",
        ModelTier.EXPLANATION: "gpt-3.5-turbo",
    }

    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = None

    def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                import openai

                self._client = openai.AsyncOpenAI(api_key=self.config.openai_api_key)
            except ImportError:
                raise RuntimeError(
                    "openai package not installed. Run: pip install openai"
                )
        return self._client

    def _get_model(self, tier: ModelTier) -> str:
        """Get model name for tier."""
        return self.MODEL_MAP.get(tier, "gpt-3.5-turbo")

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model_tier: ModelTier,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[str] = None,
    ) -> LLMResponse:
        """Generate response using GPT."""
        client = self._get_client()
        model = self._get_model(model_tier)

        temp = temperature if temperature is not None else self.config.temperature
        tokens = max_tokens if max_tokens is not None else self.config.max_tokens

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temp,
            "max_tokens": tokens,
        }

        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await client.chat.completions.create(**kwargs)

            return LLMResponse(
                content=response.choices[0].message.content,
                model=model,
                provider=LLMProvider.OPENAI,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
            )
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def health_check(self) -> bool:
        """Check OpenAI API connectivity."""
        try:
            client = self._get_client()
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return response is not None
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return False


class GeminiClient(BaseLLMClient):
    """Google Gemini client implementation."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._model = None

    def _get_model(self, tier: ModelTier):
        """Get Gemini model for tier."""
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.config.gemini_api_key)

            # Use gemini-2.5-flash for both (Gemini 3)
            model_name = "gemini-2.5-flash"

            return genai.GenerativeModel(model_name)
        except ImportError:
            raise RuntimeError(
                "google-generativeai package not installed. Run: pip install google-generativeai"
            )

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model_tier: ModelTier,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[str] = None,
    ) -> LLMResponse:
        """Generate response using Gemini."""
        import asyncio

        model = self._get_model(model_tier)
        model_name = "gemini-2.5-flash"

        temp = temperature if temperature is not None else self.config.temperature
        tokens = max_tokens if max_tokens is not None else self.config.max_tokens

        # Combine system and user prompts for Gemini
        full_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"

        generation_config = {
            "temperature": temp,
            "max_output_tokens": tokens,
        }

        try:
            # Gemini's generate_content is synchronous, wrap in executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: model.generate_content(
                    full_prompt,
                    generation_config=generation_config,
                )
            )

            return LLMResponse(
                content=response.text,
                model=model_name,
                provider=LLMProvider.GEMINI,
                usage={
                    "prompt_tokens": response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0,
                    "completion_tokens": response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0,
                },
            )
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise

    async def health_check(self) -> bool:
        """Check Gemini API connectivity."""
        try:
            import asyncio

            model = self._get_model(ModelTier.EXPLANATION)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: model.generate_content("Hi")
            )
            return response is not None
        except Exception as e:
            logger.error(f"Gemini health check failed: {e}")
            return False


class LLMClient:
    """
    Unified LLM client with provider switching and fallback.

    Primary provider is tried first.
    Falls back to secondary provider on failure.
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self._primary: Optional[BaseLLMClient] = None
        self._fallback: Optional[BaseLLMClient] = None
        self._setup_clients()

    def _setup_clients(self):
        """Setup primary and fallback clients based on config."""
        if self.config.provider == LLMProvider.GEMINI:
            if self.config.gemini_api_key:
                self._primary = GeminiClient(self.config)
            # Fallback to Anthropic or OpenAI
            if self.config.anthropic_api_key:
                self._fallback = AnthropicClient(self.config)
            elif self.config.openai_api_key:
                self._fallback = OpenAIClient(self.config)
        elif self.config.provider == LLMProvider.ANTHROPIC:
            if self.config.anthropic_api_key:
                self._primary = AnthropicClient(self.config)
            if self.config.gemini_api_key:
                self._fallback = GeminiClient(self.config)
            elif self.config.openai_api_key:
                self._fallback = OpenAIClient(self.config)
        else:  # OpenAI
            if self.config.openai_api_key:
                self._primary = OpenAIClient(self.config)
            if self.config.gemini_api_key:
                self._fallback = GeminiClient(self.config)
            elif self.config.anthropic_api_key:
                self._fallback = AnthropicClient(self.config)

        if self._primary is None and self._fallback is None:
            logger.warning("No LLM API keys configured. LLM features disabled.")

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model_tier: ModelTier,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[str] = None,
    ) -> LLMResponse:
        """
        Generate LLM response with automatic fallback.

        Tries primary provider first, falls back to secondary on failure.
        """
        if self._primary is None and self._fallback is None:
            raise RuntimeError("No LLM providers configured")

        # Try primary
        if self._primary:
            try:
                return await self._primary.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model_tier=model_tier,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                )
            except Exception as e:
                logger.warning(f"Primary LLM failed: {e}, trying fallback...")
                if self._fallback is None:
                    raise

        # Try fallback
        if self._fallback:
            return await self._fallback.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model_tier=model_tier,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
            )

        raise RuntimeError("All LLM providers failed")

    async def health_check(self) -> bool:
        """Check if any LLM provider is accessible."""
        if self._primary:
            if await self._primary.health_check():
                return True
        if self._fallback:
            if await self._fallback.health_check():
                return True
        return False

    def get_active_provider(self) -> Optional[LLMProvider]:
        """Get the currently active provider."""
        if self._primary:
            return self.config.provider
        elif self._fallback:
            return (
                LLMProvider.OPENAI
                if self.config.provider == LLMProvider.ANTHROPIC
                else LLMProvider.ANTHROPIC
            )
        return None


# Singleton instance management
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create LLM client singleton."""
    global _llm_client
    if _llm_client is None:
        from app.core.config import settings

        config = LLMConfig(
            provider=LLMProvider(settings.llm_primary_provider),
            anthropic_api_key=settings.anthropic_api_key,
            openai_api_key=settings.openai_api_key,
            gemini_api_key=settings.gemini_api_key,
            reasoning_model=settings.llm_reasoning_model,
            explanation_model=settings.llm_explanation_model,
        )
        _llm_client = LLMClient(config)
    return _llm_client
