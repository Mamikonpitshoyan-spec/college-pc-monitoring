"""Windows Service wrapper: the agent starts at boot with system rights.

Install (once, from an elevated console or install-agent-service.bat):
    .venv\\Scripts\\python.exe service.py install
    .venv\\Scripts\\python.exe service.py start
Remove:
    .venv\\Scripts\\python.exe service.py stop
    .venv\\Scripts\\python.exe service.py remove

A running service reports metrics exactly like the console agent, but runs
under LocalSystem, so ACPI temperature sensors are readable and no UAC
prompt is ever shown again after installation.
"""

from __future__ import annotations

import logging
import sys
import threading
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

SERVICE_NAME = "MonitoringAgent"
SERVICE_DISPLAY = "Monitoring Agent (LAN)"
SERVICE_DESCRIPTION = (
    "Collects CPU, RAM, disk, and network metrics and reports them to the "
    "centralized Monitoring Server over the LAN."
)

import win32event  # noqa: E402
import win32service  # noqa: E402
import win32serviceutil  # noqa: E402
import servicemanager  # noqa: E402

logger = logging.getLogger(__name__)


def _configure_service_logging() -> None:
    """Log to a file: a service has no console to write to."""
    from config.settings import settings
    from services.logging_config import configure_logging

    configure_logging(settings.log_level)
    handler = logging.FileHandler(AGENT_DIR / "agent_service.log", encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    logging.getLogger().addHandler(handler)


def _run_reporter(stop_check: threading.Event) -> None:
    """Run the normal reporting loop until the service is asked to stop."""
    from collector.metrics import MetricsCollector
    from config.settings import forget_pairing_code, settings
    from localstatus import StatusWriter, start_fast_sampler
    from network.client import AgentApiClient, TokenStore, default_agent_id
    from network.service import AgentReporter

    agent_id = settings.agent_id or default_agent_id()
    client = AgentApiClient(
        server_url=settings.server_url,
        registration_key=settings.registration_key,
        request_timeout_seconds=settings.request_timeout_seconds,
        token_store=TokenStore(settings.token_path),
    )
    status_writer = StatusWriter(settings.status_path)
    start_fast_sampler(status_writer, stop_event=stop_check)
    reporter = AgentReporter(
        agent_id=agent_id,
        client=client,
        collector=MetricsCollector(),
        report_interval_seconds=settings.report_interval_seconds,
        stop_check=stop_check.is_set,
        on_status=lambda status: status_writer.update(status),
        pair_code=settings.pairing_code,
        on_paired=forget_pairing_code,
    )
    try:
        reporter.run_forever()
    finally:
        client.close()


class MonitoringAgentService(win32serviceutil.ServiceFramework):
    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = SERVICE_DISPLAY
    _svc_description_ = SERVICE_DESCRIPTION

    def __init__(self, args) -> None:
        win32serviceutil.ServiceFramework.__init__(self, args)
        self._stop_event = win32event.CreateEvent(None, 0, 0, None)
        self._stop_requested = threading.Event()

    def SvcStop(self) -> None:
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self._stop_requested.set()
        win32event.SetEvent(self._stop_event)

    def SvcDoRun(self) -> None:
        _configure_service_logging()
        logger.info("Monitoring Agent service started.")
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )
        try:
            _run_reporter(self._stop_requested)
        except Exception:
            logger.exception("Service loop crashed.")
            servicemanager.LogErrorMsg("Monitoring Agent service crashed; see agent_service.log")
            self.ReportServiceStatus(win32service.SERVICE_STOPPED)
            raise
        logger.info("Monitoring Agent service stopped.")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Started by the Windows Service Control Manager.
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(MonitoringAgentService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(MonitoringAgentService)
