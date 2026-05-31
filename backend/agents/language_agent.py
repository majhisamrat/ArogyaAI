from tools.language_tool import (
    process_language,
    translate_to_user_language,
    apply_response_style
)

from config.logger import logger


class LanguageAgent:
    """
    Responsible for:
    - Detecting user's language
    - Detecting conversational response style
    - Translating input to English for internal AI processing
    - Translating final response back to user language
    - Preserving Banglish / Hinglish conversation style
    """

    def __init__(self):

        self.name = "LanguageAgent"

    def process_input(
        self,
        user_input: str,
        preferred_lang: str = None
    ) -> dict:
        """
        Step 1:
        Detect language + conversational style.
        Translate input into English.
        """

        result = process_language(
            user_input,
            preferred_lang
        )

        logger.info(
            f"[{self.name}] "
            f"Language: {result['language_name']} | "
            f"Style: {result['response_style']} | "
            f"Input: {user_input[:50]}"
        )

        return result

    def translate_response(
        self,
        response_text: str,
        target_lang: str,
        response_style: str = "english"
    ) -> str:
        """
        Translate and preserve conversational style.
        - Transliteration styles (hinglish, banglish, tanglish, etc.) → apply_response_style
        - Native script styles (hindi, bengali, tamil, etc.) → translate_to_user_language
        - English → return as-is
        """

        # All transliteration/romanised styles — respond using English letters
        transliteration_styles = {
            "hinglish", "banglish", "tanglish", "tenglish",
            "manglish", "gujarish", "kanglish", "manglish_ml",
            "punglish", "odish"
        }

        if response_style in transliteration_styles:
            styled = apply_response_style(response_text, response_style)
            logger.info(
                f"[{self.name}] Applied transliteration style: {response_style}"
            )
            return styled

        # For native script languages (hi, bn, ta, te, mr, gu, kn, ml, pa, od)
        # translate_to_user_language handles the proper script
        translated = translate_to_user_language(response_text, target_lang)
        logger.info(
            f"[{self.name}] Translated to: {target_lang} (style: {response_style})"
        )
        return translated