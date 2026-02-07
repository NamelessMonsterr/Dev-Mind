"""
LLM Provider abstraction for DevMind.
Supports multiple LLM providers with automatic selection.
"""

from typing import Optional, List, Dict, Any, AsyncGenerator
from enum import Enum
from abc import ABC, abstractmethod
import logging
import os

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    """LLM provider types."""
    LOCAL = "local"  # Ollama Phi-3
    SONNET = "sonnet"  # Claude 4.5 Sonnet
    OPUS = "opus"  # Claude 4.5 Opus (Thinking)
    GPT4 = "gpt4"  # OpenAI GPT-4
    GEMINI = "gemini"  # Google Gemini Pro


class LLMProvider(ABC):
    """Base class for LLM providers."""
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """Generate completion."""
        pass
    
    @abstractmethod
    async def stream(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream completion tokens."""
        pass


class OllamaProvider(LLMProvider):
    """Ollama provider for local Phi-3."""
    
    def __init__(self, model: str = "phi3", base_url: str = "http://localhost:11434"):
        """
        Initialize Ollama provider.
        
        Args:
            model: Model name (default: phi3)
            base_url: Ollama API URL
        """
        self.model = model
        self.base_url = base_url
        logger.info(f"OllamaProvider initialized (model={model})")
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """Generate completion using Ollama API."""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "temperature": temperature,
                        "stream": False
                    }
                ) as response:
                    data = await response.json()
                    return data.get("response", "")
                    
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            raise
    
    async def stream(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream completion tokens."""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "temperature": temperature,
                        "stream": True
                    }
                ) as response:
                    async for line in response.content:
                        if line:
                            import json
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                                
        except Exception as e:
            logger.error(f"Ollama streaming error: {e}")
            raise


class ClaudeProvider(LLMProvider):
    """Claude provider (Sonnet/Opus)."""
    
    def __init__(self, model: str = "claude-sonnet-4-20250514", api_key: Optional[str] = None):
        """
        Initialize Claude provider.
        
        Args:
            model: Claude model name
            api_key: Anthropic API key (or from env)
        """
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        
        logger.info(f"ClaudeProvider initialized (model={model})")
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """Generate completion using Claude API."""
        try:
            import anthropic
            
            client = anthropic.AsyncAnthropic(api_key=self.api_key)
            
            message = await client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return message.content[0].text
            
        except Exception as e:
            logger.error(f"Claude generation error: {e}")
            raise
    
    async def stream(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream completion tokens."""
        try:
            import anthropic
            
            client = anthropic.AsyncAnthropic(api_key=self.api_key)
            
            async with client.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                async for text in stream.text_stream:
                    yield text
                    
        except Exception as e:
            logger.error(f"Claude streaming error: {e}")
            raise


class LLMProviderManager:
    """
    LLM Provider Manager with automatic selection.
    
    Selects provider based on context size and complexity.
    """
    
    def __init__(self):
        """Initialize provider manager."""
        self.providers: Dict[ProviderType, LLMProvider] = {}
        logger.info("LLMProviderManager initialized")
    
    def register_provider(self, provider_type: ProviderType, provider: LLMProvider):
        """Register a provider."""
        self.providers[provider_type] = provider
        logger.info(f"Registered provider: {provider_type}")
    
    def auto_select_provider(
        self,
        context_size: int,
        query_complexity: str = "medium",
        force_provider: Optional[ProviderType] = None
    ) -> ProviderType:
        """
        Automatically select best provider.
        
        Args:
            context_size: Size of retrieved context (tokens)
            query_complexity: "simple", "medium", "complex"
            force_provider: Force specific provider
            
        Returns:
            Selected provider type
        """
        if force_provider:
            return force_provider
        
        # Selection logic
        if query_complexity == "complex" or context_size > 8000:
            # Use Opus for complex reasoning
            if ProviderType.OPUS in self.providers:
                logger.info("Selected OPUS (complex query)")
                return ProviderType.OPUS
        
        if context_size > 4000:
            # Use Sonnet for medium contexts
            if ProviderType.SONNET in self.providers:
                logger.info("Selected SONNET (large context)")
                return ProviderType.SONNET
        
        # Default to local for simple queries
        if ProviderType.LOCAL in self.providers:
            logger.info("Selected LOCAL (simple query)")
            return ProviderType.LOCAL
        
        # Fallback to Sonnet if available
        if ProviderType.SONNET in self.providers:
            logger.info("Selected SONNET (fallback)")
            return ProviderType.SONNET
        
        raise ValueError("No suitable provider available")
    
    async def generate(
        self,
        prompt: str,
        provider_type: Optional[ProviderType] = None,
        context_size: int = 0,
        query_complexity: str = "medium",
        **kwargs
    ) -> str:
        """
        Generate completion with automatic provider selection.
        
        Args:
            prompt: Input prompt
            provider_type: Force specific provider (optional)
            context_size: Context size for auto-selection
            query_complexity: Query complexity for auto-selection
            **kwargs: Additional generation kwargs
            
        Returns:
            Generated text
        """
        selected = self.auto_select_provider(
            context_size, query_complexity, provider_type
        )
        
        provider = self.providers.get(selected)
        if not provider:
            raise ValueError(f"Provider {selected} not available")
        
        logger.info(f"Generating with {selected}")
        return await provider.generate(prompt, **kwargs)
    
    async def stream(
        self,
        prompt: str,
        provider_type: Optional[ProviderType] = None,
        context_size: int = 0,
        query_complexity: str = "medium",
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream completion with automatic provider selection.
        
        Args:
            prompt: Input prompt
            provider_type: Force specific provider (optional)
            context_size: Context size for auto-selection
            query_complexity: Query complexity for auto-selection
            **kwargs: Additional generation kwargs
            
        Yields:
            Text chunks
        """
        selected = self.auto_select_provider(
            context_size, query_complexity, provider_type
        )
        
        provider = self.providers.get(selected)
        if not provider:
            raise ValueError(f"Provider {selected} not available")
        
        logger.info(f"Streaming with {selected}")
        async for chunk in provider.stream(prompt, **kwargs):
            yield chunk


# Singleton manager
_global_manager: Optional[LLMProviderManager] = None


def get_llm_manager() -> LLMProviderManager:
    """Get global LLM provider manager."""
    global _global_manager
    
    if _global_manager is None:
        _global_manager = LLMProviderManager()
        
        # Initialize providers based on available credentials
        try:
            # Try Ollama
            ollama = OllamaProvider()
            _global_manager.register_provider(ProviderType.LOCAL, ollama)
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
        
        try:
            # Try Claude Sonnet
            sonnet = ClaudeProvider(model="claude-sonnet-4-20250514")
            _global_manager.register_provider(ProviderType.SONNET, sonnet)
        except Exception as e:
            logger.warning(f"Claude Sonnet not available: {e}")
        
        try:
            # Try Claude Opus
            opus = ClaudeProvider(model="claude-opus-4-20250514")
            _global_manager.register_provider(ProviderType.OPUS, opus)
        except Exception as e:
            logger.warning(f"Claude Opus not available: {e}")
        
        try:
            # Try OpenAI GPT-4
            from .additional_providers import OpenAIProvider
            gpt4 = OpenAIProvider(model="gpt-4-turbo")
            _global_manager.register_provider(ProviderType.GPT4, gpt4)
        except Exception as e:
            logger.warning(f"OpenAI GPT-4 not available: {e}")
        
        try:
            # Try Google Gemini
            from .additional_providers import GeminiProvider
            gemini = GeminiProvider(model="gemini-2.0-flash-exp")
            _global_manager.register_provider(ProviderType.GEMINI, gemini)
        except Exception as e:
            logger.warning(f"Gemini not available: {e}")
    
    return _global_manager
