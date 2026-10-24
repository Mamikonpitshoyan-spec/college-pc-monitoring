# Monitoring Server — Stage 6 (Dashboard)

FastAPI REST backend, SQLite persistence, token-based Agent API, and the HTML admin dashboard in the «Кибер-синий» theme.

## Run

```powershell
cd "C:\Users\USER\Desktop\Arajin Ashxatanq Excel\server"
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # set AGENT_REGISTRATION_KEY and AGENT_TOKEN_PEPPER; HOST=0.0.0.0 for LAN
python -m app.main
```

## Pages

- `/` — admin dashboard: device count / online / offline cards, live device table (CPU/RAM/disk bars, connection badges), auto-refresh every 5 s.
- `/devices/{id}` — full scanned-parameter view for one device: CPU, RAM, disk partitions and I/O speeds, network interfaces (RX/TX), system identity, BIOS/motherboard, GPU, temperature.
- `/docs` — developer API reference (Swagger); the admin does not need it.

## Agent API

```text
POST /api/agent/register    (X-Registration-Key header)
POST /api/agent/heartbeat   (Bearer token)
POST /api/agent/metrics     (Bearer token)

GET  /api/devices           (includes latest headline metrics per device)
GET  /api/devices/{id}
GET  /api/devices/{id}/metrics?limit=N
DELETE /api/devices/{id}
GET  /health
```

All timestamps are serialized with an explicit UTC offset; the database stores naive UTC.

## Tests

```powershell
python -m pytest tests -v
```
