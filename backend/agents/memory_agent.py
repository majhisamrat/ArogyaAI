from config.settings import (
    get_llm_response,
    GROQ_FAST_MODEL
)


class MemoryAgent:

    def summarize_conversation(
        self,
        messages
    ):

        text = "\n".join([
            f"{m['role']}: {m['content']}"
            for m in messages
        ])

        prompt = [
            {
                "role": "system",
                "content": (
                    "Summarize this medical conversation.\n"
                    "Keep only medically important details.\n"
                    "Include:\n"
                    "- symptoms\n"
                    "- duration\n"
                    "- diseases\n"
                    "- medicines\n"
                    "- allergies\n"
                    "- severity\n"
                    "Keep under 150 words."
                )
            },
            {
                "role": "user",
                "content": text
            }
        ]

        return get_llm_response(
            prompt,
            model=GROQ_FAST_MODEL,
            temperature=0.2,
            max_tokens=200
        )