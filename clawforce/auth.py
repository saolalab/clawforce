"""JWT auth and password hashing."""

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from clawforce.core.database import get_database
from clawforce.core.store.agents import AgentStore
from clawforce.core.store.users import UserStore
from clawforce.deps import get_agent_store

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


def _get_jwt_secret() -> str:
    """Get JWT secret from env; require it in production."""
    env_secret = os.environ.get("ADMIN_JWT_SECRET")
    if env_secret:
        return env_secret
    if os.environ.get("CLAWFORCE_ENV", "development") == "production":
        raise RuntimeError("ADMIN_JWT_SECRET must be set in production")
    ephemeral = secrets.token_urlsafe(32)
    logger.warning(
        "ADMIN_JWT_SECRET not set — using ephemeral secret (dev mode). "
        "Set ADMIN_JWT_SECRET for persistence."
    )
    return ephemeral


SECRET_KEY = _get_jwt_secret()


def hash_password(password: str) -> str:
    """Hash password with bcrypt only (no SHA-256 preprocessing)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(sub: str, role: str = "admin") -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": sub, "role": role, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> dict:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    store = UserStore(get_database())
    user = store.get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return {"id": user.id, "username": user.username, "role": payload.get("role", "admin")}


def get_user_or_agent(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    agent_store: Annotated[AgentStore, Depends(get_agent_store)],
) -> dict:
    """Return current user (from JWT) or agent (from agent_token). Used for plan/artifact API calls from workers."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    payload = decode_token(token)
    if payload and "sub" in payload:
        store = UserStore(get_database())
        user = store.get_user_by_id(payload["sub"])
        if user:
            return {
                "type": "user",
                "id": user.id,
                "username": user.username,
                "role": payload.get("role", "admin"),
            }
    agent = agent_store.get_agent_by_token(token)
    if agent:
        return {"type": "agent", "agent_id": agent.id}
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
