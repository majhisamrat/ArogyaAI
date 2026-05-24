from datetime import datetime, timedelta
from database.models import HealthRecord, OutbreakLog, User
from database.db_handler import get_db_session
from config.settings import (
    OUTBREAK_THRESHOLD, OUTBREAK_WINDOW_DAYS,
    get_llm_response, GROQ_MAIN_MODEL, TEMP_OUTBREAK
)
from config.logger import logger


def update_outbreak_log(pincode: str, disease: str, location_area: str = "") -> dict:
    """
    Update outbreak log when a new case is reported.
    Returns outbreak status and alert info.
    """
    db = get_db_session()
    try:
        window_start = datetime.utcnow() - timedelta(days=OUTBREAK_WINDOW_DAYS)

        # Check if outbreak log exists for this pincode + disease recently
        log = db.query(OutbreakLog).filter(
            OutbreakLog.pincode  == pincode,
            OutbreakLog.disease  == disease,
            OutbreakLog.reported_at >= window_start,
        ).first()

        if log:
            log.case_count  += 1
            log.last_updated = datetime.utcnow()
        else:
            log = OutbreakLog(
                pincode       = pincode,
                location_area = location_area,
                disease       = disease,
                case_count    = 1,
            )
            db.add(log)

        db.commit()

        is_outbreak = log.case_count >= OUTBREAK_THRESHOLD
        return {
            "pincode":     pincode,
            "disease":     disease,
            "case_count":  log.case_count,
            "is_outbreak": is_outbreak,
            "threshold":   OUTBREAK_THRESHOLD,
        }
    finally:
        db.close()


def check_outbreak_in_area(pincode: str) -> list:
    """
    Check if there are any active outbreaks in a given pincode.
    Returns list of active outbreak alerts.
    """
    db = get_db_session()
    try:
        window_start = datetime.utcnow() - timedelta(days=OUTBREAK_WINDOW_DAYS)
        logs = db.query(OutbreakLog).filter(
            OutbreakLog.pincode      == pincode,
            OutbreakLog.case_count   >= OUTBREAK_THRESHOLD,
            OutbreakLog.reported_at  >= window_start,
        ).all()

        return [
            {
                "disease":    l.disease,
                "case_count": l.case_count,
                "pincode":    l.pincode,
                "area":       l.location_area,
            }
            for l in logs
        ]
    finally:
        db.close()


def get_outbreak_alert_message(outbreaks: list, user_lang: str = "en") -> str:
    """
    Generate a simple outbreak alert message for the user.
    """
    if not outbreaks:
        return ""

    outbreak_info = "\n".join(
        f"- {o['disease']}: {o['case_count']} cases in your area"
        for o in outbreaks
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are a public health alert system. Write a short, calm, "
                "and clear outbreak alert for rural users. "
                "Include: what disease, how to protect yourself, when to see doctor. "
                "Keep it under 100 words. Use simple language."
            ),
        },
        {
            "role": "user",
            "content": f"Write an alert for these outbreaks in the area:\n{outbreak_info}",
        },
    ]
    return get_llm_response(
        messages,
        model=GROQ_MAIN_MODEL,
        temperature=TEMP_OUTBREAK,
        max_tokens=300,
    )


def get_all_outbreak_summary() -> list:
    """
    Get summary of all active outbreaks across all pincodes.
    Useful for admin dashboard.
    """
    db = get_db_session()
    try:
        window_start = datetime.utcnow() - timedelta(days=OUTBREAK_WINDOW_DAYS)
        logs = db.query(OutbreakLog).filter(
            OutbreakLog.case_count  >= OUTBREAK_THRESHOLD,
            OutbreakLog.reported_at >= window_start,
        ).order_by(OutbreakLog.case_count.desc()).all()

        return [
            {
                "pincode":    l.pincode,
                "area":       l.location_area,
                "disease":    l.disease,
                "case_count": l.case_count,
                "updated":    l.last_updated,
            }
            for l in logs
        ]
    finally:
        db.close()