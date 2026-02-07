"""
Rate-limited LLM client with request queue and fallback.

Implements token bucket rate limiting to prevent API abuse.
Queues requests when at limit, with timeout and fallback to local model.

Features:
- Configurable rate limits (requests per minute)
- Request queue with timeout
- Automatic fallback to local model (Ollama/Phi-3)
- Background worker for queue processing
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional, AsyncIterator
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class QueuedRequest:
    """Represents a queued LLM request."""
    prompt: str
    future: asyncio.Future
    enqueued_at: float = field(default_factory=time.time)


class RateLimitedLLMClient:
    """
    Wraps LLM client with token bucket rate limiting and request queue.
    
    Fallback chain:
    - Direct execution (if under rate limit)
    - Queue request (if at limit)
    - Fallback to local model (if queue full or timeout)
    
    Example:
        ```python
        from devmind.llm.provider import ClaudeProvider, OllamaProvider
        
        primary = ClaudeProvider(api_key="...")
        fallback = OllamaProvider(model="phi-3")
        
        client = RateLimitedLLMClient(
            primary_client=primary,
            fallback_client=fallback,
            max_rpm=60,  # 60 requests per minute
        )
        
        await client.start()  # Start background worker
        
        # Will queue if at limit, fallback if queue full
        response = await client.generate("Explain this code...")
        
        await client.stop()  # Cleanup
        ```
    """

    def __init__(
        self,
        primary_client,          # Main LLM (Claude Sonnet, GPT-4, etc.)
        fallback_client=None,    # Fallback LLM (Ollama / Phi-3)
        max_rpm: int = 60,       # Maximum requests per minute
        max_queue_size: int = 100,
        queue_timeout: float = 30.0,  # Seconds
    ):
        """
        Initialize rate-limited LLM client.
        
        Args:
            primary_client: Primary LLM client (external API)
            fallback_client: Fallback LLM client (local model, optional)
            max_rpm: Maximum requests per minute
            max_queue_size: Maximum queued requests
            queue_timeout: Request timeout in seconds
        """
        self.primary = primary_client
        self.fallback = fallback_client
        self.max_rpm = max_rpm
        self.max_queue_size = max_queue_size
        self.queue_timeout = queue_timeout

        self._queue: asyncio.Queue[QueuedRequest] = asyncio.Queue(
            maxsize=max_queue_size
        )
        self._request_timestamps: deque[float] = deque()
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Start the background queue worker."""
        if self._running:
            logger.warning("Rate limiter already running")
            return
        
        self._running = True
        self._worker_task = asyncio.create_task(self._process_queue())
        logger.info("Rate limiter started (max_rpm=%d)", self.max_rpm)

    async def stop(self):
        """Stop the background worker and cleanup."""
        if not self._running:
            return
        
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Rate limiter stopped")

    async def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate response with rate limiting and fallback.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional arguments for LLM client
            
        Returns:
            Generated response text
            
        Raises:
            RuntimeError: If queue is full and no fallback available
        """
        # Try direct execution if under rate limit
        if self._can_send():
            return await self._send(prompt, **kwargs)

        # Queue the request
        if self._queue.full():
            logger.warning(
                "Queue full (%d/%d), attempting fallback",
                self._queue.qsize(),
                self.max_queue_size
            )
            if self.fallback:
                logger.info("Using fallback LLM for prompt: %s", prompt[:50])
                return await self.fallback.generate(prompt, **kwargs)
            raise RuntimeError("LLM request queue is full and no fallback available")

        future = asyncio.get_event_loop().create_future()
        request = QueuedRequest(prompt=prompt, future=future)
        await self._queue.put(request)

        logger.info(
            "Request queued (position: %d/%d): %s",
            self._queue.qsize(),
            self.max_queue_size,
            prompt[:50]
        )

        try:
            return await asyncio.wait_for(future, timeout=self.queue_timeout)
        except asyncio.TimeoutError:
            logger.warning("Queue timeout after %ds", self.queue_timeout)
            if self.fallback:
                logger.info("Using fallback LLM after timeout")
                return await self.fallback.generate(prompt, **kwargs)
            raise

    async def generate_stream(
        self, prompt: str, **kwargs
    ) -> AsyncIterator[str]:
        """
        Generate streaming response (for chat).
        
        Note: Streaming bypasses queue - use generate() for queuing.
        """
        if not self._can_send():
            logger.warning("Rate limit reached, waiting before streaming")
            await self._wait_for_capacity()
        
        async for chunk in self.primary.generate_stream(prompt, **kwargs):
            yield chunk

    def _can_send(self) -> bool:
        """Check if we can send a request now."""
        now = time.time()
        # Remove timestamps older than 60 seconds
        while self._request_timestamps and now - self._request_timestamps[0] > 60:
            self._request_timestamps.popleft()
        
        return len(self._request_timestamps) < self.max_rpm

    async def _wait_for_capacity(self):
        """Wait until we have capacity."""
        while not self._can_send():
            await asyncio.sleep(0.5)

    async def _send(self, prompt: str, **kwargs) -> str:
        """Send request to primary LLM."""
        self._request_timestamps.append(time.time())
        return await self.primary.generate(prompt, **kwargs)

    async def _process_queue(self):
        """Background worker to process queued requests."""
        logger.info("Queue worker started")
        
        while self._running:
            try:
                if self._can_send() and not self._queue.empty():
                    request = await self._queue.get()

                    # Skip expired requests
                    if time.time() - request.enqueued_at > self.queue_timeout:
                        if not request.future.done():
                            request.future.set_exception(
                                TimeoutError("Request expired in queue")
                            )
                        logger.warning("Dropped expired request from queue")
                        continue

                    # Process request
                    try:
                        result = await self._send(request.prompt)
                        if not request.future.done():
                            request.future.set_result(result)
                        logger.debug("Processed queued request successfully")
                    except Exception as e:
                        if not request.future.done():
                            request.future.set_exception(e)
                        logger.error("Queue worker error: %s", e)
                else:
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                logger.info("Queue worker cancelled")
                break
            except Exception as e:
                logger.error("Queue worker error: %s", e)
                await asyncio.sleep(1)

    async def get_status(self) -> dict:
        """Get current rate limiter status."""
        now = time.time()
        recent_requests = sum(
            1 for ts in self._request_timestamps if now - ts < 60
        )
        
        return {
            "running": self._running,
            "queue_size": self._queue.qsize(),
            "queue_capacity": self.max_queue_size,
            "requests_last_minute": recent_requests,
            "capacity_remaining": self.max_rpm - recent_requests,
            "utilization": recent_requests / self.max_rpm,
            "fallback_available": self.fallback is not None,
        }


# Example integration
"""
# In your FastAPI app:

from devmind.llm.rate_limited_client import RateLimitedLLMClient
from devmind.llm.provider import ClaudeProvider, OllamaProvider

# Initialize
claude = ClaudeProvider(api_key=settings.ANTHROPIC_API_KEY)
ollama = OllamaProvider(base_url="http://ollama:11434", model="phi-3")

llm_client = RateLimitedLLMClient(
    primary_client=claude,
    fallback_client=ollama,
    max_rpm=60,  # Anthropic tier limit
)

@app.on_event("startup")
async def start_llm_client():
    await llm_client.start()

@app.on_event("shutdown")
async def stop_llm_client():
    await llm_client.stop()

# In your chat endpoint:
@app.post("/chat")
async def chat(message: str):
    response = await llm_client.generate(message)
    return {"response": response}

# Health endpoint
@app.get("/health/llm")
async def llm_health():
    return await llm_client.get_status()
"""
