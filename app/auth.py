import os
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
serializer = URLSafeTimedSerializer(SECRET_KEY)

def hash_password(p: str) -> str:
    return pwd_context.hash(p)

def verify_password(p: str, h: str) -> bool:
    return pwd_context.verify(p, h)

def create_session(user_id: int) -> str:
    return serializer.dumps({"uid": user_id})

def read_session(token: str, max_age: int = 60 * 60 * 24 * 7):
    try:
        data = serializer.loads(token, max_age=max_age)
        return data["uid"]
    except (BadSignature, SignatureExpired):
        return None