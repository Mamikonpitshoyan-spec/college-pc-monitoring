"""HTTP-specific dependencies for server routes."""

from typing import Annotated

from fastapi import Header

from app.services.security import require_registration_key


def verify_registration_key(
    x_registration_key: Annotated[str | None, Header()] = None,
) -> None:
    """Read the temporary registration key from its dedicated header."""
    require_registration_key(x_registration_key)
