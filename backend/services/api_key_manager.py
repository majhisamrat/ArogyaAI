"""
API Key Manager for High-Concurrency Groq Requests

Manages multiple Groq API keys with:
- Load balancing based on active requests
- Health tracking per key
- Cooldown periods for unhealthy keys
- Automatic recovery after cooldown
"""

import os
import time
import threading
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from config.logger import logger


@dataclass
class APIKeyStats:
    """Tracks statistics for a single API key"""
    name: str
    api_key: str
    active_requests: int = 0
    healthy: bool = True
    cooldown_until: float = 0.0  # Unix timestamp
    total_requests: int = 0
    total_failures: int = 0
    last_error: Optional[str] = None
    last_used: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        return {
            "name": self.name,
            "active_requests": self.active_requests,
            "healthy": self.healthy,
            "cooldown_until": self.cooldown_until,
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "last_error": self.last_error,
        }


class APIKeyManager:
    """
    Manages pool of Groq API keys with load balancing and health checking.
    
    Features:
    - Loads keys from environment variables (GROQ_API_KEY_1, GROQ_API_KEY_2, etc.)
    - Tracks active requests per key
    - Implements health checking with cooldown
    - Provides least-busy load balancing
    - Thread-safe operations
    """

    COOLDOWN_DURATION = 60  # seconds
    ERROR_CODES = {401, 403, 429, 500, 502, 503, 504}  # HTTP status codes that mark key as unhealthy

    def __init__(self):
        """Initialize API key manager by loading keys from environment"""
        self._keys: List[APIKeyStats] = []
        self._lock = threading.RLock()
        self._current_round_robin_index = 0
        self._load_keys_from_env()

        if not self._keys:
            logger.warning(
                "[APIKeyManager] No API keys loaded! Set GROQ_API_KEY_1, "
                "GROQ_API_KEY_2, etc. in environment variables"
            )
        else:
            logger.info(
                f"[APIKeyManager] Loaded {len(self._keys)} API keys"
            )

    def _load_keys_from_env(self) -> None:
        """Load API keys from environment variables GROQ_API_KEY_1 to GROQ_API_KEY_6"""
        for i in range(1, 7):  # Support up to 6 keys
            key = os.getenv(f"GROQ_API_KEY_{i}")
            if key:
                stats = APIKeyStats(
                    name=f"Key{i}",
                    api_key=key
                )
                self._keys.append(stats)
                logger.info(f"[APIKeyManager] Loaded GROQ_API_KEY_{i}")

    def get_best_key(self) -> Optional[APIKeyStats]:
        """
        Select the best API key using least-busy load balancing.
        
        Algorithm:
        1. Ignore unhealthy keys
        2. Ignore keys in cooldown
        3. Select key with fewest active requests
        4. If tie, use round-robin
        
        Returns:
            APIKeyStats or None if no healthy keys available
        """
        with self._lock:
            self.auto_recover_keys()  # Auto-recover expired cooldowns
            current_time = time.time()

            # Get available keys (healthy and not in cooldown)
            available_keys = [
                key for key in self._keys
                if key.healthy and key.cooldown_until <= current_time
            ]

            if not available_keys:
                logger.warning(
                    "[APIKeyManager] No healthy keys available! "
                    f"Total keys: {len(self._keys)}, "
                    f"Healthy: {sum(1 for k in self._keys if k.healthy)}"
                )
                return None

            # Sort by active requests (ascending)
            available_keys.sort(key=lambda k: k.active_requests)

            # Get the key with fewest active requests
            best_key = available_keys[0]

            # If multiple keys have same load, use round-robin
            same_load_keys = [
                k for k in available_keys
                if k.active_requests == best_key.active_requests
            ]

            if len(same_load_keys) > 1:
                best_key = same_load_keys[
                    self._current_round_robin_index % len(same_load_keys)
                ]
                self._current_round_robin_index += 1

            logger.info(
                f"[APIKeyManager] Selected {best_key.name} | "
                f"Active: {best_key.active_requests} | "
                f"Total requests: {best_key.total_requests}"
            )

            return best_key

    def mark_request_start(self, key_stats: APIKeyStats) -> None:
        """Increment active request count"""
        with self._lock:
            key_stats.active_requests += 1
            key_stats.total_requests += 1
            key_stats.last_used = time.time()

    def mark_request_end(self, key_stats: APIKeyStats) -> None:
        """Decrement active request count"""
        with self._lock:
            if key_stats.active_requests > 0:
                key_stats.active_requests -= 1

    def mark_key_unhealthy(
        self,
        key_stats: APIKeyStats,
        error_code: int,
        error_msg: str = ""
    ) -> None:
        """
        Mark a key as unhealthy and put it into cooldown.
        
        Args:
            key_stats: The key to mark unhealthy
            error_code: HTTP status code that triggered this
            error_msg: Error message for logging
        """
        with self._lock:
            key_stats.healthy = False
            key_stats.total_failures += 1
            key_stats.cooldown_until = time.time() + self.COOLDOWN_DURATION
            key_stats.last_error = f"[{error_code}] {error_msg}"

            logger.warning(
                f"[APIKeyManager] {key_stats.name} marked unhealthy | "
                f"Error: {key_stats.last_error} | "
                f"Cooldown until: {key_stats.cooldown_until} | "
                f"Failures: {key_stats.total_failures}"
            )

    def recover_key(self, key_stats: APIKeyStats) -> None:
        """
        Recover a key from cooldown after COOLDOWN_DURATION seconds.
        Called by health check or automatically.
        """
        with self._lock:
            if not key_stats.healthy and key_stats.cooldown_until <= time.time():
                key_stats.healthy = True
                key_stats.last_error = None
                logger.info(
                    f"[APIKeyManager] {key_stats.name} recovered from cooldown"
                )

    def auto_recover_keys(self) -> None:
        """
        Check all keys and recover those whose cooldown has expired.
        Should be called periodically or after failed requests.
        """
        with self._lock:
            current_time = time.time()
            for key in self._keys:
                if not key.healthy and key.cooldown_until <= current_time:
                    self.recover_key(key)

    def get_status(self) -> Dict[str, Any]:
        """
        Get status of all keys for monitoring.
        
        Returns:
            Dict with keys array containing status of each key
        """
        with self._lock:
            self.auto_recover_keys()  # Auto-recover expired cooldowns
            return {
                "keys": [key.to_dict() for key in self._keys],
                "total_keys": len(self._keys),
                "healthy_keys": sum(1 for k in self._keys if k.healthy),
            }

    def get_all_keys(self) -> List[APIKeyStats]:
        """Get list of all key stats"""
        with self._lock:
            return self._keys.copy()

    def get_key_by_name(self, name: str) -> Optional[APIKeyStats]:
        """Get key stats by name (Key1, Key2, etc.)"""
        with self._lock:
            for key in self._keys:
                if key.name == name:
                    return key
            return None


# Global instance
_api_key_manager: Optional[APIKeyManager] = None


def get_api_key_manager() -> APIKeyManager:
    """Get or create the global API key manager instance"""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager
