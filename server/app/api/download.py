"""Agent installer download: the server hands out a ready-to-run package.

The zip contains only MonitoringAgentApp.exe; the server address travels
inside the pairing code (variant B), instructions live on this page.
"""

from __future__ import annotations

import socket
from pathlib import Path

import sys

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.setting import Setting

router = APIRouter(tags=["download"])


def _agent_dist_dir() -> Path | None:
    """Locate the built user app: bundled inside this exe, else on disk.

    Bundled-first so the admin exe works in any folder (college PC, flash
    drive); the walk-up fallback covers running from the project tree.
    """
    bundled = Path(getattr(sys, "_MEIPASS", "")) / "MonitoringAgentApp.exe"
    if bundled.exists():
        return bundled.parent
    exe_dir = Path(sys.executable).resolve().parent
    for level in [exe_dir, *exe_dir.parents]:
        candidate = level / "agent" / "dist"
        if (candidate / "MonitoringAgentApp.exe").exists():
            return candidate
    return None

_HTML = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Установка агента · Мониторинг LAN</title>
<style>
  :root {
    --bg: #0A1520; --panel: #112233; --border: #1E3750;
    --text: #E3ECF5; --muted: #7F9AB5;
    --accent: #FF7F6B; --accent-soft: rgba(255, 127, 107,.10); --accent-line: rgba(255, 127, 107,.25);
    --mono: ui-monospace, "Cascadia Mono", Consolas, monospace;
  }
  * { box-sizing: border-box; margin: 0; }
  body {
    font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
    background: var(--bg); color: var(--text); font-size: 14px;
    min-height: 100vh; display: grid; place-items: center; padding: 20px;
  }
  .card {
    width: min(480px, 94vw); background: var(--panel); border: 1px solid var(--border);
    border-radius: 12px; padding: 26px;
  }
  h1 { font-size: 17px; font-weight: 650; }
  h1 span { color: var(--accent); }
  .sub { color: var(--muted); font-size: 12.5px; margin: 6px 0 16px; }
  ol { margin: 0 0 16px 18px; color: var(--muted); font-size: 13px; line-height: 1.8; }
  ol b { color: var(--text); }
  a.dl {
    display: block; text-align: center; padding: 13px; border-radius: 10px; text-decoration: none;
    color: #0A1520; background: var(--accent); font-weight: 650; font-size: 15px;
  }
  a.dl:hover { filter: brightness(1.1); }
  .warn {
    margin: 0 0 16px; padding: 10px 12px; border-radius: 8px; font-size: 12.5px; line-height: 1.5;
    color: var(--text); background: var(--accent-soft); border: 1px solid var(--accent-line);
  }
  .addr { margin-top: 12px; color: var(--muted); font-size: 12px; text-align: center; }
  .addr code { color: var(--accent); font-family: var(--mono); }
  .lang { display: flex; gap: 4px; justify-content: flex-end; margin-top: 16px; }
  .lang button {
    padding: 3px 8px; font-size: 10.5px; font-weight: 700; color: var(--muted);
    background: transparent; border: 1px solid var(--border); border-radius: 6px; cursor: pointer; font-family: inherit;
  }
  .lang button.active { color: var(--accent); border-color: var(--accent-line); }
</style>
<link rel="stylesheet" href="/static/themes.css?v=1">
</head>
<body>
  <div class="card">
    <h1>Мониторинг <span>LAN</span> — установка агента</h1>
    <div class="sub" id="sub">Установите агента на этот компьютер, чтобы он появился в системе мониторинга.</div>
    <ol>
      <li id="li1"><b>Скачайте</b> программу (один файл MonitoringAgentApp.exe)</li>
      <li id="li2">Запустите <b>MonitoringAgentApp.exe</b> и ответьте «Да» на запрос Windows</li>
      <li id="li3">Введите <b>код подключения</b>, который дал администратор</li>
      <li id="li4">Администратор нажмёт «Принять» — готово</li>
    </ol>
    <div class="warn" id="warn">Если Windows покажет «Система Windows защитила ваш компьютер» — нажмите «Подробнее» → «Выполнить в любом случае».</div>
    <a class="dl" href="/download/agent-package" id="dl">⬇ Скачать программу (.exe)</a>
    <div class="lang">
      <button data-lang="ru" class="active">RU</button>
      <button data-lang="am">ՀԱՅ</button>
      <button data-lang="en">EN</button>
    </div>
  </div>
<script>
const LANGS = {
  ru: {sub: "Установите агента на этот компьютер, чтобы он появился в системе мониторинга.",
       l1: "программу (один файл MonitoringAgentApp.exe). Если браузер спросит — нажмите «Сохранить»", l2: "Запустите MonitoringAgentApp.exe и ответьте «Да» на запрос Windows",
       l3: "код подключения, который дал администратор", l4: "Администратор нажмёт «Принять» — готово",
       warn: "Если Windows покажет «Система Windows защитила ваш компьютер» — нажмите «Подробнее» → «Выполнить в любом случае».",
       dl: "⬇ Скачать программу (.exe)"},
  am: {sub: "Տեղադրեք ագենտը այս համակարգչում, որ այն հայտնվի մոնիտորինգի համակարգում։",
       l1: "ծրագիրը (մեկ ֆայլ՝ MonitoringAgentApp.exe)։ Եթե զննարկիչը հարցնի — սեղմեք «Պահպանել»", l2: "Գործարկեք MonitoringAgentApp.exe և պատասխանեք «Այո» Windows-ի հարցմանը",
       l3: "միացման կոդը, որը տվել է ադմինիստրատորը", l4: "Ադմինիստրատորը սեղմում է «Ընդունել» — պատրաստ է",
       warn: "Եթե Windows-ը ցույց տա «Windows-ը պաշտպանեց ձեր համակարգիչը» — սեղմեք «Մանրամասն» → «Գործարկել ամեն դեպքում»։",
       dl: "⬇ Ներբեռնել ծրագիրը (.exe)"},
  en: {sub: "Install the agent on this computer so it appears in the monitoring system.",
       l1: "the program (one file, MonitoringAgentApp.exe). If the browser asks, click “Keep”", l2: "Run MonitoringAgentApp.exe and answer Yes to the Windows prompt",
       l3: "connection code given by the administrator", l4: "The administrator clicks Approve — done",
       warn: "If Windows shows “Windows protected your PC” — click “More info” → “Run anyway”.",
       dl: "⬇ Download the program (.exe)"},
};
let lang = document.documentElement.dataset.lang || "ru";
try { const saved = localStorage.getItem("monitoring_lang"); if (LANGS[saved]) lang = saved; } catch (e) {}
function apply() {
  const t = LANGS[lang];
  document.getElementById("sub").textContent = t.sub;
  document.getElementById("li1").innerHTML = "<b>" + (lang === "en" ? "Download" : lang === "am" ? "Ներբեռնեք" : "Скачайте") + "</b> " + t.l1;
  document.getElementById("li2").textContent = t.l2;
  document.getElementById("warn").textContent = t.warn;
  document.getElementById("li3").innerHTML = (lang === "en" ? "Enter the " : lang === "am" ? "Մուտքագրեք " : "Введите ") + "<b>" + t.l3 + "</b>";
  document.getElementById("li4").textContent = t.l4;
  document.getElementById("dl").textContent = t.dl;
  document.querySelectorAll(".lang button").forEach(function (b) {
    b.classList.toggle("active", b.dataset.lang === lang);
  });
}
document.addEventListener("click", function (event) {
  const b = event.target.closest(".lang button");
  if (!b) return;
  lang = b.dataset.lang;
  try { localStorage.setItem("monitoring_lang", lang); } catch (e) {}
  apply();
});
apply();
</script>
</body>
</html>"""





@router.get("/download", include_in_schema=False)
def download_page() -> HTMLResponse:
    from app.api.monitoring import current_ui_prefs

    prefs = current_ui_prefs()
    return HTMLResponse(_HTML.replace(
        '<html lang="ru">', f'<html lang="ru" data-theme="{prefs["theme"]}" data-lang="{prefs["lang"]}">', 1))


@router.get("/download/agent-package", include_in_schema=False)
def agent_package() -> Response:
    """Hand out the user app as one exe — nothing to unpack, nothing extra next to it."""
    dist_dir = _agent_dist_dir()
    if dist_dir is None:
        return Response(
            "Agent installer files are not available on this server.",
            status_code=503,
            media_type="text/plain",
        )
    # Вариант B: адрес сервера зашит в код подключения — отдаём только exe.
    return FileResponse(
        dist_dir / "MonitoringAgentApp.exe",
        media_type="application/vnd.microsoft.portable-executable",
        filename="MonitoringAgentApp.exe",
    )


def _usable_ip(ip: str | None) -> bool:
    return bool(ip) and not ip.startswith(("127.", "169.254.", "0."))


def _lan_ip() -> str | None:
    """Best-effort LAN IP (fallback when no address is set). Never loopback."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        ip = probe.getsockname()[0]
        if _usable_ip(ip):
            return ip
    except OSError:
        pass
    finally:
        probe.close()
    try:
        candidates = socket.gethostbyname_ex(socket.gethostname())[2]
    except OSError:
        return None
    private = [ip for ip in candidates if _usable_ip(ip) and ip.startswith(("192.168.", "10.", "172."))]
    return (private or [ip for ip in candidates if _usable_ip(ip)] or [None])[0]


# Порт, на котором реально запущен сервер (admin_app подставляет найденный свободный).
ACTUAL_PORT: int | None = None
SERVER_ADDRESS_KEY = "server_address"


def server_port() -> int:
    from app.core.config import settings

    return ACTUAL_PORT or settings.port


def get_saved_address(database: Session) -> str | None:
    row = database.scalar(select(Setting).where(Setting.key == SERVER_ADDRESS_KEY))
    value = (row.value or {}).get("address") if row else None
    return value or None


def save_address(database: Session, address: str | None) -> None:
    row = database.scalar(select(Setting).where(Setting.key == SERVER_ADDRESS_KEY))
    if row is None:
        database.add(Setting(key=SERVER_ADDRESS_KEY, value={"address": address}))
    else:
        row.value = {"address": address}
    database.commit()


def server_address(database: Session) -> dict:
    """The one address users get: saved by the admin, else auto-detected."""
    saved = get_saved_address(database)
    host = saved or _lan_ip()
    port = server_port()
    return {
        "address": saved,
        "detected": _lan_ip(),
        "port": port,
        "url": f"http://{host}:{port}" if host else None,
    }
