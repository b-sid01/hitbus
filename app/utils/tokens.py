import secrets
from datetime import datetime, timedelta

def generate_verification_token() -> str:
    return secrets.token_urlsafe(32)

def token_expiry(hours: int = 24) -> datetime:
    return datetime.utcnow() + timedelta(hours=hours)
