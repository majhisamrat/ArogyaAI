from tools.health_record_tool import (
    store_health_record,
    fetch_health_history
)

from config.logger import logger


class HealthDataAgent:
    """
    Responsible for:
    - Saving structured health consultation records
    - Retrieving user health history
    - Providing medical memory context
    """

    def __init__(self):

        self.name = "HealthDataAgent"

    def save_consultation(
        self,
        phone_number: str,
        symptoms: str,
        possible_disease: str,
        advice: str,
        severity: str,
        confidence: float = 0.0,
        emergency: bool = False,
        language_used: str = "en",
    ) -> bool:
        """
        Save structured health consultation.

        Stores ONLY meaningful medical predictions.
        """

        logger.info(
            f"[{self.name}] "
            f"Saving record for {phone_number}: "
            f"{possible_disease} | "
            f"Confidence={confidence}"
        )

        result = store_health_record(
            phone_number=phone_number,
            symptoms=symptoms,
            possible_disease=possible_disease,
            advice=advice,
            severity=severity,
            confidence=confidence,
            emergency=emergency,
            language_used=language_used,
        )

        return result["success"]

    def get_history(
        self,
        phone_number: str,
        limit: int = 5
    ) -> dict:
        """
        Retrieve structured health history.
        """

        logger.info(
            f"[{self.name}] "
            f"Fetching history for {phone_number}"
        )

        return fetch_health_history(
            phone_number,
            limit=limit
        )

    def get_history_for_context(
        self,
        phone_number: str
    ) -> list:
        """
        Get raw structured records for AI reasoning context.
        """

        data = fetch_health_history(
            phone_number,
            limit=3
        )

        return data.get("records", [])