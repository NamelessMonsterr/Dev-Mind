"""
Unit tests for resilient search client.

Tests the fallback chain: Cache → Qdrant → Keyword Search
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from devmind.search.resilient_search import ResilientSearchClient


@pytest.fixture
def mock_clients():
    """Create mock clients for testing."""
    vector = AsyncMock()
    keyword = AsyncMock()
    cache = AsyncMock()
    return vector, keyword, cache


@pytest.fixture
def search_client(mock_clients):
    """Create resilient search client with mocks."""
    vector, keyword, cache = mock_clients
    return ResilientSearchClient(
        vector_client=vector,
        keyword_client=keyword,
        cache_client=cache,
    )


@pytest.mark.asyncio
async def test_cache_hit(search_client, mock_clients):
    """Test that cached results are returned first."""
    _, _, cache = mock_clients
    
    # Setup cache hit
    cached_results = [{"file": "auth.py", "score": 0.9}]
    cache.get.return_value = cached_results
    
    results = await search_client.search("test query", top_k=10)
    
    assert results == cached_results
    cache.get.assert_called_once()


@pytest.mark.asyncio
async def test_vector_search_on_cache_miss(search_client, mock_clients):
    """Test vector search when cache misses."""
    vector, _, cache = mock_clients
    
    # Setup cache miss, vector hit
    cache.get.return_value = None
    vector_results = [{"file": "jwt.py", "score": 0.85}]
    vector.search.return_value = vector_results
    
    results = await search_client.search("jwt auth", top_k=5)
    
    assert results == vector_results
    vector.search.assert_called_once()
    cache.set.assert_called_once()  # Should cache the result


@pytest.mark.asyncio
async def test_keyword_fallback_on_vector_failure(search_client, mock_clients):
    """Test fallback to keyword search when Qdrant fails."""
    vector, keyword, cache = mock_clients
    
    # Setup cache miss, vector failure, keyword success
    cache.get.return_value = None
    vector.search.side_effect = Exception("Qdrant connection refused")
    keyword_results = [{"file": "auth.py", "score": 0.5}]
    keyword.search.return_value = keyword_results
    
    results = await search_client.search("authentication", top_k=10)
    
    # Should get keyword results
    assert len(results) > 0
    keyword.search.assert_called_once()
    
    # Results should be tagged as degraded
    assert results[0].metadata["degraded"] is True
    assert results[0].metadata["search_mode"] == "keyword_fallback"


@pytest.mark.asyncio
async def test_qdrant_disabled_after_failures(search_client, mock_clients):
    """Test that Qdrant is disabled after consecutive failures."""
    vector, keyword, cache = mock_clients
    
    cache.get.return_value = None
    vector.search.side_effect = Exception("Connection error")
    keyword.search.return_value = [{"file": "test.py"}]
    
    # Trigger 3 consecutive failures
    for _ in range(3):
        await search_client.search("query", top_k=10)
    
    # Qdrant should now be disabled
    assert not search_client._qdrant_healthy
    
    # Next search should skip Qdrant entirely
    vector.search.reset_mock()
    await search_client.search("another query", top_k=10)
    vector.search.assert_not_called()
    keyword.search.assert_called()


@pytest.mark.asyncio
async def test_health_check_recovery(search_client, mock_clients):
    """Test that Qdrant is re-enabled after health check passes."""
    vector, _, _ = mock_clients
    
    # Disable Qdrant
    search_client._qdrant_healthy = False
    
    # Health check returns True
    vector.health_check.return_value = True
    
    is_healthy = await search_client.check_qdrant_health()
    
    assert is_healthy
    assert search_client._qdrant_healthy
    assert search_client._consecutive_failures == 0


@pytest.mark.asyncio
async def test_status_reporting(search_client):
    """Test status reporting includes all health indicators."""
    status = await search_client.get_status()
    
    assert "qdrant_healthy" in status
    assert "consecutive_failures" in status
    assert "cache_available" in status
    assert "fallback_enabled" in status
    assert status["fallback_enabled"] is True
