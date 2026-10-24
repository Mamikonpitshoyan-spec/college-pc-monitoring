"""Logging configuration shared by local and future service entry points."""

import logging
import sys


def configure_utf8_output() -> None:
    """Emit JSON and logs in UTF-8 instead of the active legacy code page."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            # Some embedded Python hosts expose no reconfigurable text stream.
            continue


def configure_logging(level_name: str) -> None:
    """Configure process logging without changing global handlers twice."""
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
