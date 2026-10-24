# Monitoring Agent — Stage 4 (server reporting)

The agent collects real Windows metrics and reports them to the Monitoring Server over HTTP. The old local-only console mode is still available with `--local`.

## Modes

- **Server mode (default):** register → save token → heartbeat + metrics every `MONITORING_REPORT_INTERVAL_SECONDS`, with automatic reconnection and exponential backoff when the server is unreachable.
- **Local mode (`--local`):** collect and print one JSON snapshot without any network communication.

## First run

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # then set MONITORING_REGISTRATION_KEY and MONITORING_SERVER_URL
python main.py
```

On the first successful registration the server issues an API token once; the agent saves it to `.agent_token.json` (git-ignored). Keep that file: if it is lost, the device must be deleted on the server side so the agent can re-register.

## Configuration (environment / `.env`)

| Variable | Default | Purpose |
|---|---|---|
| `MONITORING_SERVER_URL` | `http://127.0.0.1:8000` | Monitoring Server base URL (use the admin PC LAN IP, e.g. `http://192.168.1.50:8000`) |
| `MONITORING_REGISTRATION_KEY` | — | Required for first registration; matches the server's `AGENT_REGISTRATION_KEY` |
| `MONITORING_AGENT_ID` | hostname-derived | Optional stable agent id override |
| `MONITORING_TOKEN_PATH` | `.agent_token.json` | Where the issued API token is stored |
| `MONITORING_REPORT_INTERVAL_SECONDS` | `10` | Seconds between heartbeat+metrics cycles |
| `MONITORING_REQUEST_TIMEOUT_SECONDS` | `5` | Per-request HTTP timeout |
| `MONITORING_LOG_LEVEL` | `INFO` | Logging verbosity |
| `MONITORING_SAMPLE_INTERVAL_SECONDS` | `1` | Baseline delay for `--local` mode |

## CLI options

- `python main.py` — connect to the server and report continuously.
- `python main.py --once` — one registration/report cycle, then exit.
- `python main.py --local` — print a local JSON snapshot (no network).
- `python main.py --local --interval 2.5` — local snapshot with a custom rate baseline.
- `python main.py --agent-id PC-02` — override the derived agent id.

## Collected data

- CPU: Windows model/manufacturer, core counts, current psutil utilisation, and frequency when psutil exposes it.
- RAM: total, used, available, and percentage.
- Disk: mounted partitions and aggregate I/O cumulative bytes and delta/time throughput.
- Network: each interface's addresses, MAC, byte counters, RX/TX speeds, packets, errors, and dropped packets.
- System: host and OS identity, architecture, uptime, Windows manufacturer and model.
- BIOS/UEFI: `Win32_BIOS` and `Win32_BaseBoard` data via `Get-CimInstance`; no BIOS file is read.
- GPU: architecture and native adapter identity data from `Win32_VideoController`. Utilisation and GPU temperature are explicitly `null` until a later supported collector exists.
- Temperature: a separate sensor layer based on `psutil.sensors_temperatures`. On Windows this often is unavailable; `sensors` is then `null`.

## Metrics contract

Every snapshot has `schema_version: "1.0"`, `collected_at`, and the eight top-level sections: `cpu`, `ram`, `disk`, `network`, `gpu`, `temperature`, `system`, and `bios`. The server validates this envelope (`MetricsSubmission`), stores the full JSON payload, and preserves unknown future sections.

Unknown or unsupported values are JSON `null`; the agent never substitutes placeholder measurements.

## Reconnection behavior

Connection failures never crash the agent. The loop logs `Connection to the monitoring server failed … Reconnecting in N s.` and retries with exponential backoff (2 s → 4 s → … → 60 s cap). If the server rejects the stored token (401), the agent clears it and re-registers automatically.

## Tests

```powershell
python -m pytest tests -v
```

`pywin32` and `PyInstaller` remain declared for later Windows Service and packaging stages, but are not invoked yet.
