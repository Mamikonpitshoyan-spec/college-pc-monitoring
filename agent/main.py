"""Entry point for the Windows monitoring agent (local or server reporting)."""

import argparse
import json
import logging
from time import sleep

from collector.metrics import MetricsCollector
from config.settings import forget_pairing_code, settings
from network.client import AgentApiClient, TokenStore, default_agent_id
from network.service import AgentReporter
from services.logging_config import configure_logging, configure_utf8_output

logger = logging.getLogger(__name__)


def parse_arguments() -> argparse.Namespace:
    """Parse agent launch options for either operating mode."""
    parser = argparse.ArgumentParser(
        description=(
            "Collect Windows system metrics and report them to the Monitoring "
            "Server, or print a local snapshot with --local."
        )
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Collect locally and print JSON without contacting the server.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=settings.local_sample_interval_seconds,
        help="Local baseline delay in seconds (default: %(default)s).",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single cycle: one local snapshot or one server report.",
    )
    parser.add_argument(
        "--agent-id",
        default=settings.agent_id,
        help="Override the agent id derived from the hostname.",
    )
    return parser.parse_args()


def run_local(interval: float, once: bool) -> int:
    """Collect and print a local JSON snapshot; no server communication."""
    collector = MetricsCollector()
    collector.establish_rate_baseline()
    if not once:
        sleep(interval)
    snapshot = collector.collect()
    print(json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2))
    return 0


def run_server(agent_id: str, once: bool) -> int:
    """Register with the Monitoring Server and report metrics on a schedule."""
    from localstatus import StatusWriter, start_fast_sampler

    client = AgentApiClient(
        server_url=settings.server_url,
        registration_key=settings.registration_key,
        request_timeout_seconds=settings.request_timeout_seconds,
        token_store=TokenStore(settings.token_path),
    )
    status_writer = StatusWriter(settings.status_path)
    start_fast_sampler(status_writer)
    reporter = AgentReporter(
        agent_id=agent_id,
        client=client,
        collector=MetricsCollector(),
        report_interval_seconds=settings.report_interval_seconds,
        on_status=lambda status: status_writer.update(status),
        pair_code=settings.pairing_code,
        on_paired=forget_pairing_code,
    )
    try:
        reporter.run_forever(once=once)
    finally:
        client.close()
    return 0


def main() -> int:
    settings.validate()
    configure_utf8_output()
    configure_logging(settings.log_level)
    arguments = parse_arguments()
    if arguments.interval <= 0:
        raise ValueError("--interval must be greater than zero")
    if arguments.local:
        return run_local(arguments.interval, arguments.once)
    if not settings.registration_key:
        raise SystemExit(
            "MONITORING_REGISTRATION_KEY is not set. Ask the administrator for "
            "the registration key, or use --local for offline collection."
        )
    agent_id = arguments.agent_id or default_agent_id()
    return run_server(agent_id, arguments.once)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        logger.info("Monitoring agent stopped by user.")
    except Exception:
        logger.exception("Monitoring agent stopped because of an unexpected error")
        raise
