from typing import List

from config.logger import logger
from config.settings import MEM0_API_KEY


class Mem0Client:
    def __init__(self, api_key: str = None):
        self.client = None
        api_key = api_key or MEM0_API_KEY

        if not api_key:
            logger.warning("MEM0_API_KEY is not configured; Mem0 memory is disabled.")
            return

        try:
            from mem0 import MemoryClient

            self.client = MemoryClient(api_key=api_key)
        except Exception as exc:
            logger.warning(f"Unable to initialize Mem0 client: {exc}")
            self.client = None

    def add_memory(self, user_id: str, messages: list, metadata: dict = None):
        if not self.client:
            return

        try:
            self.client.add(messages, user_id=user_id)
        except Exception as exc:
            logger.error(f"Mem0 add_memory failed: {exc}")

    def search(self, user_id: str, query: str, top_k: int = 3):
        if not self.client or not query:
            return []

        try:
            results = self.client.search(query, filters={"user_id": user_id})
            if isinstance(results, dict):
                return results.get("results", [])[:top_k]
            return results[:top_k]
        except Exception as exc:
            logger.warning(f"Mem0 search failed: {exc}")
            return []

    def format_search_results(self, results: List[dict]):
        formatted = []
        for item in results:
            memory_text = item.get("memory") or item.get("content") or item.get("text")
            if memory_text:
                formatted.append(memory_text)
        return formatted
