"""Auth endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from clawforce.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from clawforce.core.audit import log_auth_event
from clawforce.core.database import get_database
from clawforce.core.store.users import UserStore
from clawforce.core.stream_token import create_stream_token
from clawforce.middleware.rate_limit import limiter


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class StreamTokenResponse(BaseModel):
    token: str


class UserResponse(BaseModel):
    id: str
    username: str
    role: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, form: OAuth2PasswordRequestForm = Depends()):
    ip = request.client.host if request.client else ""
    store = UserStore(get_database())
    user = store.get_user_by_username(form.username)
    if not user:
        log_auth_event("login", None, ip, False, "invalid credentials")
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not verify_password(form.password, user.password_hash):
        log_auth_event("login", None, ip, False, "invalid credentials")
        raise HTTPException(status_code=401, detail="Invalid username or password")
    log_auth_event("login", user.id, ip, True)
    token = create_access_token(sub=user.id, role=user.role)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(current: dict = Depends(get_current_user)):
    return UserResponse(**current)


@router.post("/stream-token", response_model=StreamTokenResponse)
def issue_stream_token(current: dict = Depends(get_current_user)):
    """Issue a short-lived (5-minute) token for SSE / WebSocket connections.

    Browser EventSource and WebSocket APIs cannot send custom headers, so the
    JWT cannot be passed as an Authorization header for streaming endpoints.
    Use this endpoint to obtain a short-lived token to pass as ?token=<value>
    instead of exposing the long-lived JWT in URLs.
    """
    token = create_stream_token({"sub": current["id"], "role": current.get("role", "admin")})
    return StreamTokenResponse(token=token)


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    current: dict = Depends(get_current_user),
):
    """Change password for the currently logged-in user."""
    user_id = current.get("id")
    store = UserStore(get_database())
    user = store.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    new_hash = hash_password(body.new_password)
    store.update_user(user_id, password_hash=new_hash)
    log_auth_event("password_change", user_id, "", True)
    return {"message": "Password changed successfully"}
