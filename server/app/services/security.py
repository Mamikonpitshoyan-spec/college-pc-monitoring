"""Registration and bearer-token checks without logging secrets."""

from __future__ import annotations

import hashlib
import hmac
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import get_db
from app.models.device import Device

bearer_scheme = HTTPBearer(auto_error=False)


def require_registration_key(registration_key: str | None) -> None:
    """Check the temporary registration credential configured outside source code."""
    configured_key = settings.agent_registration_key
    if not configured_key or not settings.agent_token_pepper:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent registration is not configured on this server.",
        )
    if registration_key is None or not hmac.compare_digest(registration_key, configured_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid registration key.")


def generate_api_token() -> str:
    """Generate an opaque token returned only once at initial registration."""
    return secrets.token_urlsafe(32)


def hash_api_token(token: str) -> str:
    """Hash a token with the environment-supplied server pepper."""
    pepper = settings.agent_token_pepper
    if not pepper:
        raise RuntimeError("AGENT_TOKEN_PEPPER is not configured")
    return hashlib.sha256(f"{pepper}:{token}".encode("utf-8")).hexdigest()


def get_authenticated_device(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    database: Session = Depends(get_db),
) -> Device:
    """Resolve a bearer token to its device without exposing the token in logs."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required.")
    if not settings.agent_token_pepper:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Agent authentication is not configured.")

    token_hash = hash_api_token(credentials.credentials)
    device = database.scalar(select(Device).where(Device.api_token_hash == token_hash))
    if device is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid agent token.")
    return device
