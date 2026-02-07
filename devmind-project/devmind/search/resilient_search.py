"""
Resilient search client with fallback chain.

Search priority:
1. Redis Cache (fastest)
2. Qdrant Vector Search (primary)
3. PostgreSQL Keyword Search (degraded fallback)

Automatically detects Qdrant failures and falls back to keyword search,
then re-enables vector search when health is restored.
"""

import logging
from typing import Optional, List

logger = logging.getLogger(__name__)


class ResilientSearchClient:
    """
    Search client with automatic fallback chain.
    
    Fallback order:
    - Cache → Qdrant → Keyword Search
    
    Features:
    - Automatic health detection
    - Seamless degradation
    - Health recovery monitoring
    - Result tagging for degraded mode
    """

    def __init__(
        self,
        vector_client,      # VectorSearchClient
        keyword_client,     # KeywordSearchClient
        cache_client,       # CacheClient (Redis)
    ):
        """
        Initialize resilient search.
        
        Args:
            vector_client: Qdrant vector search client
            keyword_client: PostgreSQL keyword search client
            cache_client: Redis cache client
        """
        self.vector = vector_client
        self.keyword = keyword_client
        self.cache = cache_client
        self._qdrant_healthy = True
        self._consecutive_failures = 0
        self._max_failures_before_disable = 3

    async def search(
        self,
        query: str,
        top_k: int = 10,
        workspace_id: Optional[str] = None,
        collection: Optional[str] = None,
    ):
        """
        Execute search with fallback chain.
        
        Args:
            query: Natural language query
            top_k: Number of results to return
            workspace_id: Workspace isolation filter
            collection: Optional Qdrant collection name
            
        Returns:
            List of search results with metadata
        """
        # Layer 1: Cache
        cache_key = f"search:{workspace_id}:{query}:{top_k}"
        cached = await self._try_cache(cache_key)
        if cached:
            logger.debug("Cache hit for query: %s", query[:50])
            return cached

        # Layer 2: Vector search (primary)
        if self._qdrant_healthy:
            results = await self._try_vector_search(
                query, top_k, workspace_id, collection
            )
            if results is not None:
                # Success - cache and return
                await self._set_cache(cache_key, results, ttl=300)
                self._consecutive_failures = 0
                return results
        
        # Layer 3: Keyword fallback (degraded)
        logger.warning(
            "Using keyword fallback for query: %s (Qdrant: %s)",
            query[:50],
            "disabled" if not self._qdrant_healthy else "failed"
        )
        results = await self.keyword.search(
            query, top_k=top_k, workspace_id=workspace_id
        )

        # Tag results so UI can show degradation notice
        for r in results:
            if not hasattr(r, 'metadata'):
                r.metadata = {}
            r.metadata["search_mode"] = "keyword_fallback"
            r.metadata["degraded"] = True

        return results

    async def _try_cache(self, key: str):
        """Try to get cached results."""
        try:
            return await self.cache.get(key)
        except Exception as e:
            logger.warning("Cache read failed: %s", e)
            return None

    async def _set_cache(self, key: str, value, ttl: int):
        """Try to cache results."""
        try:
            await self.cache.set(key, value, ttl=ttl)
        except Exception as e:
            logger.warning("Cache write failed: %s", e)

    async def _try_vector_search(
        self,
        query: str,
        top_k: int,
        workspace_id: Optional[str],
        collection: Optional[str],
    ):
        """
        Try vector search, handle failures gracefully.
        
        Returns:
            Results on success, None on failure
        """
        try:
            results = await self.vector.search(
                query,
                top_k=top_k,
                workspace_id=workspace_id,
                collection=collection,
            )
            return results
        except Exception as e:
            logger.error("Qdrant search failed: %s", e)
            self._consecutive_failures += 1
            
            # Disable after multiple failures
            if self._consecutive_failures >= self._max_failures_before_disable:
                logger.error(
                    "Disabling Qdrant after %d consecutive failures",
                    self._consecutive_failures
                )
                self._qdrant_healthy = False
            
            return None

    async def check_qdrant_health(self) -> bool:
        """
        Check Qdrant health and re-enable if recovered.
        
        This should be called periodically by a background task.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            healthy = await self.vector.health_check()
            
            if healthy and not self._qdrant_healthy:
                logger.info("Qdrant recovered, re-enabling vector search")
                self._consecutive_failures = 0
            
            self._qdrant_healthy = healthy
            return healthy
        except Exception as e:
            logger.error("Qdrant health check failed: %s", e)
            self._qdrant_healthy = False
            return False

    async def get_status(self) -> dict:
        """
        Get current search system status.
        
        Returns:
            Status dictionary with health indicators
        """
        return {
            "qdrant_healthy": self._qdrant_healthy,
            "consecutive_failures": self._consecutive_failures,
            "cache_available": await self._check_cache_health(),
            "fallback_enabled": True,  # Keyword search always available
        }

    async def _check_cache_health(self) -> bool:
        """Check Redis cache health."""
        try:
            await self.cache.ping()
            return True
        except Exception:
            return False


# Example usage and integration
"""
# In your FastAPI app initialization:

from devmind.search.resilient_search import ResilientSearchClient
from devmind.search.vector_search import VectorSearchClient
from devmind.search.keyword_search import KeywordSearchClient
from devmind.cache.redis_client import CacheClient

# Initialize clients
vector_client = VectorSearchClient(qdrant_url="http://qdrant:6333")
keyword_client = KeywordSearchClient(db=database)
cache_client = CacheClient(redis_url="redis://redis:6379")

# Create resilient search
search_client = ResilientSearchClient(
    vector_client=vector_client,
    keyword_client=keyword_client,
    cache_client=cache_client,
)

# Background task for health monitoring
@app.on_event("startup")
async def start_health_monitor():
    async def monitor():
        while True:
            await asyncio.sleep(30)  # Check every 30 seconds
            await search_client.check_qdrant_health()
    
    asyncio.create_task(monitor())

# In your search endpoint:
@app.post("/search")
async def search(query: str, workspace_id: str):
    results = await search_client.search(
        query=query,
        top_k=10,
        workspace_id=workspace_id,
    )
    
    # Check if degraded
    is_degraded = any(
        r.metadata.get("degraded", False) for r in results
    )
    
    return {
        "results": results,
        "degraded_mode": is_degraded,
        "warning": "Using keyword search fallback" if is_degraded else None
    }

# Health check endpoint
@app.get("/health/search")
async def search_health():
    return await search_client.get_status()
"""
