from rag.retriever import retrieve_medical_context

from config.settings import (
    get_llm_response,
    GROQ_MAIN_MODEL
)


RAG_SYSTEM_PROMPT = """
You are a healthcare AI assistant.

Answer ONLY using the provided medical context.

Rules:
- Do not hallucinate
- If answer not found, say you don't know
- Use simple language
- Be medically cautious
"""


def rag_medical_response(user_query: str):

    contexts = retrieve_medical_context(user_query)

    combined_context = "\n\n".join(contexts)

    messages = [
        {
            "role": "system",
            "content": RAG_SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": (
                f"Medical Context:\n{combined_context}\n\n"
                f"Question:\n{user_query}"
            )
        }
    ]

    response = get_llm_response(
        messages,
        model=GROQ_MAIN_MODEL,
        temperature=0.2,
        max_tokens=700
    )

    return response