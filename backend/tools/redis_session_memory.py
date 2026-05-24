import json
import logging

import redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class RedisSessionMemory:
    def __init__(self, redis_url: str = "redis://localhost:6379/0", max_messages: int = 20):
        self.max_messages = max_messages
        self.local_cache = {}
        self.client = None

        try:
            self.client = redis.Redis.from_url(redis_url, decode_responses=True)
            self.client.ping()
        except Exception as exc:
            logger.warning(f"Redis session memory unavailable: {exc}")
            self.client = None

    def _recent_key(self, phone_number: str) -> str:
        return f"session:recent:{phone_number}"

    def _state_key(self, phone_number: str) -> str:
        return f"session:state:{phone_number}"

    def _context_key(self, phone_number: str) -> str:
        return f"session:context:{phone_number}"

    def save_message(self, phone_number: str, role: str, content: str):
        payload = json.dumps({"role": role, "content": content}, ensure_ascii=False)

        if self.client:
            try:
                self.client.rpush(self._recent_key(phone_number), payload)
                self.client.ltrim(self._recent_key(phone_number), -self.max_messages, -1)
                return
            except RedisError as exc:
                logger.warning(f"Unable to save session message to Redis: {exc}")

        self._save_local_message(phone_number, role, content)

    def _save_local_message(self, phone_number: str, role: str, content: str):
        entry = {"role": role, "content": content}
        bucket = self.local_cache.setdefault(phone_number, {"recent": [], "state": None, "context": None})
        bucket["recent"].append(entry)
        bucket["recent"] = bucket["recent"][-self.max_messages:]

    def get_recent_messages(self, phone_number: str, limit: int = 10):
        if self.client:
            try:
                items = self.client.lrange(self._recent_key(phone_number), -limit, -1)
                return [json.loads(item) for item in items if item]
            except RedisError as exc:
                logger.warning(f"Unable to read session messages from Redis: {exc}")

        bucket = self.local_cache.get(phone_number, {"recent": []})
        return bucket["recent"][-limit:]

    def save_dialogue_state(self, phone_number: str, state: dict):
        payload = json.dumps(state, ensure_ascii=False)

        if self.client:
            try:
                self.client.set(self._state_key(phone_number), payload)
                return
            except RedisError as exc:
                logger.warning(f"Unable to save dialogue state to Redis: {exc}")

        bucket = self.local_cache.setdefault(phone_number, {"recent": [], "state": None, "context": None})
        bucket["state"] = state

    def load_session_context(self, phone_number: str):
        if self.client:
            try:
                raw = self.client.get(self._context_key(phone_number))
                if raw:
                    return raw
            except RedisError as exc:
                logger.warning(f"Unable to load session context from Redis: {exc}")

        bucket = self.local_cache.get(phone_number, {"recent": [], "state": None, "context": None})
        return bucket["context"]

    def save_session_context(self, phone_number: str, context):
        payload = context if isinstance(context, str) else json.dumps(context, ensure_ascii=False)

        if self.client:
            try:
                self.client.set(self._context_key(phone_number), payload)
                return
            except RedisError as exc:
                logger.warning(f"Unable to save session context to Redis: {exc}")

        bucket = self.local_cache.setdefault(phone_number, {"recent": [], "state": None, "context": None})
        bucket["context"] = payload

    def load_dialogue_state(self, phone_number: str):
        if self.client:
            try:
                raw = self.client.get(self._state_key(phone_number))
                if raw:
                    return json.loads(raw)
            except RedisError as exc:
                logger.warning(f"Unable to load dialogue state from Redis: {exc}")

        bucket = self.local_cache.get(phone_number, {"state": None})
        return bucket["state"]
