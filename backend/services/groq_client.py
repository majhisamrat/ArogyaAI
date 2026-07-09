"""
Async Groq Client with High-Concurrency Support

Features:
- Async/await pattern for non-blocking operations
- Multiple API key management with load balancing
- Automatic retry logic across different keys
- Health checking with cooldown recovery
- Redis response caching
- Comprehensive logging and monitoring
- Backward compatible with synchronous code via asyncio
"""

import asyncio
import time
from typing import Optional, List, Dict, Any
from groq import Groq, APIStatusError, APITimeoutError, APIConnectionError, RateLimitError
import httpx

from services.api_key_manager import APIKeyStats, get_api_key_manager
from services.cache import get_response_cache
from config.logger import logger


class AsyncGroqClient:
    """
    Async Groq client with load balancing, retry logic, and caching.
    
    Supports:
    - Multiple API keys with least-busy load balancing
    - Automatic retry on failures with different keys
    - Health checking and cooldown management
    - Redis response caching with 24-hour TTL
    - Full async/await pattern for non-blocking operations
    - Streaming support
    """

    MAX_RETRIES = 3
    TIMEOUT_SECONDS = 30

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """
        Initialize async Groq client.
        
        Args:
            redis_url: Redis connection URL for caching
        """
        self.api_key_manager = get_api_key_manager()
        self.cache = get_response_cache(redis_url)
        self._client_pool: Dict[str, Groq] = {}
        self._lock = asyncio.Lock()
        
        # Override class MAX_RETRIES to scale dynamically with configured keys pool
        self.MAX_RETRIES = max(3, len(self.api_key_manager.get_all_keys()) - 1)

        logger.info(f"[AsyncGroqClient] Initialized with async support. Dynamic retries limit: {self.MAX_RETRIES}")

    def _get_groq_client(self, api_key: str) -> Groq:
        """
        Get or create a Groq client for the given API key.
        
        Args:
            api_key: Groq API key
            
        Returns:
            Groq client instance
        """
        if api_key not in self._client_pool:
            self._client_pool[api_key] = Groq(api_key=api_key)

        return self._client_pool[api_key]

    def _should_retry(self, error: Exception) -> bool:
        """
        Determine if error is retryable.
        
        Args:
            error: The exception that occurred
            
        Returns:
            True if we should retry with another key
        """
        # Retryable errors
        retryable_errors = (
            RateLimitError,  # 429
            APIStatusError,  # 500+ server errors
            APITimeoutError,  # Timeout
            APIConnectionError,  # Connection issues
            asyncio.TimeoutError,
            httpx.TimeoutException,
        )

        return isinstance(error, retryable_errors)

    def _extract_error_code(self, error: Exception) -> Optional[int]:
        """Extract HTTP status code from error"""
        if isinstance(error, APIStatusError):
            return error.status_code
        return None

    async def _make_request(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        key_stats: APIKeyStats,
        retry_count: int = 0,
    ) -> str:
        """
        Make a single request to Groq with a specific key.
        
        Args:
            messages: Conversation messages
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            key_stats: API key stats object
            retry_count: Current retry attempt number
            
        Returns:
            LLM response string
            
        Raises:
            Exception if request fails after retries
        """
        try:
            self.api_key_manager.mark_request_start(key_stats)
            start_time = time.time()

            # Get client and make request
            client = self._get_groq_client(key_stats.api_key)

            # Run synchronous Groq call in executor to avoid blocking
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    ),
                ),
                timeout=self.TIMEOUT_SECONDS,
            )

            latency = time.time() - start_time
            content = response.choices[0].message.content.strip()

            logger.info(
                f"[AsyncGroqClient] {key_stats.name} | "
                f"Latency: {latency:.2f}s | "
                f"Tokens: {response.usage.completion_tokens if response.usage else 'N/A'} | "
                f"Retry: {retry_count}"
            )

            return content

        except Exception as e:
            error_code = self._extract_error_code(e)
            error_msg = str(e)[:100]  # Truncate long errors

            logger.error(
                f"[AsyncGroqClient] Request failed for {key_stats.name} | "
                f"Error: {error_msg} | "
                f"Status: {error_code} | "
                f"Retry: {retry_count}"
            )

            # Mark key as unhealthy if error indicates this
            if error_code in self.api_key_manager.ERROR_CODES:
                self.api_key_manager.mark_key_unhealthy(
                    key_stats,
                    error_code,
                    error_msg
                )

            raise

        finally:
            self.api_key_manager.mark_request_end(key_stats)

    async def _call_with_retry(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        user_prompt: str,
        system_prompt: str = "",
    ) -> str:
        """
        Call Groq API with automatic retry logic across multiple keys.
        
        Algorithm:
        1. Try to get best available key
        2. If request succeeds, cache and return
        3. If request fails and is retryable, try another key
        4. After all retries exhausted, raise error
        
        Args:
            messages: Conversation messages
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            user_prompt: Original user prompt for cache key
            system_prompt: System prompt for cache key
            
        Returns:
            LLM response string
            
        Raises:
            Exception if all retries fail
        """
        last_error = None
        attempted_keys = []

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                # Get best available key
                key_stats = self.api_key_manager.get_best_key()
                if not key_stats:
                    raise RuntimeError(
                        "No healthy API keys available. All keys are either "
                        "unhealthy or in cooldown."
                    )

                attempted_keys.append(key_stats.name)

                # Make request
                response = await self._make_request(
                    messages,
                    model,
                    temperature,
                    max_tokens,
                    key_stats,
                    attempt,
                )

                # Cache the response
                self.cache.set(
                    response,
                    user_prompt,
                    model,
                    system_prompt,
                )

                return response

            except Exception as e:
                last_error = e

                if not self._should_retry(e) or attempt >= self.MAX_RETRIES:
                    # Non-retryable or out of retries
                    break

                # Wait a bit before retry to avoid thundering herd
                await asyncio.sleep(0.5 * (attempt + 1))

                # Auto-recover keys before next attempt
                self.api_key_manager.auto_recover_keys()

        # All retries exhausted
        logger.error(
            f"[AsyncGroqClient] All retries exhausted | "
            f"Attempted: {', '.join(attempted_keys)} | "
            f"Error: {str(last_error)}"
        )
        raise last_error

    async def chat_completions_create(
        self,
        messages: List[Dict[str, str]],
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.5,
        max_tokens: int = 1024,
        use_cache: bool = True,
        system_prompt: str = "",
    ) -> str:
        """
        Create a chat completion with caching and retry logic.
        
        Args:
            messages: Conversation messages in format:
                     [{"role": "system/user/assistant", "content": "..."}]
            model: Model name
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            use_cache: Whether to use Redis cache
            system_prompt: System prompt for cache key (if different from messages)
            
        Returns:
            LLM response string
            
        Raises:
            Exception if request fails after all retries
        """
        # Extract user prompt from messages for cache key
        user_prompt = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_prompt = msg.get("content", "")
                break

        # Check cache first
        if use_cache:
            cached_response = self.cache.get(user_prompt, model, system_prompt)
            if cached_response:
                logger.info("[AsyncGroqClient] Cache HIT - returning cached response")
                return cached_response

        # Call with retry logic
        return await self._call_with_retry(
            messages,
            model,
            temperature,
            max_tokens,
            user_prompt,
            system_prompt,
        )

    async def chat_completions_stream(
        self,
        messages: List[Dict[str, str]],
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.5,
        max_tokens: int = 1024,
    ):
        """
        Stream chat completions token-by-token.
        
        Args:
            messages: Conversation messages
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Yields:
            Token deltas from LLM stream
            
        Note:
            Streaming does not use cache (responses are streamed in real-time)
        """
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                key_stats = self.api_key_manager.get_best_key()
                if not key_stats:
                    raise RuntimeError("No healthy API keys available")

                self.api_key_manager.mark_request_start(key_stats)
                start_time = time.time()

                try:
                    client = self._get_groq_client(key_stats.api_key)

                    # Stream in executor to avoid blocking
                    loop = asyncio.get_event_loop()
                    stream = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            lambda: client.chat.completions.create(
                                model=model,
                                messages=messages,
                                temperature=temperature,
                                max_tokens=max_tokens,
                                stream=True,
                            ),
                        ),
                        timeout=self.TIMEOUT_SECONDS,
                    )

                    for chunk in stream:
                        if chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content

                    latency = time.time() - start_time
                    logger.info(
                        f"[AsyncGroqClient] Stream completed on {key_stats.name} | "
                        f"Latency: {latency:.2f}s"
                    )
                    return

                finally:
                    self.api_key_manager.mark_request_end(key_stats)

            except Exception as e:
                logger.error(
                    f"[AsyncGroqClient] Stream error on attempt {attempt + 1}: {str(e)}"
                )

                if not self._should_retry(e) or attempt >= self.MAX_RETRIES:
                    raise

                await asyncio.sleep(0.5 * (attempt + 1))

    def get_status(self) -> Dict[str, Any]:
        """
        Get detailed status of API keys and cache.
        
        Returns:
            Dict with full system status
        """
        return {
            "api_keys": self.api_key_manager.get_status(),
            "cache": self.cache.get_stats(),
        }


# Global instance
_async_groq_client: Optional[AsyncGroqClient] = None


def get_async_groq_client(redis_url: str = "redis://localhost:6379/0") -> AsyncGroqClient:
    """
    Get or create the global async Groq client instance.
    
    Args:
        redis_url: Redis connection URL
        
    Returns:
        AsyncGroqClient instance
    """
    global _async_groq_client
    if _async_groq_client is None:
        _async_groq_client = AsyncGroqClient(redis_url)
    return _async_groq_client
