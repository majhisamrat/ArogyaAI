from jose import jwt
from datetime import datetime, timedelta


SECRET_KEY = "health_assistant_secret"

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_HOURS = 24


def create_access_token(data: dict):

    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(
        hours=ACCESS_TOKEN_EXPIRE_HOURS
    )

    to_encode.update({
        "exp": expire
    })

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return encoded_jwt