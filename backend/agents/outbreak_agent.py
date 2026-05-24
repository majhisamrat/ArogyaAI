from tools.outbreak_tool import (
    update_outbreak_log,
    check_outbreak_in_area,
    get_outbreak_alert_message,
    get_all_outbreak_summary,
)
from config.logger import logger

class OutbreakAgent:
    """
    Responsible for:
    - Logging new disease cases per pincode
    - Detecting outbreak patterns (5+ cases in 7 days)
    - Generating outbreak alerts for users
    - Providing outbreak summary for admin dashboard
    """

    def __init__(self):
        self.name = "OutbreakAgent"

    def log_and_check(
        self,
        pincode: str,
        disease: str,
        location_area: str = "",
        user_lang: str = "en",
    ) -> dict:
        """
        Log a new disease case and check if it triggers an outbreak.

        Args:
            pincode:       User's pincode
            disease:       Detected disease from symptom agent
            location_area: Area name from pincode
            user_lang:     User language for alert message

        Returns:
            dict with is_outbreak, case_count, alert_message
        """
        logger.info(f"[{self.name}] Logging case: {disease} in {pincode}")

        # Update outbreak log in DB
        log_result = update_outbreak_log(pincode, disease, location_area)

        alert_message = ""
        if log_result["is_outbreak"]:
            logger.info(f"[{self.name}] ⚠️ OUTBREAK DETECTED: {disease} in {pincode} ({log_result['case_count']} cases)")
            outbreaks = [
                {
                    "disease":    disease,
                    "case_count": log_result["case_count"],
                    "pincode":    pincode,
                    "area":       location_area,
                }
            ]
            alert_message = get_outbreak_alert_message(outbreaks, user_lang)

        return {
            "is_outbreak":   log_result["is_outbreak"],
            "case_count":    log_result["case_count"],
            "disease":       disease,
            "pincode":       pincode,
            "alert_message": alert_message,
        }

    def check_area_outbreaks(self, pincode: str, user_lang: str = "en") -> str:
        """
        Check and return any active outbreak alerts for user's area.
        Called when user first starts a session.
        Returns alert message or empty string if no outbreaks.
        """
        outbreaks = check_outbreak_in_area(pincode)
        if not outbreaks:
            return ""
        logger.info(f"[{self.name}] Found {len(outbreaks)} active outbreaks in {pincode}")
        return get_outbreak_alert_message(outbreaks, user_lang)

    def get_dashboard_summary(self) -> list:
        """
        Get all active outbreaks for admin dashboard in Streamlit.
        """
        return get_all_outbreak_summary()