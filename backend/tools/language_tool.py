import json

from config.settings import (
    get_llm_response,
    GROQ_FAST_MODEL,
    TEMP_LANGUAGE,
    MAX_TOKENS_LANGUAGE,
    SUPPORTED_LANGUAGES
)

from config.logger import logger


# ══════════════════════════════════════════════════════
# LLM LANGUAGE + STYLE ANALYZER
# ══════════════════════════════════════════════════════

def analyze_language_style(user_input: str) -> dict:
    """
    Use LLM to detect:
    - language
    - conversational style
    """

    messages = [
        {
            "role": "system",
            "content": """
You are a multilingual language analyzer.

Analyze the user's message.

Return ONLY valid JSON.

Supported language codes:
- en
- bn
- hi

Supported styles:
- english
- bengali
- hindi
- banglish
- hinglish

Definitions:

english:
English written in English script.

bengali:
Bengali written in Bengali script.

hindi:
Hindi written in Devanagari script.

banglish:
Bengali written using English letters.

hinglish:
Hindi written using English letters.

Examples:

"ami jante chai"
→ {"language":"bn","style":"banglish"}

"mujhe bukhar hai"
→ {"language":"hi","style":"hinglish"}

"আমি জানতে চাই"
→ {"language":"bn","style":"bengali"}

"I have fever"
→ {"language":"en","style":"english"}

Return ONLY JSON.
"""
        },
        {
            "role": "user",
            "content": user_input
        }
    ]

    result = get_llm_response(
        messages,
        model=GROQ_FAST_MODEL,
        temperature=0,
        max_tokens=50
    )

    try:

        cleaned = (
            result
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

        parsed = json.loads(cleaned)

        language = parsed.get("language", "en")
        style = parsed.get("style", "english")

        allowed_languages = ["en", "bn", "hi"]

        allowed_styles = [
            "english",
            "bengali",
            "hindi",
            "banglish",
            "hinglish"
        ]

        if language not in allowed_languages:
            language = "en"

        if style not in allowed_styles:
            style = "english"

        logger.info(
            f"[LanguageAnalyzer] "
            f"Language={language} | Style={style}"
        )

        return {
            "language": language,
            "style": style
        }

    except Exception as e:

        logger.info(
            f"[LanguageAnalyzer] Parse failed: {e}"
        )

        return {
            "language": "en",
            "style": "english"
        }


# ══════════════════════════════════════════════════════
# TRANSLATE TO ENGLISH
# ══════════════════════════════════════════════════════

def translate_to_english(
    text: str,
    source_lang: str
) -> str:
    """
    Translate user input into English.
    """

    if source_lang == "en":
        return text

    messages = [
        {
            "role": "system",
            "content": """
You are a multilingual medical translation assistant.

Translate the user's message into clear English.

IMPORTANT RULES:
- Preserve medical meaning accurately
- Do NOT mistranslate disease names
- Do NOT mistranslate vaccine names
- Preserve pregnancy-related meaning carefully
- Understand Bengali, Hindi, Hinglish, Banglish, and mixed-language inputs
- If a medical term already exists in English, keep it unchanged
- Return ONLY translated English text
"""
        },
        {
            "role": "user",
            "content": (
                f"Translate from "
                f"{SUPPORTED_LANGUAGES.get(source_lang, source_lang)} "
                f"to English:\n\n{text}"
            )
        }
    ]

    translated = get_llm_response(
        messages,
        model=GROQ_FAST_MODEL,
        temperature=TEMP_LANGUAGE,
        max_tokens=MAX_TOKENS_LANGUAGE
    )

    logger.info(
        f"[LanguageTool] {source_lang} → English | "
        f"Original: {text[:50]} | "
        f"Translated: {translated[:50]}"
    )

    return translated.strip()


# ══════════════════════════════════════════════════════
# TRANSLATE TO USER LANGUAGE
# ══════════════════════════════════════════════════════

def translate_to_user_language(
    text: str,
    target_lang: str
) -> str:
    """
    Translate AI response into target language.
    """

    if target_lang == "en":
        return text

    lang_name = SUPPORTED_LANGUAGES.get(
        target_lang,
        target_lang
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are a translator.\n"
                "Translate the given text to the target language.\n"
                "Use simple, rural-friendly language.\n"
                "Preserve medical meaning carefully.\n"
                "Return ONLY translated text."
            )
        },
        {
            "role": "user",
            "content": f"Translate to {lang_name}:\n{text}"
        }
    ]

    return get_llm_response(
        messages,
        model=GROQ_FAST_MODEL,
        temperature=TEMP_LANGUAGE,
        max_tokens=512
    )


# ══════════════════════════════════════════════════════
# RESPONSE STYLE CONVERTER
# ══════════════════════════════════════════════════════

def apply_response_style(
    text: str,
    style: str
) -> str:
    """
    Convert response into conversational style.
    """

    if style == "banglish":

        messages = [
            {
                "role": "system",
                "content": (
                    "Convert the response into natural Banglish.\n"
                    "Banglish means Bengali written using English letters.\n"
                    "Return ONLY the converted text."
                )
            },
            {
                "role": "user",
                "content": text
            }
        ]

        return get_llm_response(
            messages,
            model=GROQ_FAST_MODEL,
            temperature=0.3,
            max_tokens=700
        )

    elif style == "hinglish":

        messages = [
            {
                "role": "system",
                "content": (
                    "Convert the response into natural Hinglish.\n"
                    "Hinglish means Hindi written using English letters.\n"
                    "Return ONLY the converted text."
                )
            },
            {
                "role": "user",
                "content": text
            }
        ]

        return get_llm_response(
            messages,
            model=GROQ_FAST_MODEL,
            temperature=0.3,
            max_tokens=700
        )

    return text


# ══════════════════════════════════════════════════════
# MAIN PROCESS FUNCTION
# ══════════════════════════════════════════════════════

def process_language(
    user_input: str,
    preferred_lang: str = None
) -> dict:
    """
    Detect language + conversational style.
    Translate user input into English.
    """

    analysis = analyze_language_style(user_input)

    detected_lang = analysis["language"]

    response_style = analysis["style"]

    # Optional fallback
    if detected_lang == "en" and preferred_lang:
        detected_lang = preferred_lang

    english_text = translate_to_english(
        user_input,
        detected_lang
    )

    logger.info(
        f"[LanguageTool] "
        f"Language={detected_lang} | "
        f"Style={response_style}"
    )

    return {
        "detected_language": detected_lang,
        "language_name": SUPPORTED_LANGUAGES.get(
            detected_lang,
            "English"
        ),
        "response_style": response_style,
        "original_text": user_input,
        "english_text": english_text,
    }