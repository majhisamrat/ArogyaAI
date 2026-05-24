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
        """
        # Banglish / Hinglish special handling

        if response_style in ["banglish", "hinglish"]:

            styled = apply_response_style(
                response_text,
                response_style
            )

            logger.info(
                f"[{self.name}] "
                f"Applied direct style conversion: {response_style}"
            )

            return styled

        # Normal translation flow

        translated = translate_to_user_language(
            response_text,
            target_lang
        )

        logger.info(
            f"[{self.name}] "
            f"Translated to: {target_lang}"
        )

        return translated