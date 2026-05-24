from config.settings import (
    get_llm_response,
    GROQ_FAST_MODEL
)


def build_medical_context(
    conversation_messages: list
) -> str:

    if not conversation_messages:

        return ""

    history_text = ""

    for msg in conversation_messages[-12:]:

        role = msg["role"]

        content = msg["content"]

        history_text += (
            f"{role}: {content}\n"
        )

    prompt = f"""
You are a medical conversation memory system.

Your task:
Summarize the user's CURRENT medical situation from the conversation.

Focus on:
- symptom timeline
- symptom progression
- ongoing symptoms
- severity changes
- duration
- relevant context

Keep it concise.

Conversation:

{history_text}
"""

    summary = get_llm_response(

        [
            {
                "role": "system",
                "content": (
                    "You summarize medical conversations."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],

        model=GROQ_FAST_MODEL,

        temperature=0.2,

        max_tokens=200
    )

    return summary