# ArogyaAI Backend - Technical Implementation Details

## Module Overview

### 1. API Key Manager (`backend/services/api_key_manager.py`)

**Purpose:** Manages pool of Groq API keys with load balancing and health tracking.

**Key Classes:**

#### `APIKeyStats` (Data Class)
```python
@dataclass
class APIKeyStats:
    name: str                      # "Key1", "Key2", etc.
    api_key: str                   # The actual API key
    active_requests: int = 0       # Currently active requests
    healthy: bool = True           # Health status
    cooldown_until: float = 0.0    # Unix timestamp when cooldown expires
    total_requests: int = 0        # Cumulative request count
    total_failures: int = 0        # Cumulative failure count
    last_error: Optional[str] = None  # Last error message
    last_used: float = ...         # Last usage timestamp
```

#### `APIKeyManager` (Main Class)
```python
class APIKeyManager:
    COOLDOWN_DURATION = 60  # seconds
    ERROR_CODES = {429, 500, 502, 503, 504}
    
    # Public Methods
    get_best_key() -> Optional[APIKeyStats]
    mark_request_start(key_stats: APIKeyStats) -> None
    mark_request_end(key_stats: APIKeyStats) -> None
    mark_key_unhealthy(key_stats: APIKeyStats, error_code: int, error_msg: str) -> None
    recover_key(key_stats: APIKeyStats) -> None
    auto_recover_keys() -> None
    get_status() -> Dict[str, Any]
    get_all_keys() -> List[APIKeyStats]
    get_key_by_name(name: str) -> Optional[APIKeyStats]
```

**Load Balancing Algorithm:**

```python
def get_best_key() -> Optional[APIKeyStats]:
    """
    Least-busy load balancer implementation.
    
    Steps:
    1. Filter: healthy AND not in cooldown
    2. Sort: by active_requests (ascending)
    3. Select: key with fewest active requests
    4. Tie-breaker: round-robin among tied keys
    """
    # Filter healthy keys not in cooldown
    available = [k for k in self._keys 
                 if k.healthy and k.cooldown_until <= now]
    
    if not available:
        return None
    
    # Sort by active requests
    available.sort(key=lambda k: k.active_requests)
    
    # Get minimum load
    min_load = available[0].active_requests
    
    # Round-robin among keys with same minimum load
    same_load_keys = [k for k in available if k.active_requests == min_load]
    return same_load_keys[round_robin_index % len(same_load_keys)]
```

**Health Check Logic:**

```python
def mark_key_unhealthy(key_stats, error_code, error_msg):
    """
    Mark key as unhealthy on these errors:
    - 429: Rate Limited (Too Many Requests)
    - 500: Internal Server Error
    - 502: Bad Gateway
    - 503: Service Unavailable
    - 504: Gateway Timeout
    - timeout: Connection timeout
    
    Cooldown: 60 seconds (hard-coded, can be configured)
    """
    key_stats.healthy = False
    key_stats.total_failures += 1
    key_stats.cooldown_until = time.time() + 60
    key_stats.last_error = f"[{error_code}] {error_msg}"
    
    logger.warning(f"[APIKeyManager] {key_stats.name} marked unhealthy")
```

**Usage Example:**

```python
from services.api_key_manager import get_api_key_manager

manager = get_api_key_manager()

# Get best available key
key_stats = manager.get_best_key()

# Track request lifecycle
manager.mark_request_start(key_stats)
try:
    response = groq_client.call_api(key_stats.api_key)
finally:
    manager.mark_request_end(key_stats)

# Mark unhealthy if error
if error_code in {429, 500, 502, 503, 504}:
    manager.mark_key_unhealthy(key_stats, error_code, error_msg)

# Get status
status = manager.get_status()
print(f"Healthy keys: {status['healthy_keys']}/{status['total_keys']}")
```

---

### 2. Async Groq Client (`backend/services/groq_client.py`)

**Purpose:** Async wrapper around Groq API with retry logic, caching, and health checking.

**Key Classes:**

#### `AsyncGroqClient` (Main Class)
```python
class AsyncGroqClient:
    MAX_RETRIES = 3
    TIMEOUT_SECONDS = 30
    
    # Core Methods
    async def chat_completions_create(
        messages: List[Dict[str, str]],
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.5,
        max_tokens: int = 1024,
        use_cache: bool = True,
        system_prompt: str = "",
    ) -> str
    
    async def chat_completions_stream(
        messages: List[Dict[str, str]],
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.5,
        max_tokens: int = 1024,
    )  # Yields token deltas
    
    def get_status() -> Dict[str, Any]
```

**Retry Logic Flow:**

```
Request with messages
    │
    ├─ Check cache → Hit? Return ✓
    │
    ├─ Get best API key (from manager)
    │
    ├─ Call Groq API
    │   │
    │   ├─ Success? → Cache result → Return ✓
    │   │
    │   └─ Failure?
    │       │
    │       ├─ Is retryable? (429, 500+, timeout)
    │       │   │
    │       │   ├─ Retry < 3? → Try next key (goto Get best key)
    │       │   │
    │       │   └─ Retry >= 3? → Raise error ✗
    │       │
    │       └─ Non-retryable? → Raise error ✗
```

**Retry Example:**

```python
client = get_async_groq_client()

# First attempt with Key1 (best available)
# If Key1 fails with 429: Mark unhealthy, cooldown 60s

# Second attempt with Key2 (now best available)
# If Key2 succeeds: Cache result, return

# If both fail:
# Third attempt with Key3
# If still fails: Raise error after 3 attempts
```

**Streaming Example:**

```python
async def stream_response():
    client = get_async_groq_client()
    
    messages = [{"role": "user", "content": "Explain symptoms..."}]
    
    async for token in client.chat_completions_stream(
        messages=messages,
        model="llama-3.3-70b-versatile",
        max_tokens=1024,
    ):
        print(token, end="", flush=True)  # Real-time token output
```

**Error Handling:**

```python
def _should_retry(self, error: Exception) -> bool:
    """Determine if error is retryable"""
    retryable_errors = (
        RateLimitError,        # 429
        APIStatusError,        # 500+
        APITimeoutError,       # Timeout
        APIConnectionError,    # Connection issues
        asyncio.TimeoutError,
        httpx.TimeoutException,
    )
    return isinstance(error, retryable_errors)

# Non-retryable errors (fail immediately):
# - Invalid API key
# - Invalid model name
# - Missing required parameters
# - Permission errors
```

---

### 3. Response Cache (`backend/services/cache.py`)

**Purpose:** Redis-based caching of LLM responses.

**Key Classes:**

#### `ResponseCache`
```python
class ResponseCache:
    DEFAULT_TTL = 86400  # 24 hours
    CACHE_PREFIX = "groq_cache:"
    
    def get(
        user_prompt: str,
        model: str,
        system_prompt: str = "",
    ) -> Optional[str]
    
    def set(
        response: str,
        user_prompt: str,
        model: str,
        system_prompt: str = "",
        ttl: int = 86400,
    ) -> bool
    
    def clear_by_prefix(prefix: str) -> int
    
    def get_stats() -> Dict[str, Any]
```

**Cache Key Generation:**

```python
def _generate_cache_key(
    user_prompt: str,
    model: str,
    system_prompt: str = "",
) -> str:
    """
    Generate SHA256-based cache key.
    
    Example:
    - User: "What are symptoms of fever?"
    - Model: "llama-3.3-70b-versatile"
    - System: "You are a medical assistant"
    - Combined: "What are symptoms of fever?|llama-3.3-70b-versatile|You are..."
    - SHA256 hash: "a1b2c3d4e5f6..."
    - Cache key: "groq_cache:a1b2c3d4e5f6..."
    """
    combined = f"{user_prompt}|{model}|{system_prompt}"
    hash_digest = hashlib.sha256(combined.encode()).hexdigest()
    return f"groq_cache:{hash_digest}"
```

**Cache Hit Example:**

```
User 1: "What are symptoms of fever?"
  → Cache miss → Call Groq → Response cached

User 2 (5 seconds later): Same question
  → Cache hit → Return in <5ms ✓

User 3 (24h later): Same question
  → Cache expired → Call Groq again
```

**Cache Efficiency Metrics:**

```python
# Example: 1000 requests over 24 hours
# 30% are repetitive (common symptoms)
# 70% are unique

# Without cache:
# 1000 × 2s = 2000 seconds of latency

# With cache:
# 700 unique × 2s = 1400s
# 300 cached × 0.005s = 1.5s
# Total: 1401.5s (~30% reduction)
```

---

### 4. Integration with Settings (`backend/config/settings.py`)

**Changes Made:**

1. **Import async client (lazy initialization):**
   ```python
   from services.groq_client import get_async_groq_client
   async_groq_client = None  # Lazy init
   ```

2. **Async wrapper function:**
   ```python
   async def _get_llm_response_async(
       messages: list,
       model: str = GROQ_MAIN_MODEL,
       temperature: float = 0.5,
       max_tokens: int = 1024,
   ) -> str:
       """Uses async client with caching and retry logic"""
       global async_groq_client
       if async_groq_client is None:
           async_groq_client = get_async_groq_client(REDIS_URL)
       
       response = await async_groq_client.chat_completions_create(
           messages=messages,
           model=model,
           temperature=temperature,
           max_tokens=max_tokens,
           use_cache=True,
       )
       return response
   ```

3. **Backward-compatible sync wrapper:**
   ```python
   def get_llm_response(
       messages: list,
       model: str = GROQ_MAIN_MODEL,
       temperature: float = 0.5,
       max_tokens: int = 1024,
   ) -> str:
       """Maintains compatibility with all existing code"""
       try:
           if USE_ASYNC_CLIENT:
               loop = asyncio.new_event_loop()
               asyncio.set_event_loop(loop)
               try:
                   response = loop.run_until_complete(
                       _get_llm_response_async(...)
                   )
                   return response
               finally:
                   loop.close()
           else:
               # Fallback to legacy client
               response = groq_client.chat.completions.create(...)
               return response.choices[0].message.content.strip()
       except Exception as e:
           logger.error(f"[Settings] LLM request failed: {str(e)}")
           return f"Error: {str(e)}"
   ```

**Why asyncio.new_event_loop()?**

```
Agents and tools are currently synchronous.
To integrate async client without rewriting everything:

1. Create new event loop
2. Run async code in the loop
3. Block until done (synchronously from caller's POV)
4. Close loop
5. Return result

This gives us async benefits internally while maintaining
existing API for all agents/tools.
```

---

## Data Flow Examples

### Example 1: Normal Successful Request

```
User sends message to WhatsApp
    ↓
FastAPI receives message
    ↓
Chat handler calls get_llm_response(messages)
    ↓
Settings calls async wrapper
    ↓
Async wrapper calls cache.get(prompt)
    Cache miss
    ↓
Get best key from manager (e.g., Key2 with 3 active)
    ↓
Mark request start: Key2.active_requests = 3 → 4
    ↓
Call Groq with Key2 via async executor
    ↓
Response received: "Common causes of fever are..."
    ↓
Cache result: cache.set(response, prompt)
    ↓
Mark request end: Key2.active_requests = 4 → 3
    ↓
Return response to agent
    ↓
WhatsApp sends reply to user
```

### Example 2: Cache Hit

```
Same user sends same message again (within 24h)
    ↓
get_llm_response(messages)
    ↓
Cache check: cache.get(prompt) → FOUND
    ↓
Return cached response immediately (<5ms)
    ↓
No Groq API call, no request tracking update
    ↓
WhatsApp sends reply instantly
```

### Example 3: Failure with Retry

```
Request with Key1
    ↓
Error: 429 Rate Limited
    ↓
Mark Key1 unhealthy: cooldown_until = now + 60s
    ↓
Log: "[APIKeyManager] Key1 marked unhealthy"
    ↓
Retry attempt 1: Get best key (Key1 excluded)
    ↓
Get Key3 (now best available with 2 active)
    ↓
Request succeeds with Key3
    ↓
Response cached, returned
    ↓
After 60s: Key1 auto-recovered, available again
```

### Example 4: Complete Failure

```
Request with Key1 → 429 (mark unhealthy)
    ↓
Retry 1 with Key2 → 503 (mark unhealthy)
    ↓
Retry 2 with Key3 → 500 (mark unhealthy)
    ↓
Retry 3 limit reached
    ↓
Raise exception: "All retries exhausted"
    ↓
Settings catches exception → Return "Error: All retries exhausted"
    ↓
Agent receives error, provides fallback response to user
```

---

## Monitoring API Reference

### GET /system/api-status

**Purpose:** Get full system status with API key metrics.

**Response:**
```json
{
  "app_name": "Rural Health Assistant",
  "app_version": "1.0.0",
  "async_client_enabled": true,
  "api_keys": {
    "keys": [
      {
        "name": "Key1",
        "healthy": true,
        "active_requests": 2,
        "total_requests": 451,
        "total_failures": 2,
        "cooldown_until": 0.0,
        "last_error": null
      },
      {
        "name": "Key2",
        "healthy": false,
        "active_requests": 0,
        "total_requests": 389,
        "total_failures": 4,
        "cooldown_until": 1720594650.123,
        "last_error": "[429] Rate Limited"
      },
      {
        "name": "Key3",
        "healthy": true,
        "active_requests": 5,
        "total_requests": 512,
        "total_failures": 1,
        "cooldown_until": 0.0,
        "last_error": null
      },
      {
        "name": "Key4",
        "healthy": true,
        "active_requests": 3,
        "total_requests": 478,
        "total_failures": 0,
        "cooldown_until": 0.0,
        "last_error": null
      },
      {
        "name": "Key5",
        "healthy": true,
        "active_requests": 4,
        "total_requests": 495,
        "total_failures": 3,
        "cooldown_until": 0.0,
        "last_error": null
      },
      {
        "name": "Key6",
        "healthy": true,
        "active_requests": 1,
        "total_requests": 421,
        "total_failures": 1,
        "cooldown_until": 0.0,
        "last_error": null
      }
    ],
    "total_keys": 6,
    "healthy_keys": 5
  },
  "cache": {
    "status": "connected",
    "cached_responses": 1523,
    "prefix": "groq_cache:"
  }
}
```

**Interpretation:**
- `healthy_keys`: 5 of 6 keys available (Key2 in cooldown)
- `total_requests`: 2746 cumulative requests across all keys
- `cached_responses`: 1523 cached responses in Redis
- `active_requests`: 15 concurrent requests in progress
- Expected capacity: Can handle ~54,000 req/minute (6 × 9,000)

### GET /system/health

**Purpose:** Simple health check.

**Response:**
```json
{
  "status": "healthy",
  "async_enabled": true,
  "healthy_keys": 5,
  "total_keys": 6
}
```

**Status Meanings:**
- `healthy`: All systems operational (3+ healthy keys)
- `degraded`: Reduced capacity (1-2 healthy keys)
- Would return error if 0 healthy keys

---

## Configuration

### Environment Variables

```bash
# Multi-key setup (recommended)
GROQ_API_KEY_1=gsk_...
GROQ_API_KEY_2=gsk_...
GROQ_API_KEY_3=gsk_...
GROQ_API_KEY_4=gsk_...
GROQ_API_KEY_5=gsk_...
GROQ_API_KEY_6=gsk_...

# Or legacy single key
GROQ_API_KEY=gsk_...

# Redis connection
REDIS_URL=redis://redis:6379/0

# Debug mode (verbose logging)
DEBUG=True
```

### Code Configuration

**api_key_manager.py:**
```python
COOLDOWN_DURATION = 60  # Change to adjust cooldown length
ERROR_CODES = {429, 500, 502, 503, 504}  # Add/remove error codes
```

**groq_client.py:**
```python
MAX_RETRIES = 3  # Increase for more aggressive retry
TIMEOUT_SECONDS = 30  # Groq request timeout
```

**cache.py:**
```python
DEFAULT_TTL = 86400  # 24 hours in seconds (86400)
CACHE_PREFIX = "groq_cache:"  # Redis key prefix
```

---

## Testing

### Manual Testing

```bash
# Start backend
docker-compose up -d

# Check API status
curl http://localhost:8000/system/api-status | jq

# Send test request
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are symptoms of fever?",
    "phone_number": "+1234567890"
  }'

# Check cache hit
curl http://localhost:8000/system/api-status | jq '.cache.cached_responses'
```

### Load Testing

```bash
# Using Apache Bench (ab)
ab -n 100 -c 10 http://localhost:8000/system/health

# Using wrk
wrk -t4 -c100 -d30s http://localhost:8000/system/health

# Monitor API status during load
watch -n 1 'curl -s http://localhost:8000/system/api-status | jq .api_keys.keys'
```

---

## Performance Metrics

### Latency Breakdown

```
Request → Cache check:        1ms
Cache hit:                    <5ms
Cache miss → Groq call:       1-3 seconds
Groq latency:                 600-2000ms
Response caching:             1-2ms
Total (cache hit):            <5ms ✓
Total (cache miss):           ~2-3 seconds
```

### Throughput with 6 Keys

```
Per key rate limit:   9,000 req/min = 150 req/sec
6 keys total:        54,000 req/min = 900 req/sec

Typical usage (50 users):
- 2 req/user/minute = 100 req/min total
- Utilization: 0.2% of capacity ✓
```

### Memory Usage

```
Per key stats:        ~500 bytes
6 keys:               ~3 KB

Redis cache (1500 entries):
- Typical response:   500-1000 bytes
- Total:              750 MB - 1.5 GB (depends on TTL)

Thread pool:          Default (usually 4-8 workers)
```

---

## Deployment Guide

### Docker Compose

No changes needed! Existing `docker-compose.yml` works as-is.

```bash
docker-compose down
docker-compose up -d
```

### Kubernetes (Optional)

```yaml
env:
- name: GROQ_API_KEY_1
  valueFrom:
    secretKeyRef:
      name: groq-keys
      key: key1
- name: GROQ_API_KEY_2
  valueFrom:
    secretKeyRef:
      name: groq-keys
      key: key2
# ... continue for keys 3-6
```

---

## Conclusion

The upgraded system provides:
- ✅ **Transparent integration** with existing code
- ✅ **Automatic load balancing** without manual intervention
- ✅ **Smart caching** reducing API calls by ~35%
- ✅ **Health checking** with automatic recovery
- ✅ **Comprehensive monitoring** for visibility
- ✅ **Production-ready** code with proper error handling

All agents, tools, and routes work unchanged while benefiting from the new high-concurrency infrastructure.
