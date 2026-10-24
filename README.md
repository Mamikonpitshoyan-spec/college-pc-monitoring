# Centralized Computer Monitoring

Stage 4 establishes real LAN reporting: the Monitoring Agent registers with the Monitoring Server, receives an API token, and continuously reports heartbeat and metrics with automatic reconnection. Stages 1–3 (architecture, local collection, server persistence) remain unchanged.

## Layout

- `server/` — FastAPI REST backend, SQLite persistence, token-based Agent API, and future alert/event/settings tables.
- `agent/` — Windows-agent collectors for real local CPU, RAM, disk, network, system, BIOS/UEFI, available GPU, and optional temperature data.
- `installer/` — reserved for future server and agent installers; no installer is implemented.

## Run the server

PowerShell:

```powershell
cd "C:\Users\USER\Desktop\Arajin Ashxatanq Excel\server"
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload
```

The health endpoint is available at `http://127.0.0.1:8000/health`; FastAPI documentation is at `http://127.0.0.1:8000/docs`. The server binds `HOST`/`PORT` from `server/.env` when started with `python -m app.main` (set `HOST=0.0.0.0` for LAN access). Before Agent registration, set distinct secure `AGENT_REGISTRATION_KEY` and `AGENT_TOKEN_PEPPER` values in `server/.env`.

## Run the agent

In a separate PowerShell window:

```powershell
cd "C:\Users\USER\Desktop\Arajin Ashxatanq Excel\agent"
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python main.py
```

The agent registers with the server (registration key required), stores its API token in `.agent_token.json`, then reports heartbeat and metrics every `MONITORING_REPORT_INTERVAL_SECONDS`. Use `python main.py --local` for a local JSON snapshot without network communication.
