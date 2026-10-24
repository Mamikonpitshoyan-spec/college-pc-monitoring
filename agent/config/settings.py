"""Configuration for local collection and Monitoring Server reporting."""

import sys
from dataclasses import dataclass
from os import getenv
from pathlib import Path
from sys import version_info

from dotenv import load_dotenv

# The agent directory: .env and the token live here regardless of the
# working directory (a Windows Service starts in System32). When frozen
# with PyInstaller, config lives next to the executable.
if getattr(sys, "frozen", False):
    AGENT_DIR = Path(sys.executable).resolve().parent
else:
    AGENT_DIR = Path(__file__).resolve().parents[1]

load_dotenv(AGENT_DIR / ".env")


def forget_pairing_code() -> None:
    """One code — one computer: drop the used code from .env after approval."""
    env_path = AGENT_DIR / ".env"
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return
    kept = [line for line in lines if not line.startswith("MONITORING_PAIRING_CODE=")]
    if kept != lines:
        env_path.write_text("\n".join(kept) + "\n", encoding="utf-8")


@dataclass(frozen=True)
class AgentSettings:
    server_url: str = getenv("MONITORING_SERVER_URL", "http://127.0.0.1:8000")
    registration_key: str | None = getenv("MONITORING_REGISTRATION_KEY")
    agent_id: str | None = getenv("MONITORING_AGENT_ID")
    pairing_code: str | None = getenv("MONITORING_PAIRING_CODE")
    token_path: str = getenv(
        "MONITORING_TOKEN_PATH", str(AGENT_DIR / ".agent_token.json")
    )
    status_path: str = getenv(
        "MONITORING_STATUS_PATH", str(AGENT_DIR / "status.json")
    )
    log_level: str = getenv("MONITORING_LOG_LEVEL", "INFO")
    local_sample_interval_seconds: float = float(
        getenv("MONITORING_SAMPLE_INTERVAL_SECONDS", "1.0")
    )
    report_interval_seconds: float = float(
        getenv("MONITORING_REPORT_INTERVAL_SECONDS", "10.0")
    )
    request_timeout_seconds: float = float(
        getenv("MONITORING_REQUEST_TIMEOUT_SECONDS", "5.0")
    )
    lhm_url: str = getenv(
        "MONITORING_LHM_URL", "http://127.0.0.1:8085/data.json"
    )

    def validate(self) -> None:
        if version_info < (3, 10):
            raise RuntimeError("Python 3.10 or newer is required.")
        if not self.server_url.startswith(("http://", "https://")):
            raise ValueError("MONITORING_SERVER_URL must begin with http:// or https://")
        if self.local_sample_interval_seconds <= 0:
            raise ValueError("MONITORING_SAMPLE_INTERVAL_SECONDS must be greater than zero")
        if self.report_interval_seconds <= 0:
            raise ValueError("MONITORING_REPORT_INTERVAL_SECONDS must be greater than zero")
        if self.request_timeout_seconds <= 0:
            raise ValueError("MONITORING_REQUEST_TIMEOUT_SECONDS must be greater than zero")


settings = AgentSettings()
