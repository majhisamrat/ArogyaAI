from tools.education_tool import (
    get_disease_education,
    get_health_tip_of_day,
    detect_education_intent,
)
from config.logger import logger



class EducationAgent:
    """
    Responsible for:
    - Teaching users about diseases and health topics
    - Providing daily health tips
    - Detecting if user wants information vs reporting symptoms
    """

    def __init__(self):
        self.name = "EducationAgent"

    def is_education_request(self, user_input_english: str) -> bool:
        """
        Detect if the user is asking for education/information
        rather than reporting symptoms.
        """
        return detect_education_intent(user_input_english)

    def educate(self, topic: str, user_name: str) -> str:
        """
        Provide educational content about a health topic or disease.

        Args:
            topic:     Disease or health topic in English
            user_name: For personalized greeting

        Returns:
            Formatted educational message
        """
        logger.info(f"[{self.name}] Educating about: {topic}")
        content = get_disease_education(topic)

        return (
            f"📚 Hello {user_name}! Here is what you should know about *{topic}*:\n\n"
            f"{content}\n\n"
            f"💡 _Always consult a doctor if you experience any of these symptoms._"
        )

    def daily_tip(self, user_name: str) -> str:
        """
        Generate a daily health tip for the user.
        """
        print(f"[{self.name}] Generating daily health tip")
        tip = get_health_tip_of_day()
        return f"🌟 *Daily Health Tip for {user_name}:*\n\n{tip}"