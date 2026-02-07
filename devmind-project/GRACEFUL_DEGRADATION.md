# Graceful Degradation Implementation

This directory contains production resilience features that prevent hard failures when dependencies are unavailable.

## Components

### 1. Resilient Search (`search/resilient_search.py`)

Multi-layer fallback chain for search operations:

```
Cache (Redis) → Vector Search (Qdrant) → Keyword Search (PostgreSQL)
   ↓                  ↓                        ↓
< 50ms             200ms                   500ms
Fastest         Primary                  Degraded
```

**Features**:

- Automatic Qdrant failure detection
- Seamless degradation to keyword search
- Health monitoring and recovery
- Result tagging for degraded mode
- Cache layer for performance

**Usage**:

```python
from devmind.search.resilient_search import ResilientSearchClient

search = ResilientSearchClient(
    vector_client=qdrant_client,
    keyword_client=postgres_client,
    cache_client=redis_client,
)

# Automatically falls back if Qdrant is down
results = await search.search(query="authentication logic", top_k=10)

# Check if degraded
if any(r.metadata.get("degraded") for r in results):
    print("⚠️ Using keyword fallback")
```

**Health Monitoring**:

```python
# Background task (runs every 30s)
async def monitor_search():
    while True:
        await asyncio.sleep(30)
        healthy = await search.check_qdrant_health()
        if not healthy:
            alert("Qdrant is down, using keyword fallback")
```

### 2. Rate-Limited LLM Client (`llm/rate_limited_client.py`)

Token bucket rate limiting with request queue and fallback:

```
Request → Under limit? → Send to Primary (Claude)
             ↓ No
          Queue full? → Wait in queue → Send when capacity
             ↓ Yes
          Fallback → Local Model (Phi-3)
```

**Features**:

- Configurable requests-per-minute limit
- Request queue with timeout
- Automatic fallback to local model
- Background worker for queue processing
- Streaming support (bypasses queue)

**Usage**:

```python
from devmind.llm.rate_limited_client import RateLimitedLLMClient

llm = RateLimitedLLMClient(
    primary_client=claude_client,
    fallback_client=ollama_client,
    max_rpm=60,  # Anthropic tier limit
    max_queue_size=100,
    queue_timeout=30.0,
)

await llm.start()

# Will queue if at limit, fallback if queue full
response = await llm.generate("Explain this code...")

# For chat (streaming)
async for chunk in llm.generate_stream("Help me debug..."):
    print(chunk, end="")

await llm.stop()
```

**Status Monitoring**:

```python
status = await llm.get_status()
# {
#   "queue_size": 12,
#   "requests_last_minute": 58,
#   "capacity_remaining": 2,
#   "utilization": 0.97
# }
```

## Integration

### FastAPI App Setup

```python
# main.py

from devmind.search.resilient_search import ResilientSearchClient
from devmind.llm.rate_limited_client import RateLimitedLLMClient

# Initialize on startup
@app.on_event("startup")
async def startup():
    # Search
    app.state.search = ResilientSearchClient(
        vector_client=qdrant,
        keyword_client=postgres,
        cache_client=redis,
    )

    # Start health monitoring
    asyncio.create_task(monitor_search_health())

    # LLM
    app.state.llm = RateLimitedLLMClient(
        primary_client=claude,
        fallback_client=ollama,
        max_rpm=60,
    )
    await app.state.llm.start()

@app.on_event("shutdown")
async def shutdown():
    await app.state.llm.stop()

# Health check endpoints
@app.get("/health/search")
async def search_health():
    return await app.state.search.get_status()

@app.get("/health/llm")
async def llm_health():
    return await app.state.llm.get_status()
```

### Search Endpoint

```python
@app.post("/search")
async def search(query: str, workspace_id: str):
    results = await app.state.search.search(
        query=query,
        top_k=10,
        workspace_id=workspace_id,
    )

    # Check degradation
    degraded = any(r.metadata.get("degraded") for r in results)

    return {
        "results": results,
        "degraded_mode": degraded,
        "warning": "Using keyword search fallback" if degraded else None,
    }
```

### Chat Endpoint

```python
@app.post("/chat")
async def chat(message: str, stream: bool = False):
    if stream:
        async def generate():
            async for chunk in app.state.llm.generate_stream(message):
                yield f"data: {chunk}\n\n"
        return StreamingResponse(generate())
    else:
        response = await app.state.llm.generate(message)
        return {"response": response}
```

## Benefits

### Resilient Search

| Scenario        | Behavior                 | User Experience            |
| --------------- | ------------------------ | -------------------------- |
| **Normal**      | Qdrant vector search     | Best quality, <200ms       |
| **Qdrant slow** | Falls back after timeout | Degraded quality, ~500ms   |
| **Qdrant down** | Keyword search           | Exact matches only, ~500ms |
| **All down**    | Cached results           | Stale but functional       |

### Rate-Limited LLM

| Scenario         | Behavior          | User Experience            |
| ---------------- | ----------------- | -------------------------- |
| **Under limit**  | Direct to Claude  | Best quality, ~2s          |
| **At limit**     | Queued (30s max)  | Slight delay, same quality |
| **Queue full**   | Fallback to Phi-3 | Immediate, lower quality   |
| **Primary down** | Always Phi-3      | Degraded but functional    |

## Testing

### Simulate Qdrant Failure

```bash
# Stop Qdrant
docker-compose stop qdrant

# Search should still work (keyword fallback)
curl -X POST http://localhost:8000/search \
  -d '{"query": "authentication", "workspace_id": "..."}'

# Response includes degradation warning:
# {"results": [...], "degraded_mode": true}

# Restart Qdrant
docker-compose start qdrant

# Within 30s, vector search should resume
```

### Simulate Rate Limit

```python
# Send 100 requests rapidly
import asyncio
async def stress_test():
    tasks = [llm.generate(f"Query {i}") for i in range(100)]
    results = await asyncio.gather(*tasks)

# First 60: Direct to API
# Next 40: Queued or fallback to Phi-3
```

## Monitoring

### Metrics to Track

```python
# Search resilience
search_degraded_percentage = (
    keyword_searches / total_searches
)

# LLM resilience
llm_fallback_percentage = (
    phi3_responses / total_responses
)
llm_queue_wait_time_p95 = ...
```

### Alerts

```yaml
# Prometheus alerts
- alert: QdrantDownFor5Min
  expr: search_degraded_percentage > 0.5 for 5m

- alert: LLMQueueSaturated
  expr: llm_queue_utilization > 0.9 for 2m
```

## Future Enhancements

- [ ] Circuit breaker pattern for Qdrant
- [ ] Exponential backoff for retries
- [ ] Redis-backed shared rate limiter (multi-instance)
- [ ] Priority queue (premium users first)
- [ ] Metrics export to Prometheus

## Related Files

- `devmind/search/vector_search.py` - Qdrant client
- `devmind/search/keyword_search.py` - PostgreSQL keyword search
- `devmind/cache/redis_client.py` - Redis cache
- `devmind/llm/provider.py` - LLM provider interfaces
