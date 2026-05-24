from config.settings import (
    get_llm_response, GROQ_MAIN_MODEL,
    TEMP_EDUCATION, MAX_TOKENS_EDUCATION
)
from data.disease_keywords import COMMON_DISEASE_KEYWORDS
from config.logger import logger

EDUCATION_SYSTEM_PROMPT = """
You are a friendly rural health educator. Your job is to teach people about diseases,
health tips, and prevention in a very simple and friendly way.

Rules:
- Use very simple language, like you are talking to a farmer or village person
- Use short sentences and bullet points
- Give practical tips that are easy to follow in rural areas
- Be encouraging and positive
- Cover: What is the disease, How it spreads, Symptoms, Prevention, When to see doctor
- Keep response under 200 words
"""


# Common disease keywords for quick matching
DISEASE_KEYWORDS = COMMON_DISEASE_KEYWORDS


def get_disease_education(topic: str) -> str:
    """
    Provide education content about a disease or health topic.
    Returns a simple, easy-to-understand explanation.
    """
    messages = [
        {"role": "system", "content": EDUCATION_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Please teach me about: {topic}\n"
                "Include: what it is, how it spreads, symptoms, prevention, when to see doctor."
            ),
        },
    ]
    return get_llm_response(
        messages,
        model=GROQ_MAIN_MODEL,
        temperature=TEMP_EDUCATION,
        max_tokens=MAX_TOKENS_EDUCATION,
    )


def get_health_tip_of_day() -> str:
    """Generate a daily health tip for rural users."""
    messages = [
        {"role": "system", "content": EDUCATION_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Give one important daily health tip for rural people. "
                "Make it practical, simple, and actionable. Keep it under 80 words."
            ),
        },
    ]
    return get_llm_response(
        messages,
        model=GROQ_MAIN_MODEL,
        temperature=0.9,       # Higher temp for variety
        max_tokens=200,
    )


def detect_education_intent(user_input: str) -> bool:
    """
    Check if user is asking for education/information
    rather than reporting symptoms.
    """
    education_triggers = [
        "what is", "tell me about", "explain", "how does",
        "how to prevent", "what causes", "information about",
        "teach me", "i want to know", "kya hai", "batao",
        "ki jaankari", "what are", "symptoms of", "causes of",
    ]
    lower = user_input.lower()
    return any(trigger in lower for trigger in education_triggers)