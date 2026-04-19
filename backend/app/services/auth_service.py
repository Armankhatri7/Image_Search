from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from app.config import settings
from app.services.supabase_client import supabase_service

# bcrypt truncates passwords beyond 72 bytes. bcrypt_sha256 pre-hashes first,
# which preserves full password entropy and avoids runtime length errors.
pwd_context = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto")


class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_token(user_id: str) -> str:
        expire = datetime.now(tz=timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
        payload = {"sub": user_id, "exp": expire}
        return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

    def create_user(self, username: str, password: str) -> dict:
        existing = supabase_service.select("users", filters={"username": username}, limit=1)
        if existing:
            raise ValueError("Username already exists")

        user = supabase_service.insert(
            "users",
            {"username": username.lower().strip(), "password_hash": self.hash_password(password)},
        )
        return user

    def authenticate(self, username: str, password: str) -> dict:
        users = supabase_service.select("users", filters={"username": username.lower().strip()}, limit=1)
        if not users:
            raise ValueError("Invalid credentials")

        user = users[0]
        if not self.verify_password(password, user["password_hash"]):
            raise ValueError("Invalid credentials")
        return user


auth_service = AuthService()
