"""Administrator authentication: password hash and cookie sessions in the DB.

First run: no password stored → the dashboard redirects to /setup where the
administrator creates one (PBKDF2 hash, salt stored alongside). After that
every dashboard page and admin API requires a valid session cookie; a
malicious LAN user opening the server address only sees the login page.
Agent endpoints are NOT affected — agents authenticate with their own tokens.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.setting import Setting
from app.services.agent_service import utc_now

SESSION_COOKIE = "admin_session"
_SESSION_KEY = "admin_session"
_PASSWORD_KEY = "admin_password"
_SESSION_TTL = timedelta(days=30)
_PBKDF2_ITERATIONS = 200_000


def _get_setting(database: Session, key: str) -> Setting | None:
    return database.scalar(select(Setting).where(Setting.key == key))


def _put_setting(database: Session, key: str, value: dict) -> None:
    row = _get_setting(database, key)
    if row is None:
        database.add(Setting(key=key, value=value))
    else:
        row.value = value
    database.commit()


def is_password_set(database: Session) -> bool:
    row = _get_setting(database, _PASSWORD_KEY)
    return bool(row and row.value and row.value.get("hash"))


def set_password(database: Session, password: str) -> None:
    """Store a PBKDF2 hash (salt included); the plaintext is never saved."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), _PBKDF2_ITERATIONS
    ).hex()
    _put_setting(database, _PASSWORD_KEY, {"salt": salt, "hash": digest})


def verify_password(database: Session, password: str) -> bool:
    row = _get_setting(database, _PASSWORD_KEY)
    if not row or not row.value:
        return False
    salt = row.value.get("salt", "")
    stored = row.value.get("hash", "")
    calculated = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), _PBKDF2_ITERATIONS
    ).hex()
    return secrets.compare_digest(calculated, stored)


def create_session(database: Session) -> str:
    """Issue a session token (stored in the DB, returned for the cookie)."""
    token = secrets.token_urlsafe(32)
    expires = (utc_now() + _SESSION_TTL).isoformat()
    _put_setting(database, _SESSION_KEY, {"token": token, "expires_at": expires})
    return token


def session_valid(database: Session, token: str | None) -> bool:
    if not token:
        return False
    row = _get_setting(database, _SESSION_KEY)
    if not row or not row.value:
        return False
    if row.value.get("token") != token:
        return False
    expires = row.value.get("expires_at")
    return bool(expires) and utc_now() <= utc_now().fromisoformat(expires)


def destroy_session(database: Session, token: str | None) -> None:
    _put_setting(database, _SESSION_KEY, {"token": None, "expires_at": None})
