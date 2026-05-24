from datetime import datetime, timedelta
import random


otp_memory = {}


def generate_otp(phone_number: str):

    otp = str(random.randint(100000, 999999))

    otp_memory[phone_number] = {
        "otp": otp,
        "expires": datetime.utcnow() + timedelta(minutes=5)
    }

    return otp


def verify_otp(phone_number: str, otp: str):

    data = otp_memory.get(phone_number)

    if not data:
        return False

    if datetime.utcnow() > data["expires"]:
        return False

    return data["otp"] == otp