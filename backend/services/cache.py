"""
Redis Response Cache for Groq API Responses

Caches LLM responses to avoid redundant API calls for identical prompts.
- Uses SHA256 hash of (prompt + model + system_prompt) as cache key
- 24-hour TTL by default
- Thread-safe operations
"""

import hashlib
import json
import redis
from typing import Optional, Dict, Any
from config.logger import logger


class ResponseCache:
    """
    Cache layer for LLM responses using Redis.
    
    Cache key generation:
    - SHA256(user_prompt + model + system_prompt)
    
    TTL: 24 hours (86400 seconds)
    """

    DEFAULT_TTL = 86400  # 24 hours
    CACHE_PREFIX = "groq_cache:"

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """
        Initialize Redis cache.
        
        Args:
            redis_url: Redis connection URL
        """
        try:
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
            )
            # Test connection
            self.redis_client.ping()
            logger.info("[ResponseCache] Connected to Redis successfully")
        except Exception as e:
            logger.error(f"[ResponseCache] Failed to connect to Redis: {e}")
            self.redis_client = None

    @staticmethod
    def _generate_cache_key(
        user_prompt: str,
        model: str,
        system_prompt: str = ""
    ) -> str:
        """
        Generate SHA256 hash-based cache key.
        
        Args:
            user_prompt: The user's input prompt
            model: Model name (e.g., "llama-3.3-70b-versatile")
            system_prompt: System prompt if any
            
        Returns:
            Cache key string
        """
        combined = f"{user_prompt}|{model}|{system_prompt}"
        hash_digest = hashlib.sha256(combined.encode()).hexdigest()
        return f"{ResponseCache.CACHE_PREFIX}{hash_digest}"

    def get(
        self,
        user_prompt: str,
        model: str,
        system_prompt: str = ""
    ) -> Optional[str]:
        """
        Retrieve cached response.
        
        Args:
            user_prompt: The user's input prompt
            model: Model name
            system_prompt: System prompt if any
            
        Returns:
            Cached response string or None if not found
        """
        if not self.redis_client:
            return None

        try:
            cache_key = self._generate_cache_key(user_prompt, model, system_prompt)
            response = self.redis_client.get(cache_key)

            if response:
                logger.info(f"[ResponseCache] Cache HIT for key: {cache_key[:20]}...")
                return response
            else:
                logger.debug(f"[ResponseCache] Cache MISS for key: {cache_key[:20]}...")
                return None

        except Exception as e:
            logger.warning(f"[ResponseCache] Error retrieving from cache: {e}")
            return None

    def set(
        self,
        response: str,
        user_prompt: str,
        model: str,
        system_prompt: str = "",
        ttl: int = DEFAULT_TTL
    ) -> bool:
        """
        Store response in cache.
        
        Args:
            response: The LLM response to cache
            user_prompt: The user's input prompt
            model: Model name
            system_prompt: System prompt if any
            ttl: Time-to-live in seconds
            
        Returns:
            True if successfully cached, False otherwise
        """
        if not self.redis_client:
            return False

        try:
            cache_key = self._generate_cache_key(user_prompt, model, system_prompt)
            self.redis_client.setex(cache_key, ttl, response)
            logger.info(
                f"[ResponseCache] Cached response for key: {cache_key[:20]}... "
                f"(TTL: {ttl}s)"
            )
            return True

        except Exception as e:
            logger.warning(f"[ResponseCache] Error storing in cache: {e}")
            return False

    def clear_by_prefix(self, prefix: str = CACHE_PREFIX) -> int:
        """
        Clear all cache entries matching prefix.
        
        Args:
            prefix: Cache key prefix to clear
            
        Returns:
            Number of keys deleted
        """
        if not self.redis_client:
            return 0

        try:
            cursor = 0
            count = 0
            while True:
                cursor, keys = self.redis_client.scan(
                    cursor,
                    match=f"{prefix}*",
                    count=100
                )
                if keys:
                    count += self.redis_client.delete(*keys)
                if cursor == 0:
                    break

            logger.info(f"[ResponseCache] Cleared {count} cache entries")
            return count

        except Exception as e:
            logger.error(f"[ResponseCache] Error clearing cache: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache info
        """
        if not self.redis_client:
            return {"status": "disconnected"}

        try:
            cursor = 0
            count = 0
            while True:
                cursor, keys = self.redis_client.scan(
                    cursor,
                    match=f"{self.CACHE_PREFIX}*",
                    count=100
                )
                if keys:
                    count += len(keys)
                if cursor == 0:
                    break

            return {
                "status": "connected",
                "cached_responses": count,
                "prefix": self.CACHE_PREFIX,
            }

        except Exception as e:
            logger.error(f"[ResponseCache] Error getting stats: {e}")
            return {"status": "error", "error": str(e)}


# Global cache instance
_response_cache: Optional[ResponseCache] = None


def get_response_cache(redis_url: str = "redis://localhost:6379/0") -> ResponseCache:
    """
    Get or create the global response cache instance.
    
    Args:
        redis_url: Redis connection URL
        
    Returns:
        ResponseCache instance
    """
    global _response_cache
    if _response_cache is None:
        _response_cache = ResponseCache(redis_url)
    return _response_cache
