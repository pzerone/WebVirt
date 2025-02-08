import random
import string
import jwt
from jwt.exceptions import InvalidTokenError
from datetime import datetime, timedelta, timezone
from app.config import settings


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


def decode_token(token: str) -> dict | None:
    try:
        decoded_token = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return decoded_token
    except InvalidTokenError as e:
        print(f"JWT Token error {e}.")
        return None


def generate_password(length: int) -> str:
    if length < 4:
        raise ValueError(
            "Password length should be at least 4 to include all character types."
        )

    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits

    password = [
        random.choice(lowercase),
        random.choice(uppercase),
        random.choice(digits),
    ]
    all_characters = lowercase + uppercase + digits
    password += random.choices(all_characters, k=length - 4)
    random.shuffle(password)
    return "".join(password)
