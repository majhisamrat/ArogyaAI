from sentence_transformers import (
    SentenceTransformer,
    util
)

MODEL = SentenceTransformer(
    "all-MiniLM-L6-v2"
)


class MemorySelectorAgent:

    def rank_memories(
        self,
        query,
        memories,
        top_k=3
    ):

        if not memories:
            return []

        query_embedding = MODEL.encode(
            query,
            convert_to_tensor=True,
            show_progress_bar=False
        )

        scored = []

        for memory in memories:

            text = memory.get("text", "")

            memory_embedding = MODEL.encode(
                text,
                convert_to_tensor=True,
                show_progress_bar=False
            )

            similarity = util.cos_sim(

                query_embedding,

                memory_embedding
            ).item()

            scored.append({

                "text": text,

                "score": similarity
            })

        scored.sort(

            key=lambda x: x["score"],

            reverse=True
        )

        return scored[:top_k]