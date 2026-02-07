"""
Redis cache layer for DevMind.
Provides caching for search results and embeddings.
"""

import json
import hashlib
import logging
from typing import Optional, Any, List
from datetime import timedelta

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Async Redis cache manager.
    Caches search results, embeddings, and LLM responses.
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        default_ttl: int = 3600,  # 1 hour
        enabled: bool = True
    ):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.enabled = enabled and REDIS_AVAILABLE
        self.client: Optional[aioredis.Redis] = None
        
        if not REDIS_AVAILABLE and enabled:
            logger.warning("Redis not available, caching disabled")
    
    async def connect(self):
        """Connect to Redis."""
        if not self.enabled:
            return
        
        try:
            self.client = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.client.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.enabled = False
    
    async def close(self):
        """Close Redis connection."""
        if self.client:
            await self.client.close()
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        # Create stable hash from args and kwargs
        key_data = json.dumps({
            "args": args,
            "kwargs": sorted(kwargs.items())
        }, sort_keys=True)
        
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"{prefix}:{key_hash}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.enabled or not self.client:
            return None
        
        try:
            value = await self.client.get(key)
            if value:
                logger.debug(f"Cache hit: {key}")
                return json.loads(value)
            logger.debug(f"Cache miss: {key}")
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ):
        """Set value in cache with TTL."""
        if not self.enabled or not self.client:
            return
        
        try:
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value)
            await self.client.setex(key, ttl, serialized)
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    async def delete(self, key: str):
        """Delete key from cache."""
        if not self.enabled or not self.client:
            return
        
        try:
            await self.client.delete(key)
            logger.debug(f"Cache delete: {key}")
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
    
    async def clear_prefix(self, prefix: str):
        """Clear all keys with given prefix."""
        if not self.enabled or not self.client:
            return
        
        try:
            pattern = f"{prefix}:*"
            keys = await self.client.keys(pattern)
            if keys:
                await self.client.delete(*keys)
                logger.info(f"Cleared {len(keys)} keys with prefix {prefix}")
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
    
    # Convenience methods for common cache patterns
    
    async def cache_search_results(
        self,
        query: str,
        results: List[Any],
        ttl: int = 1800  # 30 minutes
    ):
        """Cache search results."""
        key = self._generate_key("search", query)
        await self.set(key, results, ttl)
    
    async def get_search_results(self, query: str) -> Optional[List[Any]]:
        """Get cached search results."""
        key = self._generate_key("search", query)
        return await self.get(key)
    
    async def cache_embedding(
        self,
        text: str,
        embedding: List[float],
        ttl: int = 86400  # 24 hours
    ):
        """Cache embedding vector."""
        key = self._generate_key("embedding", text)
        await self.set(key, embedding, ttl)
    
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get cached embedding."""
        key = self._generate_key("embedding", text)
        return await self.get(key)


# Global cache instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        import os
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        enabled = os.getenv("ENABLE_CACHING", "true").lower() == "true"
        _cache_manager = CacheManager(redis_url=redis_url, enabled=enabled)
    return _cache_manager
