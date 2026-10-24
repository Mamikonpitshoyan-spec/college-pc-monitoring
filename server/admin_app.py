"""MonitoringAdminApp — the whole admin application in one executable.

Embeds the FastAPI server (uvicorn in a background thread) and opens a
native window with the dashboard. Data (monitoring.db) and configuration
(.env) live in %LOCALAPPDATA%/MonitoringAdmin, so the folder with the exe
stays clean (one file). Closing the window hides it to the tray; the server keeps
running until "Выход" in the tray menu.
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
from pathlib import Path

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

# PyInstaller в --windowed режиме оставляет sys.stdout/stderr = None,
# а uvicorn при настройке логов вызывает sys.stdout.isatty() — подставляем
# безопасные потоки, иначе приложение падает на старте.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

# DB (sqlite:///./monitoring.db) и .env резолвятся от рабочей директории.
# Собранный exe держит их в %LOCALAPPDATA%\MonitoringAdmin — рядом с exe ничего не появляется.
if getattr(sys, "frozen", False):
    DATA_DIR = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "MonitoringAdmin"
else:
    DATA_DIR = BASE_DIR
DATA_DIR.mkdir(parents=True, exist_ok=True)
# Данные прежней версии лежали рядом с exe — переносим, чтобы агенты не потеряли связь.
for _name in (".env", "monitoring.db"):
    _old, _new = BASE_DIR / _name, DATA_DIR / _name
    if _old.exists() and not _new.exists() and _old != _new:
        try:
            _old.replace(_new)
        except OSError:
            pass
os.chdir(DATA_DIR)
sys.path.insert(0, str(BASE_DIR))

APP_NAME = "Monitoring Admin"


def resource_path(name: str) -> Path:
    """Locate bundled resources both in dev and inside PyInstaller bundles."""
    base = Path(getattr(sys, "_MEIPASS", BASE_DIR))
    candidate = base / name
    if candidate.exists():
        return candidate
    return BASE_DIR / name


def _ensure_secrets() -> None:
    """First run: create the registration key and token pepper in the data folder's .env."""
    import secrets

    env_path = DATA_DIR / ".env"
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        lines = []
    values = {line.split("=", 1)[0].strip(): line.split("=", 1)[1].strip()
              for line in lines if "=" in line and not line.lstrip().startswith("#")}
    missing = [key for key in ("AGENT_REGISTRATION_KEY", "AGENT_TOKEN_PEPPER") if not values.get(key)]
    if not missing:
        return
    lines = [line for line in lines if line.split("=", 1)[0].strip() not in missing]
    lines += [f"{key}={secrets.token_urlsafe(32)}" for key in missing]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _ensure_firewall_rule(port: int) -> None:
    """Allow inbound TCP on the server port (one UAC prompt, only if the rule is missing)."""
    import ctypes
    import subprocess

    name = f"Monitoring Admin TCP {port}"
    no_window = 0x08000000
    try:
        shown = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule", f"name={name}"],
            capture_output=True, creationflags=no_window, timeout=10,
        )
        if shown.returncode == 0:
            return
        rule = ["advfirewall", "firewall", "add", "rule", f"name={name}",
                "dir=in", "action=allow", "protocol=TCP", f"localport={port}"]
        if ctypes.windll.shell32.IsUserAnAdmin():
            subprocess.run(["netsh", *rule], capture_output=True, creationflags=no_window, timeout=10)
        else:
            args = subprocess.list2cmdline(rule)
            ctypes.windll.shell32.ShellExecuteW(None, "runas", "netsh", args, None, 0)
    except Exception:
        # Отказ от UAC или нет netsh — инструкция есть в «Настройках».
        pass


def _find_free_port(start: int, span: int = 20) -> int:
    port = start
    while port < start + span:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind(("0.0.0.0", port))
                return port
            except OSError:
                port += 1
    return start


def _start_server(port: int):
    import uvicorn

    from app.main import app

    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning")
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True, name="embedded-server").start()
    return server


def _wait_health(port: int, timeout: float = 25.0) -> bool:
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
                if response.status == 200:
                    return True
        except OSError:
            pass
        time.sleep(0.3)
    return False


def _tray(stop: threading.Event, url: str) -> None:
    import pystray
    import webview
    from PIL import Image

    try:
        image = Image.open(resource_path("icon-4-network.png")).convert("RGBA")
    except OSError:
        image = Image.new("RGBA", (64, 64), (17, 34, 51, 255))

    def on_open(_, item):
        for window in webview.windows:
            window.show()

    def on_exit(icon_, item):
        stop.set()
        icon_.stop()
        for window in list(webview.windows):
            window.destroy()
        os._exit(0)

    icon = pystray.Icon(
        "MonitoringAdmin",
        image,
        APP_NAME,
        menu=pystray.Menu(
            pystray.MenuItem("Открыть", on_open, default=True),
            pystray.MenuItem("Выход", on_exit),
        ),
    )
    icon.run(setup=lambda i: setattr(i, "visible", True))


def main() -> None:
    _ensure_secrets()
    from app.core.config import settings
    from app.api import download

    port = _find_free_port(settings.port)
    download.ACTUAL_PORT = port
    server = _start_server(port)
    if not _wait_health(port):
        print("Embedded server failed to start; see logs.")
        sys.exit(1)
    url = f"http://127.0.0.1:{port}/"
    stop = threading.Event()
    threading.Thread(target=_ensure_firewall_rule, args=(port,), daemon=True).start()
    threading.Thread(target=_tray, args=(stop, url), daemon=True).start()

    import webview

    window = webview.create_window(APP_NAME, url, width=1280, height=860, min_size=(960, 640))

    def on_closing():
        # Крестик прячет окно в трей; сервер продолжает принимать агентов.
        if stop.is_set():
            return True
        window.hide()
        return False

    window.events.closing += on_closing
    webview.start()
    server.should_exit = True
    stop.set()


def _fatal_log(message: str) -> None:
    """Windowed exe has no console — write the traceback to the data folder."""
    try:
        (DATA_DIR / "admin_app_error.log").write_text(message, encoding="utf-8")
    except OSError:
        pass
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, message[:1500], APP_NAME + " — ошибка", 0x10)
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback

        _fatal_log(traceback.format_exc())
        raise
