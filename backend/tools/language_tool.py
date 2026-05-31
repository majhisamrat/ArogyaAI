import json

from config.settings import (
    get_llm_response,
    GROQ_FAST_MODEL,
    TEMP_LANGUAGE,
    MAX_TOKENS_LANGUAGE,
    SUPPORTED_LANGUAGES
)

from config.logger import logger


# LLM LANGUAGE + STYLE ANALYZER

def analyze_language_style(user_input: str) -> dict:
    """
    Use LLM to detect:
    - language (one of 11 Indian languages + English)
    - conversational style (script or transliteration mode)
    """

    messages = [
        {
            "role": "system",
            "content": """
You are a multilingual Indian language analyzer.

Analyze the user's message and return ONLY valid JSON.

Supported language codes:
- en  → English
- hi  → Hindi
- bn  → Bengali
- ta  → Tamil
- te  → Telugu
- mr  → Marathi
- gu  → Gujarati
- kn  → Kannada
- ml  → Malayalam
- pa  → Punjabi
- od  → Odia

Supported styles:
- english      : English written in English script
- hindi        : Hindi written in Devanagari script
- hinglish     : Hindi written using English/Roman letters (e.g. "mujhe bukhar hai")
- bengali      : Bengali written in Bengali script
- banglish     : Bengali written using English/Roman letters (e.g. "ami jante chai")
- tamil        : Tamil written in Tamil script
- tanglish     : Tamil written using English/Roman letters (e.g. "enakku kaichal irukku")
- telugu       : Telugu written in Telugu script
- tenglish     : Telugu written using English/Roman letters (e.g. "naku jwaram ga undi")
- marathi      : Marathi written in Devanagari script
- manglish     : Marathi written using English/Roman letters (e.g. "mala tar vatat ahe")
- gujarati     : Gujarati written in Gujarati script
- gujarish     : Gujarati written using English/Roman letters (e.g. "mane taav aave che")
- kannada      : Kannada written in Kannada script
- kanglish     : Kannada written using English/Roman letters (e.g. "nanage jwara iddhe")
- malayalam    : Malayalam written in Malayalam script
- manglish_ml  : Malayalam written using English/Roman letters (e.g. "enikku pani und")
- punjabi      : Punjabi written in Gurmukhi script
- punglish     : Punjabi written using English/Roman letters (e.g. "mane bukhar hai")
- odia         : Odia written in Odia script
- odish        : Odia written using English/Roman letters

Examples:
"I have fever" → {"language":"en","style":"english"}
"मुझे बुखार है" → {"language":"hi","style":"hindi"}
"mujhe bukhar hai" → {"language":"hi","style":"hinglish"}
"আমার জ্বর হয়েছে" → {"language":"bn","style":"bengali"}
"ami jante chai" → {"language":"bn","style":"banglish"}
"எனக்கு காய்ச்சல்" → {"language":"ta","style":"tamil"}
"enakku kaichal irukku" → {"language":"ta","style":"tanglish"}
"నాకు జ్వరంగా ఉంది" → {"language":"te","style":"telugu"}
"naku jwaram ga undi" → {"language":"te","style":"tenglish"}
"मला ताप आला आहे" → {"language":"mr","style":"marathi"}
"mala tar vatat ahe" → {"language":"mr","style":"manglish"}
"મને તાવ આવે છે" → {"language":"gu","style":"gujarati"}
"mane taav aave che" → {"language":"gu","style":"gujarish"}
"ನನಗೆ ಜ್ವರ ಇದೆ" → {"language":"kn","style":"kannada"}
"nanage jwara iddhe" → {"language":"kn","style":"kanglish"}
"എനിക്ക് പനി ഉണ്ട്" → {"language":"ml","style":"malayalam"}
"enikku pani und" → {"language":"ml","style":"manglish_ml"}
"ਮੈਨੂੰ ਬੁਖਾਰ ਹੈ" → {"language":"pa","style":"punjabi"}
"mane bukhar hai" → {"language":"pa","style":"punglish"}
"ମୋର ଜ୍ୱର ଅଛି" → {"language":"od","style":"odia"}

Return ONLY JSON like: {"language":"ta","style":"tanglish"}
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

        allowed_languages = list(SUPPORTED_LANGUAGES.keys())

        # All known styles including all 11 languages + transliterations
        allowed_styles = [
            "english",
            "hindi", "hinglish",
            "bengali", "banglish",
            "tamil", "tanglish",
            "telugu", "tenglish",
            "marathi", "manglish",
            "gujarati", "gujarish",
            "kannada", "kanglish",
            "malayalam", "manglish_ml",
            "punjabi", "punglish",
            "odia", "odish",
        ]

        if language not in allowed_languages:
            language = "en"

        if style not in allowed_styles:
            # Fallback: map unknown style to the base language style
            style = language if language != "en" else "english"
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


# TRANSLATE TO ENGLISH

def translate_to_english(
    text: str,
    source_lang: str
) -> str:
    """
    Translate user input into English.
    """

    if source_lang == "en":
        return text

    lang_name = SUPPORTED_LANGUAGES.get(source_lang, source_lang)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a multilingual medical translation assistant.\n"
                "Translate the user's message into clear English.\n\n"
                "You understand ALL of these languages and scripts:\n"
                "- Hindi (Devanagari script and Roman/Hinglish)\n"
                "- Bengali (Bengali script and Roman/Banglish)\n"
                "- Tamil (Tamil script and Roman/Tanglish)\n"
                "- Telugu (Telugu script and Roman/Tenglish)\n"
                "- Marathi (Devanagari script and Roman transliteration)\n"
                "- Gujarati (Gujarati script and Roman transliteration)\n"
                "- Kannada (Kannada script and Roman/Kanglish)\n"
                "- Malayalam (Malayalam script and Roman/Manglish)\n"
                "- Punjabi (Gurmukhi script and Roman/Punglish)\n"
                "- Odia (Odia script and Roman transliteration)\n\n"
                "IMPORTANT RULES:\n"
                "- Preserve medical meaning accurately\n"
                "- Do NOT mistranslate disease names\n"
                "- Do NOT mistranslate vaccine names\n"
                "- Preserve pregnancy-related meaning carefully\n"
                "- If a medical term already exists in English, keep it unchanged\n"
                "- Return ONLY translated English text, nothing else\n"
            )
        },
        {
            "role": "user",
            "content": (
                f"Translate from "
                f"{lang_name} "
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


# TRANSLATE TO USER LANGUAGE


def translate_to_user_language(
    text: str,
    target_lang: str
) -> str:
    """
    Translate AI response into target language.
    Works for all 11 supported languages.
    """

    if target_lang == "en":
        return text

    lang_name = SUPPORTED_LANGUAGES.get(
        target_lang,
        target_lang
    )

    # Script hints so the LLM uses the correct script for each language
    script_hints = {
        "hi": "Devanagari script (हिन्दी)",
        "bn": "Bengali script (বাংলা)",
        "ta": "Tamil script (தமிழ்)",
        "te": "Telugu script (తెలుగు)",
        "mr": "Devanagari script (मराठी)",
        "gu": "Gujarati script (ગુજરાતી)",
        "kn": "Kannada script (ಕನ್ನಡ)",
        "ml": "Malayalam script (മലയാളം)",
        "pa": "Gurmukhi script (ਪੰਜਾਬੀ)",
        "od": "Odia script (ଓଡ଼ିଆ)",
    }
    script_hint = script_hints.get(target_lang, "")

    messages = [
        {
            "role": "system",
            "content": (
                f"You are a medical translator.\n"
                f"Translate the given English text to {lang_name}.\n"
                f"Use the {script_hint} to write the translation.\n"
                f"Use simple, rural-friendly language.\n"
                f"Preserve all medical terms and advice accurately.\n"
                f"Return ONLY the translated text in {lang_name}, nothing else."
            )
        },
        {
            "role": "user",
            "content": f"Translate to {lang_name}:\n{text}"
        }
    ]

    translated = get_llm_response(
        messages,
        model=GROQ_FAST_MODEL,
        temperature=TEMP_LANGUAGE,
        max_tokens=700
    )

    logger.info(
        f"[LanguageTool] English → {target_lang} ({lang_name}) | Output: {translated[:60]}"
    )

    return translated

# RESPONSE STYLE CONVERTER

def apply_response_style(
    text: str,
    style: str
) -> str:
    """
    Convert response into the user's conversational script/style.
    Handles all transliteration modes (Hinglish, Banglish, Tanglish, etc.)
    """

    # Map each transliteration style to a plain-English description for the LLM
    transliteration_styles = {
        "hinglish":    ("Hinglish",     "Hindi written using English/Roman letters"),
        "banglish":    ("Banglish",     "Bengali written using English/Roman letters"),
        "tanglish":    ("Tanglish",     "Tamil written using English/Roman letters"),
        "tenglish":    ("Tenglish",     "Telugu written using English/Roman letters"),
        "manglish":    ("Manglish",     "Marathi written using English/Roman letters"),
        "gujarish":    ("Gujarish",     "Gujarati written using English/Roman letters"),
        "kanglish":    ("Kanglish",     "Kannada written using English/Roman letters"),
        "manglish_ml": ("Manglish",     "Malayalam written using English/Roman letters"),
        "punglish":    ("Punglish",     "Punjabi written using English/Roman letters"),
        "odish":       ("Odish",        "Odia written using English/Roman letters"),
    }

    if style in transliteration_styles:
        style_name, style_def = transliteration_styles[style]
        messages = [
            {
                "role": "system",
                "content": (
                    f"Convert the response into natural {style_name}.\n"
                    f"{style_name} means {style_def}.\n"
                    f"Write every word using only English/Roman letters — do NOT use any native script.\n"
                    f"Keep the medical meaning intact.\n"
                    f"Return ONLY the converted text."
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

    # For native-script styles (hindi, bengali, tamil, etc.) fall through to
    # translate_to_user_language which handles proper script rendering
    return text


# MAIN PROCESS FUNCTION

def process_language(
    user_input: str,
    preferred_lang: str = None
) -> dict:
    """
    Detect language + conversational style.
    Translate user input into English.

    IMPORTANT: The response language is determined by the user's ACTUAL typed
    language, not their database preference. preferred_lang is ONLY used as a
    last-resort fallback when language detection itself fails (i.e. LLM could
    not classify the input at all, not when user types in English).
    """

    analysis = analyze_language_style(user_input)

    detected_lang = analysis["language"]

    response_style = analysis["style"]

    # NOTE: We intentionally do NOT override detected_lang with preferred_lang.
    # If the user typed in English (detected_lang == 'en'), respond in English.
    # If the user typed in Hindi (detected_lang == 'hi'), respond in Hindi.
    # The preferred_lang from DB profile is used for WhatsApp-initiated sessions
    # where language cannot be auto-detected (e.g. short greeting text).
    # For the web chat, we always honor the detected language from the message.

    english_text = translate_to_english(
        user_input,
        detected_lang
    )

    logger.info(
        f"[LanguageTool] "
        f"Language={detected_lang} | "
        f"Style={response_style} | "
        f"PreferredLang (ignored for response)={preferred_lang}"
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