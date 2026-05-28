from datetime import datetime
from database.models import User, HealthRecord, OutbreakLog, RegistrationState
from database.db_handler import get_db_session
import requests


# Pincode → Location helper 
def get_location_from_pincode(pincode: str) -> str:
    """Fetch area name from Indian pincode using free API."""
    try:
        res = requests.get(f"https://api.postalpincode.in/pincode/{pincode}", timeout=5)
        data = res.json()
        if data[0]["Status"] == "Success":
            post_office = data[0]["PostOffice"][0]
            area = f"{post_office['Name']}, {post_office['District']}, {post_office['State']}"
            return area
    except Exception:
        pass
    return "Unknown Area"


#  USER REGISTRATION & LOOKUP

def is_registered(phone_number: str) -> bool:
    """Check if user exists in DB."""
    db = get_db_session()
    try:
        user = db.query(User).filter(User.phone_number == phone_number).first()
        return user is not None
    finally:
        db.close()


def get_user(phone_number: str) -> dict | None:
    """Get user profile as dict. Returns None if not found."""
    db = get_db_session()
    try:
        user = db.query(User).filter(User.phone_number == phone_number).first()
        if not user:
            return None
        return {
            "id":            user.id,
            "phone_number":  user.phone_number,
            "name":          user.name,
            "age":           user.age,
            "gender":        user.gender,
            "pincode":       user.pincode,
            "location_area": user.location_area,
            "language":      user.language,
            "registered_at": user.registered_at,
        }
    finally:
        db.close()


def register_user(
    phone_number: str,
    name: str,
    age: int,
    gender: str,
    pincode: str,
    language: str = "en",
) -> dict:
    """Register a new user. Returns user dict."""
    db = get_db_session()
    try:
        location_area = get_location_from_pincode(pincode)
        user = User(
            phone_number  = phone_number,
            name          = name,
            age           = int(age),
            gender        = gender,
            pincode       = pincode,
            location_area = location_area,
            language      = language,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return get_user(phone_number)
    finally:
        db.close()


def update_last_active(phone_number: str):
    """Update last_active timestamp for user."""
    db = get_db_session()
    try:
        user = db.query(User).filter(User.phone_number == phone_number).first()
        if user:
            user.last_active = datetime.utcnow()
            db.commit()
    finally:
        db.close()


#  HEALTH RECORDS

def save_health_record(
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
    Save ONLY meaningful health predictions.
    """

    # Ignore weak/unknown predictions
    if (
        not possible_disease
        or possible_disease.lower() == "unknown"
        or confidence < 0.5
    ):
        return False

    db = get_db_session()

    try:

        user = (
            db.query(User)
            .filter(User.phone_number == phone_number)
            .first()
        )

        if not user:
            return False

        record = HealthRecord(
            user_id=user.id,
            symptoms=symptoms,
            possible_disease=possible_disease,
            advice=advice,
            severity=severity,
            confidence=confidence,
            emergency=emergency,
            language_used=language_used,
        )

        db.add(record)

        db.commit()

        return True

    finally:

        db.close()


def get_user_health_history(phone_number: str, limit: int = 5) -> list:
    """Get last N health records for a user."""
    db = get_db_session()
    try:
        user = db.query(User).filter(User.phone_number == phone_number).first()
        if not user:
            return []
        records = (
            db.query(HealthRecord)
            .filter(HealthRecord.user_id == user.id)
            .order_by(HealthRecord.timestamp.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "possible_disease": r.possible_disease,
                "severity": r.severity,
                "confidence": r.confidence,
                "emergency": r.emergency,
                "timestamp": r.timestamp,
            }
            for r in records
        ]
    finally:
        db.close()


#  WHATSAPP REGISTRATION STATE

def get_registration_state(phone_number: str) -> dict | None:
    """Get current WhatsApp registration step."""
    db = get_db_session()
    try:
        state = db.query(RegistrationState).filter(
            RegistrationState.phone_number == phone_number
        ).first()
        if not state:
            return None
        return {
            "current_step": state.current_step,
            "temp_name":    state.temp_name,
            "temp_age":     state.temp_age,
            "temp_gender":  state.temp_gender,
            "temp_pincode": state.temp_pincode,
        }
    finally:
        db.close()


def update_registration_state(phone_number: str, step: str, **kwargs):
    """Update registration state for WhatsApp onboarding."""
    db = get_db_session()
    try:
        state = db.query(RegistrationState).filter(
            RegistrationState.phone_number == phone_number
        ).first()
        if not state:
            state = RegistrationState(phone_number=phone_number)
            db.add(state)
        state.current_step = step
        for key, val in kwargs.items():
            setattr(state, key, val)
        db.commit()
    finally:
        db.close()


def clear_registration_state(phone_number: str):
    """Delete registration state after completion."""
    db = get_db_session()
    try:
        db.query(RegistrationState).filter(
            RegistrationState.phone_number == phone_number
        ).delete()
        db.commit()
    finally:
        db.close()