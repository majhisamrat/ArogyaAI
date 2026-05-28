from database.login_manager import (
    save_health_record,
    get_user_health_history
)

from config.logger import logger


# STORE HEALTH RECORD

def store_health_record(
    phone_number: str,
    symptoms: str,
    possible_disease: str,
    advice: str,
    severity: str,
    confidence: float = 0.0,
    emergency: bool = False,
    language_used: str = "en",
) -> dict:
    """
    Save structured health consultation.

    Stores ONLY meaningful medical predictions.
    """

    logger.info(
        f"[HealthRecordTool] "
        f"Saving disease={possible_disease} "
        f"| confidence={confidence}"
    )

    success = save_health_record(
        phone_number=phone_number,
        symptoms=symptoms,
        possible_disease=possible_disease,
        advice=advice,
        severity=severity,
        confidence=confidence,
        emergency=emergency,
        language_used=language_used,
    )

    return {
        "success": success,
        "message": (
            "Health record saved."
            if success
            else "Failed to save record."
        ),
    }


# FETCH HEALTH HISTORY

def fetch_health_history(
    phone_number: str,
    limit: int = 5
) -> dict:
    """
    Retrieve structured user health history.
    """

    records = get_user_health_history(
        phone_number,
        limit=limit
    )

    if not records:

        return {
            "records": [],
            "formatted_summary": (
                "No health records found."
            ),
        }

    summary_lines = [
        "📋 *Your Recent Health History:*\n"
    ]

    for i, r in enumerate(records, 1):

        date_str = r["timestamp"].strftime(
            "%d %b %Y"
        )

        confidence_pct = int(
            r.get("confidence", 0) * 100
        )

        emergency_text = (
            " 🚨 Emergency"
            if r.get("emergency")
            else ""
        )

        summary_lines.append(
            f"{i}. *{r['possible_disease']}*\n"
            f"   Severity: {r['severity']}\n"
            f"   Confidence: {confidence_pct}%{emergency_text}\n"
            f"   Date: {date_str}"
        )

    return {
        "records": records,
        "formatted_summary": "\n\n".join(summary_lines),
    }