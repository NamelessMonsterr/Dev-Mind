"""
Unit tests for rate-limited LLM client.

Tests rate limiting, queuing, and fallback behavior.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from devmind.llm.rate_limited_client import RateLimitedLLMClient


@pytest.fixture
def mock_llm_clients():
    """Create mock LLM clients."""
    primary = AsyncMock()
    fallback = AsyncMock()
    return primary, fallback


@pytest.fixture
async def llm_client(mock_llm_clients):
    """Create rate-limited client."""
    primary, fallback = mock_llm_clients
    client = RateLimitedLLMClient(
        primary_client=primary,
        fallback_client=fallback,
        max_rpm=10,  # Low limit for testing
        max_queue_size=5,
        queue_timeout=2.0,
    )
    await client.start()
    yield client
    await client.stop()


@pytest.mark.asyncio
async def test_direct_execution_under_limit(llm_client, mock_llm_clients):
    """Test that requests go directly when under rate limit."""
    primary, _ = mock_llm_clients
    primary.generate.return_value = "Response"
    
    result = await llm_client.generate("Test prompt")
    
    assert result == "Response"
    primary.generate.assert_called_once_with("Test prompt")


@pytest.mark.asyncio
async def test_queuing_at_limit(llm_client, mock_llm_clients):
    """Test that requests are queued when at rate limit."""
    primary, _ = mock_llm_clients
    primary.generate.return_value = "Response"
    
    # Fill the rate limit (10 rpm)
    tasks = [llm_client.generate(f"Prompt {i}") for i in range(15)]
    
    # First 10 should execute, rest should queue
    results = await asyncio.gather(*tasks)
    
    assert len(results) == 15
    assert all(r == "Response" for r in results)


@pytest.mark.asyncio
async def test_fallback_on_queue_full(llm_client, mock_llm_clients):
    """Test fallback to local model when queue is full."""
    primary, fallback = mock_llm_clients
    primary.generate.return_value = "Primary"
    fallback.generate.return_value = "Fallback"
    
    # Set queue size to 0 to force immediate fallback
    llm_client._queue = asyncio.Queue(maxsize=0)
    
    # Saturate rate limit first
    llm_client._request_timestamps = [asyncio.get_event_loop().time()] * 10
    
    result = await llm_client.generate("Test")
    
    assert result == "Fallback"
    fallback.generate.assert_called_once()


@pytest.mark.asyncio
async def test_no_fallback_raises_on_queue_full(mock_llm_clients):
    """Test that error is raised when queue full and no fallback."""
    primary, _ = mock_llm_clients
    client = RateLimitedLLMClient(
        primary_client=primary,
        fallback_client=None,  # No fallback
        max_rpm=1,
        max_queue_size=0,
    )
    await client.start()
    
    # Saturate
    client._request_timestamps = [asyncio.get_event_loop().time()]
    
    with pytest.raises(RuntimeError, match="queue is full"):
        await client.generate("Test")
    
    await client.stop()


@pytest.mark.asyncio
async def test_queue_timeout_fallback(llm_client, mock_llm_clients):
    """Test fallback when queue request times out."""
    primary, fallback = mock_llm_clients
    
    # Make primary slow
    async def slow_generate(prompt, **kwargs):
        await asyncio.sleep(5)
        return "Slow response"
    
    primary.generate.side_effect = slow_generate
    fallback.generate.return_value = "Fallback"
    
    # Saturate rate limit
    llm_client._request_timestamps = [asyncio.get_event_loop().time()] * 10
    
    # Should timeout and fallback (timeout = 2s)
    result = await llm_client.generate("Test")
    
    assert result == "Fallback"
    fallback.generate.assert_called_once()


@pytest.mark.asyncio
async def test_status_reporting(llm_client):
    """Test status reporting accuracy."""
    status = await llm_client.get_status()
    
    assert status["running"] is True
    assert "queue_size" in status
    assert "requests_last_minute" in status
    assert "capacity_remaining" in status
    assert "utilization" in status
    assert status["fallback_available"] is True


@pytest.mark.asyncio
async def test_rate_limit_resets_after_minute(llm_client, mock_llm_clients):
    """Test that rate limit capacity resets after 60 seconds."""
    primary, _ = mock_llm_clients
    primary.generate.return_value = "Response"
    
    # Fill rate limit
    now = asyncio.get_event_loop().time()
    llm_client._request_timestamps = [now - 61] * 10  # Old timestamps
    
    # Should be able to send immediately (old requests expired)
    assert llm_client._can_send() is True


@pytest.mark.asyncio
async def test_concurrent_requests(llm_client, mock_llm_clients):
    """Test handling of concurrent requests."""
    primary, _ = mock_llm_clients
    primary.generate.return_value = "Response"
    
    tasks = [llm_client.generate(f"Concurrent {i}") for i in range(20)]
    results = await asyncio.gather(*tasks)
    
    assert len(results) == 20
    assert all(r == "Response" for r in results)
