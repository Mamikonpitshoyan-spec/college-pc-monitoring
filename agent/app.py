"""User app: install wizard + live status + own parameters, one executable.

Flow for a fresh computer: open the exe → UAC (admin rights requested
automatically) → enter ONLY the pairing code from the administrator → the
app installs the embedded service, the service pairs and waits for
approval, and the app switches to the live status view with a button that
shows all scanned parameters of this computer.

The page is served by a tiny local HTTP server (default 127.0.0.1:8137)
and reads /status.json — no framework bridge, no races.
"""

from __future__ import annotations

import ctypes
import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP_NAME = "Monitoring Agent"
WINDOW_SIZE = (820, 640)
PORT_RANGE = range(8137, 8147)
SERVICE_DIR = Path("C:/Program Files/MonitoringAgent/service")
SERVICE_EXE_NAME = "MonitoringAgentService.exe"
INSTALLED_STATUS_PATH = SERVICE_DIR / "status.json"


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


if getattr(sys, "frozen", False):
    CONFIG_DIR = Path(sys.executable).resolve().parent
else:
    CONFIG_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("PROGRAMDATA", "C:/ProgramData")) / "MonitoringAgent"
STATUS_PATH = Path(
    os.getenv("MONITORING_STATUS_PATH", str(DATA_DIR / "status.json"))
)
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # как на сервере (services/pairing.py)
ADDRESS_BASE_PORT = 8000
ADDRESS_PORT_SPAN = 32


def parse_connection_code(raw: str) -> tuple[str, str | None]:
    """'A7K-29P-XXXX-XXXX' → ('A7K-29P', 'http://ip:port'); a bare code → (code, None)."""
    import ipaddress

    chars = "".join(ch for ch in raw.upper() if ch.isalnum())
    if len(chars) not in (6, 14) or any(ch not in CODE_ALPHABET for ch in chars):
        raise ValueError("bad_code")
    code = f"{chars[:3]}-{chars[3:6]}"
    if len(chars) == 6:
        return code, None
    value = 0
    for ch in chars[6:]:
        value = value * len(CODE_ALPHABET) + CODE_ALPHABET.index(ch)
    ip_value, offset = divmod(value, ADDRESS_PORT_SPAN)
    if ip_value > 0xFFFFFFFF:
        raise ValueError("bad_code")
    return code, f"http://{ipaddress.IPv4Address(ip_value)}:{ADDRESS_BASE_PORT + offset}"

import webview  # noqa: E402

_HTML = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root {
    --bg: #0A1520; --panel: #112233; --border: #1E3750;
    --text: #E3ECF5; --muted: #7F9AB5;
    --accent: #FF7F6B; --accent-soft: rgba(255, 127, 107,.10); --accent-line: rgba(255, 127, 107,.25);
    --ok: #5FD3A0; --err: #FF4D6D; --warn: #F2C14E;
    --mono: ui-monospace, "Cascadia Mono", Consolas, monospace;
  }
  * { box-sizing: border-box; margin: 0; }
  body {
    font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
    background: var(--bg); color: var(--text); font-size: 14px;
    padding: 18px; user-select: none;
  }
  .head { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
  .dot { width: 12px; height: 12px; border-radius: 50%; background: var(--err); flex-shrink: 0; }
  .dot.ok { background: var(--ok); box-shadow: 0 0 10px rgba(95, 211, 160,.7); }
  h1 { font-size: 15px; font-weight: 650; }
  h1 span { color: var(--accent); }
  .card {
    background: var(--panel); border: 1px solid var(--border); border-radius: 10px;
    padding: 12px 14px; margin-bottom: 12px;
  }
  .row { display: flex; justify-content: space-between; padding: 6px 0; font-size: 13px; }
  .row .k { color: var(--muted); }
  .row .v { font-family: var(--mono); text-align: right; overflow-wrap: anywhere; }
  .bar-row { margin: 10px 0; }
  .bar-row .lbl { display: flex; justify-content: space-between; font-size: 12px; color: var(--muted); margin-bottom: 4px; }
  .track { height: 6px; border-radius: 3px; background: rgba(255,255,255,.08); overflow: hidden; }
  .fill { height: 100%; border-radius: 3px; background: var(--accent); transition: width .4s; }
  .privacy { color: var(--muted); font-size: 11.5px; line-height: 1.5; }
  .err-text { color: var(--err); font-family: var(--mono); font-size: 11.5px; }
  .btn {
    display: block; width: 100%; padding: 12px; border-radius: 10px; cursor: pointer;
    font-size: 14px; font-weight: 650; font-family: inherit; color: #0A1520;
    background: var(--accent); border: none; margin-top: 12px;
  }
  .btn:hover { filter: brightness(1.1); }
  .btn:disabled { opacity: .6; cursor: wait; }
  .btn.ghost { background: transparent; color: var(--muted); border: 1px solid var(--border); }
  input {
    width: 100%; padding: 10px 12px; border-radius: 8px; font-size: 14px; font-family: var(--mono);
    background: #15293C; border: 1px solid var(--border); color: var(--text);
  }
  input:focus { outline: none; border-color: var(--accent-line); }
  label { display: block; color: var(--muted); font-size: 12px; margin: 12px 0 5px; }
  .setup-only { display: none; }
  body.mode-setup .setup-only { display: block; }
  body.mode-setup .status-only { display: none; }
  .err { color: var(--err); font-size: 12.5px; margin-top: 8px; display: none; }
  .sec h3 { font-size: 12px; color: var(--accent); text-transform: uppercase; letter-spacing: .05em; margin-bottom: 6px; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th { text-align: left; color: var(--muted); font-size: 10px; letter-spacing: .04em; padding: 5px 6px; }
  td { padding: 6px; border-top: 1px solid var(--border); font-family: var(--mono); }
  #jserr { display: none; color: var(--warn); font-family: var(--mono); font-size: 11px; margin-top: 8px; }
  .hidden { display: none; }
  .lang { margin-left: auto; display: flex; gap: 4px; }
  .lang button {
    padding: 4px 9px; font-size: 11px; font-weight: 700; font-family: inherit; cursor: pointer;
    color: var(--muted); background: transparent; border: 1px solid var(--border); border-radius: 6px;
  }
  .lang button.active { color: var(--accent); border-color: var(--accent-line); }
  .lang { position: relative; }
  .lang .theme-pop { top: calc(100% + 8px); bottom: auto; right: 0; }
  .theme-btn { display: grid; place-items: center; }
  .theme-pop {
    position: absolute; bottom: calc(100% + 8px); right: 10px; z-index: 50; width: 190px; padding: 8px;
    background: var(--panel); border: 1px solid var(--border); border-radius: 12px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, .25);
  }
  .theme-pop[hidden] { display: none; }
  .theme-opt {
    display: flex; align-items: center; gap: 10px; width: 100%; padding: 7px 8px; border: 1px solid transparent;
    border-radius: 8px; background: transparent; color: var(--text); font: inherit; font-size: 13px; cursor: pointer;
  }
  .theme-opt:hover { background: var(--accent-soft); }
  .theme-opt.active { border-color: var(--accent-line); background: var(--accent-soft); }
  .swatch { width: 22px; height: 22px; border-radius: 50%; border: 1px solid var(--border); flex-shrink: 0; }
  
html[data-theme="light"] { --bg:#F4F7FA;--sidebar:#EAF0F5;--panel:#FFFFFF;--panel2:#F6F9FB; --border:#C5D1DC;--border-soft:#DFE6EC;--text:#0F1E2C;--muted:#4A5E70; --accent:#E2543F;--accent-soft:rgba(226,84,63,.10);--accent-line:rgba(226,84,63,.35); --ok:#16855A;--warn:#A87700;--crit:#C81E3A;--err:#C81E3A;--off:#7A8C9C }
  html[data-theme="light"] body { background:var(--bg);color:var(--text) }
  html[data-theme="light"] .b-ok { color:#0F6B47 }
  html[data-theme="light"] .b-warn { color:#7D5800 }
  html[data-theme="light"] .b-crit { color:#A3122B }
  html[data-theme="light"] .stat.off .value { color:#5E7183 }
  html[data-theme="light"] .track { background:#DDE5EC }
  html[data-theme="light"] .btn, html[data-theme="light"] .btn-primary, html[data-theme="light"] a.dl { color:#FFFFFF }
  html[data-theme="light"] .btn.ghost { color:var(--muted) }
  html[data-theme="light"] .modal-overlay { background:rgba(15,30,44,.35) }
  html[data-theme="light"] .mini-btn.auto.on { color:#B23A28 }
  html[data-theme="light"] .b-neutral { color:#B23A28 }
  html[data-theme="light"] input { background:#FFFFFF;color:#0F1E2C;border-color:#C5D1DC }
  html[data-theme="lavender"] { --bg:#F5F4FB;--sidebar:#ECEAF8;--panel:#FFFFFF;--panel2:#F8F7FD; --border:#D6D2EE;--border-soft:#E8E5F6;--text:#2B2A45;--muted:#615F80; --accent:#7466D3;--accent-soft:rgba(116,102,211,.10);--accent-line:rgba(116,102,211,.35); --ok:#238A6A;--warn:#A87700;--crit:#C7385A;--err:#C7385A;--off:#8B89A6 }
  html[data-theme="lavender"] body { background:var(--bg);color:var(--text) }
  html[data-theme="lavender"] .b-ok { color:#1B6F55 }
  html[data-theme="lavender"] .b-warn { color:#7D5800 }
  html[data-theme="lavender"] .b-crit { color:#A32549 }
  html[data-theme="lavender"] .stat.off .value { color:#6E6C8C }
  html[data-theme="lavender"] .track { background:#E4E1F3 }
  html[data-theme="lavender"] .btn, html[data-theme="lavender"] .btn-primary, html[data-theme="lavender"] a.dl { color:#FFFFFF }
  html[data-theme="lavender"] .btn.ghost { color:var(--muted) }
  html[data-theme="lavender"] .modal-overlay { background:rgba(43,42,69,.30) }
  html[data-theme="lavender"] .mini-btn.auto.on { color:#5446B8 }
  html[data-theme="lavender"] .b-neutral { color:#5446B8 }
  html[data-theme="lavender"] input { background:#FFFFFF;color:#2B2A45;border-color:#D6D2EE }
  html[data-theme="graphite"] { --bg:#121417;--sidebar:#16191D;--panel:#1C2026;--panel2:#21262D; --border:#2E353E;--border-soft:#262C34;--text:#E6EAF0;--muted:#8D97A4; --accent:#4FD1A5;--accent-soft:rgba(79,209,165,.12);--accent-line:rgba(79,209,165,.35); --ok:#6FCF97;--warn:#E9B949;--crit:#F2687B;--err:#F2687B;--off:#5D6673 }
  html[data-theme="graphite"] body { background:var(--bg);color:var(--text) }
  html[data-theme="graphite"] .btn, html[data-theme="graphite"] .btn-primary, html[data-theme="graphite"] a.dl { color:#0E1512 }
  html[data-theme="graphite"] .mini-btn.auto.on { color:#8FE6C8 }
  html[data-theme="graphite"] .b-neutral { color:#8FE6C8 }
  html[data-theme="graphite"] input { background:#16191D;color:#E6EAF0 }
  html[data-theme="graphite"] .btn.ghost { color:var(--muted) }
  .btn-pair { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .src { color: var(--muted); font-size: 11.5px; margin: 0 2px 10px; }
  .loading { color: var(--muted); font-size: 13px; padding: 14px; text-align: center; }
  .layout { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; align-items: start; }
  .layout > div > .card:last-child { margin-bottom: 0; }
  @media (max-width: 640px) { .layout { grid-template-columns: 1fr; } }
</style>
</head>
<body>
  <div class="head"><div class="dot" id="dot"></div><h1 id="title">…</h1>
    <div class="lang"><button data-lang="ru">RU</button><button data-lang="am">AM</button><button data-lang="en">EN</button>
      <button class="theme-btn" id="theme-btn"><svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3a9 9 0 1 0 0 18c1.1 0 1.5-.8 1.5-1.5 0-.9-.7-1.3-.7-2.2 0-.8.7-1.3 1.5-1.3H17a4 4 0 0 0 4-4C21 6.6 17 3 12 3z"/><circle cx="7.5" cy="11" r="1"/><circle cx="10" cy="7" r="1"/><circle cx="15" cy="7.5" r="1"/></svg></button>
      <div class="theme-pop" id="theme-pop" hidden><button class="theme-opt" data-theme-choice="sea"><span class="swatch" style="background:linear-gradient(135deg,#0A1520 50%,#FF7F6B 50%)"></span><span data-t="theme.sea"></span></button><button class="theme-opt" data-theme-choice="light"><span class="swatch" style="background:linear-gradient(135deg,#F4F7FA 50%,#E2543F 50%)"></span><span data-t="theme.light"></span></button><button class="theme-opt" data-theme-choice="lavender"><span class="swatch" style="background:linear-gradient(135deg,#F5F4FB 50%,#7466D3 50%)"></span><span data-t="theme.lavender"></span></button><button class="theme-opt" data-theme-choice="graphite"><span class="swatch" style="background:linear-gradient(135deg,#121417 50%,#4FD1A5 50%)"></span><span data-t="theme.graphite"></span></button></div></div>
  </div>

  <div class="layout">
  <div class="col-left">
  <div class="card setup-only">
    <label id="l-code">Код подключения (от администратора)</label>
    <input id="i-code" placeholder="A7K-29P-XXXX-XXXX">
    <div id="server-box" class="hidden">
      <label id="l-server-in">Адрес сервера</label>
      <input id="i-server" placeholder="192.168.1.9:8000">
    </div>
    <div class="err" id="setup-err"></div>
    <button class="btn" id="i-install">Подключить</button>
    <div class="privacy" style="margin-top:12px" id="l-priv-setup">Установка поставит службу мониторинга (автозапуск с Windows) и добавит это приложение в автозагрузку. Потребуются права администратора.</div>
  </div>

  <div class="card status-only">
    <div class="privacy" id="l-reconnect-hint">Компьютер уже подключён. Чтобы подключить его к другому серверу или по новому коду — «Подключить заново».</div>
    <button class="btn ghost" id="reconnect-btn" style="margin-top:10px">Подключить заново</button>
  </div>
  </div>
  <div class="col-right">
  <div class="card">
    <div class="row"><span class="k" id="l-conn">Связь с сервером</span><span class="v" id="v-conn">—</span></div>
    <div class="row"><span class="k" id="l-last">Последний отчёт</span><span class="v" id="v-last">—</span></div>
    <div class="row"><span class="k" id="l-server">Сервер</span><span class="v" id="v-server">—</span></div>
    <div class="row" id="err-row" style="display:none"><span class="k" id="l-err">Проблема</span><span class="v err-text" id="v-err"></span></div>
  </div>

  <div class="card">
    <div class="bar-row"><div class="lbl"><span>CPU</span><span id="v-cpu">—</span></div><div class="track"><div class="fill" id="b-cpu" style="width:0%"></div></div></div>
    <div class="bar-row"><div class="lbl"><span>RAM</span><span id="v-ram">—</span></div><div class="track"><div class="fill" id="b-ram" style="width:0%"></div></div></div>
    <div class="bar-row"><div class="lbl"><span id="l-disk">Диск</span><span id="v-disk">—</span></div><div class="track"><div class="fill" id="b-disk" style="width:0%"></div></div></div>
  </div>

  <div class="btn-pair">
    <button class="btn" id="params-btn">Мои параметры</button>
    <button class="btn ghost" id="scan-btn">Сканировать компьютер</button>
  </div>
  </div>
  </div>

  <div id="params"></div>

  <div class="card">
    <div class="privacy" id="privacy">Собираются только технические данные: нагрузка процессора, память, диски и сеть. Личные файлы, пароли и переписки не собираются.</div>
    <div id="jserr"></div>
  </div>

<script>
window.onerror = function (message) {
  const el = document.getElementById("jserr");
  el.style.display = "block";
  el.textContent = "JS: " + message;
};

const LANGS = {
  ru: {conn: "Связь с сервером", on: "НА СВЯЗИ", off: "НЕТ СВЯЗИ",
       last: "Последний отчёт", server: "Сервер", problem: "Проблема", disk: "Диск",
       never: "ещё не было", na: "нет данных",
       lserver: "Адрес сервера", lcode: "Код подключения (от администратора)",
       install: "Подключить", installing: "Устанавливаю…", params: "Мои параметры",
       scan: "Сканировать компьютер", scanning: "Сканирую компьютер… это займёт 5–15 секунд",
       srcService: "Данные службы мониторинга", srcScan: "Локальное сканирование", noParams: "Данных пока нет — нажмите «Сканировать компьютер».",
       gpuNone: "не обнаружена", ports: "Открытые порты",
       theme: "Тема", theme_sea: "Морская", theme_light: "Светлая", theme_lavender: "Лавандовая", theme_graphite: "Графит",
       reconnectHint: "Компьютер уже подключён. Чтобы подключить его к другому серверу или по новому коду — «Подключить заново».",
       back: "← Назад к статусу", fillAll: "Заполните все поля", reconnect: "Подключить заново",
       errCode: "Код не найден или истёк. Возьмите новый у администратора.",
       errServer: "Не удалось связаться с сервером. Проверьте адрес.",
       privacy: "Собираются только технические данные: нагрузка процессора, память, диски и сеть. Личные файлы, пароли и переписки не собираются.",
       privacySetup: "Установка поставит службу мониторинга (автозапуск с Windows) и добавит это приложение в автозагрузку. Потребуются права администратора.",
       "k_model": "Модель", "k_manufacturer": "Производитель", "k_cores": "Физические ядра",
       "k_threads": "Логические потоки", "k_freq": "Частота", "k_load": "Загрузка",
       "k_total": "Всего", "k_used": "Использовано", "k_free": "Свободно",
       "k_adapter": "Адаптер", "k_driver": "Драйвер", "k_vram": "Видеопамять",
       "k_biosVersion": "BIOS", "k_biosVendor": "Производитель BIOS", "k_release": "Дата выпуска",
       "k_serial": "Серийный номер", "k_board": "Материнская плата", "k_boardVendor": "Производитель платы",
       "k_hostname": "Имя компьютера", "k_os": "Операционная система", "k_arch": "Архитектура",
       "k_uptime": "Время работы",
       secCpu: "Процессор", secMem: "Оперативная память", secDisks: "Диски", secNet: "Сеть",
       secSys: "Система", secBios: "BIOS / материнская плата", secGpu: "Видеокарта", secTemp: "Температура",
       sensors: "Датчики", k_temp: "Температура", ghz: " ГГц", perSec: "/с", locale: "ru-RU",
       units: ["Б", "КБ", "МБ", "ГБ", "ТБ"],
       thPart: "РАЗДЕЛ", thFs: "ФС", thSize: "РАЗМЕР", thUsed: "ЗАНЯТО", thLoad: "ЗАГРУЗКА",
       thIface: "АДАПТЕР", thSpeed: "СКОРОСТЬ", thTotal: "ВСЕГО ↓ / ↑", thProto: "ПРОТОКОЛ", thPort: "ПОРТ", thProgram: "ПРОГРАММА",
       err_bad_code: "Неверный код подключения. Проверьте, что он введён полностью.",
       err_need_server: "Этот код без адреса сервера — впишите адрес сервера.",
       err_need_admin: "Нужны права администратора: закройте программу и запустите снова, ответив «Да».",
       err_locked: "Старая версия ещё работает. Перезагрузите компьютер и повторите.",
       err_missing_files: "Файл программы повреждён. Скачайте программу заново.",
       errInstall: "Не удалось установить",
       trayOpen: "Открыть", trayExit: "Выход",
       titleOk: "Этот компьютер под мониторингом", titleSetup: "Подключение к мониторингу"},
  am: {conn: "Կապը սերվերի հետ", on: "ԿԱՊՎԱԾ Է", off: "ԿԱՊԸ ԿՏՐՎԱԾ Է",
       last: "Վերջին զեկույցը", server: "Սերվեր", problem: "Խնդիր", disk: "Սկավառակ",
       never: "դեռ եղել չէ", na: "տվյալներ չկան",
       lserver: "Սերվերի հասցեն", lcode: "Միացման կոդը (ադմինիստրատորից)",
       install: "Միացնել", installing: "Տեղադրվում է…", params: "Իմ պարամետրերը",
       scan: "Սկանավորել համակարգիչը", scanning: "Սկանավորում եմ… 5–15 վայրկյան",
       srcService: "Մոնիտորինգի ծառայության տվյալներ", srcScan: "Տեղական սկանավորում", noParams: "Տվյալներ դեռ չկան — սեղմեք «Սկանավորել համակարգիչը»։",
       gpuNone: "չի հայտնաբերվել", ports: "Բաց պորտեր",
       theme: "Թեմա", theme_sea: "Ծովային", theme_light: "Լուսավոր", theme_lavender: "Լավանդա", theme_graphite: "Գրաֆիտ",
       reconnectHint: "Համակարգիչն արդեն միացված է։ Այլ սերվերին կամ նոր կոդով միացնելու համար՝ «Նորից միացնել»։",
       back: "← Վերադառնալ կարգավիճակին", fillAll: "Լրացրեք բոլոր դաշտերը", reconnect: "Նորից միացնել",
       errCode: "Կոդը չի գտնվել կամ ժամկետանց է։ Վերցրեք նորը ադմինիստրատորից։",
       errServer: "Չհաջողվեց կապվել սերվերի հետ։ Ստուգեք հասցեն։",
       privacy: "Հավաքվում են միայն տեխնիկական տվյալներ՝ պրոցեսորի, հիշողության, սկավառակների և ցանցի բեռնվածությունը։ Անձնական ֆայլերը, գաղտնաբառերը և նամակագրությունը չեն հավաքվում։",
       privacySetup: "Տեղադրումը կտեղադրի մոնիտորինգի ծառայությունը (ավտոմեկնարկ Windows-ի հետ) և այս հավելվածը կավելացնի ավտոմեկնարկին։ Կպահանջվեն ադմինիստրատորի իրավունքներ։",
       "k_model": "Մոդել", "k_manufacturer": "Արտադրող", "k_cores": "Ֆիզիկական միջուկներ",
       "k_threads": "Տրամաբանական հոսքեր", "k_freq": "Հաճախականություն", "k_load": "Բեռնվածություն",
       "k_total": "Ընդհանուր", "k_used": "Օգտագործված", "k_free": "Ազատ",
       "k_adapter": "Ադապտեր", "k_driver": "Դրայվեր", "k_vram": "Վիդեոհիշողություն",
       "k_biosVersion": "BIOS", "k_biosVendor": "BIOS-ի արտադրողը", "k_release": "Թողարկման ամսաթիվ",
       "k_serial": "Սերիական համար", "k_board": "Մայր պլատա", "k_boardVendor": "Պլատայի արտադրողը",
       "k_hostname": "Համակարգչի անունը", "k_os": "Օպերացիոն համակարգ", "k_arch": "Ճարտարապետություն",
       "k_uptime": "Աշխատանքի ժամանակը",
       secCpu: "Պրոցեսոր", secMem: "Օպերատիվ հիշողություն", secDisks: "Սկավառակներ", secNet: "Ցանց",
       secSys: "Համակարգ", secBios: "BIOS / մայր պլատա", secGpu: "Վիդեոքարտ", secTemp: "Ջերմաստիճան",
       sensors: "Սենսորներ", k_temp: "Ջերմաստիճան", ghz: " ԳՀց", perSec: "/վ", locale: "hy-AM",
       units: ["Բ", "ԿԲ", "ՄԲ", "ԳԲ", "ՏԲ"],
       thPart: "ԲԱԺԻՆ", thFs: "ՖՀ", thSize: "ՉԱՓ", thUsed: "ԶԲԱՂՎԱԾ", thLoad: "ԲԵՌՆՎԱԾՈՒԹՅՈՒՆ",
       thIface: "ԱԴԱՊՏԵՐ", thSpeed: "ԱՐԱԳՈՒԹՅՈՒՆ", thTotal: "ԸՆԴԱՄԵՆԸ ↓ / ↑", thProto: "ԱՐՁԱՆԱԳՐՈՒԹՅՈՒՆ", thPort: "ՊՈՐՏ", thProgram: "ԾՐԱԳԻՐ",
       err_bad_code: "Միացման կոդը սխալ է։ Ստուգեք, որ այն ամբողջությամբ է մուտքագրված։",
       err_need_server: "Այս կոդում սերվերի հասցե չկա — մուտքագրեք սերվերի հասցեն։",
       err_need_admin: "Անհրաժեշտ են ադմինիստրատորի իրավունքներ․ փակեք ծրագիրը և նորից գործարկեք՝ պատասխանելով «Այո»։",
       err_locked: "Հին տարբերակը դեռ աշխատում է։ Վերագործարկեք համակարգիչը և կրկնեք։",
       err_missing_files: "Ծրագրի ֆայլը վնասված է։ Ներբեռնեք ծրագիրը նորից։",
       errInstall: "Չհաջողվեց տեղադրել",
       trayOpen: "Բացել", trayExit: "Ելք",
       titleOk: "Այս համակարգիչը հսկվում է", titleSetup: "Միացում մոնիտորինգին"},
  en: {conn: "Server connection", on: "CONNECTED", off: "DISCONNECTED",
       last: "Last report", server: "Server", problem: "Problem", disk: "Disk",
       never: "not yet", na: "no data",
       lserver: "Server address", lcode: "Connection code (from the administrator)",
       install: "Connect", installing: "Installing…", params: "My parameters",
       scan: "Scan computer", scanning: "Scanning the computer… 5–15 seconds",
       srcService: "Monitoring service data", srcScan: "Local scan", noParams: "No data yet — click “Scan computer”.",
       gpuNone: "not detected", ports: "Open ports",
       theme: "Theme", theme_sea: "Sea", theme_light: "Light", theme_lavender: "Lavender", theme_graphite: "Graphite",
       reconnectHint: "This computer is already connected. To connect it to another server or with a new code, use “Connect again”.",
       back: "← Back to status", fillAll: "Fill in all fields", reconnect: "Connect again",
       errCode: "Code not found or expired. Get a new one from the administrator.",
       errServer: "Could not reach the server. Check the address.",
       privacy: "Only technical data is collected: CPU, memory, disk, and network load. Personal files, passwords, and messages are not collected.",
       privacySetup: "The setup will install the monitoring service (auto-start with Windows) and add this app to Startup. Administrator rights will be requested.",
       "k_model": "Model", "k_manufacturer": "Manufacturer", "k_cores": "Physical cores",
       "k_threads": "Logical threads", "k_freq": "Frequency", "k_load": "Load",
       "k_total": "Total", "k_used": "Used", "k_free": "Free",
       "k_adapter": "Adapter", "k_driver": "Driver", "k_vram": "Video memory",
       "k_biosVersion": "BIOS", "k_biosVendor": "BIOS vendor", "k_release": "Release date",
       "k_serial": "Serial number", "k_board": "Motherboard", "k_boardVendor": "Board vendor",
       "k_hostname": "Computer name", "k_os": "Operating system", "k_arch": "Architecture",
       "k_uptime": "Uptime",
       secCpu: "Processor", secMem: "Memory", secDisks: "Disks", secNet: "Network",
       secSys: "System", secBios: "BIOS / motherboard", secGpu: "GPU", secTemp: "Temperature",
       sensors: "Sensors", k_temp: "Temperature", ghz: " GHz", perSec: "/s", locale: "en-GB",
       units: ["B", "KB", "MB", "GB", "TB"],
       thPart: "PARTITION", thFs: "FS", thSize: "SIZE", thUsed: "USED", thLoad: "LOAD",
       thIface: "ADAPTER", thSpeed: "SPEED", thTotal: "TOTAL ↓ / ↑", thProto: "PROTOCOL", thPort: "PORT", thProgram: "PROGRAM",
       err_bad_code: "Invalid connection code. Check that it is entered completely.",
       err_need_server: "This code has no server address — enter the server address.",
       err_need_admin: "Administrator rights are needed: close the app and start it again, answering Yes.",
       err_locked: "The old version is still running. Restart the computer and try again.",
       err_missing_files: "The program file is damaged. Download the program again.",
       errInstall: "Installation failed",
       trayOpen: "Open", trayExit: "Exit",
       titleOk: "This computer is monitored", titleSetup: "Connect to monitoring"},
};
let lang = document.documentElement.dataset.lang || "ru";
let t = LANGS[lang];

function applyLang() {
  document.getElementById("l-conn").textContent = t.conn;
  document.getElementById("l-last").textContent = t.last;
  document.getElementById("l-server").textContent = t.server;
  document.getElementById("l-err").textContent = t.problem;
  document.getElementById("l-disk").textContent = t.disk;
  document.getElementById("l-code").textContent = t.lcode;
  document.getElementById("l-server-in").textContent = t.lserver;
  document.getElementById("reconnect-btn").textContent = t.reconnect;
  document.getElementById("l-reconnect-hint").textContent = t.reconnectHint;
  document.getElementById("l-priv-setup").textContent = t.privacySetup;
  document.getElementById("scan-btn").textContent = t.scan;
  document.getElementById("privacy").textContent = t.privacy;
  const install = document.getElementById("i-install");
  if (!install.disabled) install.textContent = t.install;
  document.title = "Monitoring Agent";
  const pb = document.getElementById("params-btn");
  if (pb) pb.textContent = paramsVisible ? t.back : t.params;
  document.getElementById("theme-btn").title = t.theme;
  document.querySelectorAll("[data-t]").forEach(function (el) { el.textContent = t[el.dataset.t.replace(".", "_")]; });
  markTheme();
  document.querySelectorAll(".lang button[data-lang]").forEach(function (b) {
    b.classList.toggle("active", b.dataset.lang === lang);
  });
}
document.addEventListener("click", function (event) {
  const b = event.target.closest(".lang button[data-lang]");
  if (!b) return;
  lang = b.dataset.lang;
  t = LANGS[lang];
  savePrefs();
  applyLang();
  refresh();
  if (paramsVisible && lastRendered) renderParams(lastRendered.snapshot, lastRendered.source);
  syncTrayLang();
});

// Тема и язык сохраняются в файл настроек (окно программы не хранит localStorage между запусками).
function savePrefs() {
  const prefs = { theme: document.documentElement.dataset.theme || "sea", lang: lang };
  fetch("/prefs", { method: "POST", body: JSON.stringify(prefs) }).catch(function () {});
}
function markTheme() {
  const current = document.documentElement.dataset.theme || "sea";
  document.querySelectorAll("[data-theme-choice]").forEach(function (b) {
    b.classList.toggle("active", b.dataset.themeChoice === current);
  });
}
document.addEventListener("click", function (event) {
  const pop = document.getElementById("theme-pop");
  if (event.target.closest("#theme-btn")) { pop.hidden = !pop.hidden; return; }
  const choice = event.target.closest("[data-theme-choice]");
  if (choice) {
    document.documentElement.dataset.theme = choice.dataset.themeChoice;
    markTheme();
    savePrefs();
  }
  if (!event.target.closest("#theme-pop")) pop.hidden = true;
});

// Язык пунктов меню в трее (Открыть / Выход) — как в окне.
function syncTrayLang() {
  fetch("/lang", { method: "POST", body: lang }).catch(function () {});
}

function fmtBytes(b) {
  if (b === null || b === undefined) return "—";
  const u = t.units;
  let s = Number(b), i = 0;
  while (s >= 1024 && i < u.length - 1) { s /= 1024; i++; }
  return s.toFixed(i ? 1 : 0) + " " + u[i];
}
function pct(v) { return (v === null || v === undefined) ? "—" : Math.round(v) + " %"; }
function setBar(id, v) {
  const el = document.getElementById("b-" + id);
  if (v === null || v === undefined) { el.style.width = "0%"; return; }
  el.style.width = Math.min(v, 100) + "%";
  el.style.background = v >= 95 ? "var(--err)" : v >= 80 ? "var(--warn)" : "var(--accent)";
}
function esc(v) {
  return String(v === null || v === undefined ? "" : v).replace(/[&<>"]/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
  });
}

function refresh() {
  fetch("/status.json")
    .then(function (r) { return r.json(); })
    .then(function (s) {
      const ok = !!s.connected;
      document.getElementById("dot").className = "dot" + (ok ? " ok" : "");
      document.getElementById("title").textContent = document.body.classList.contains("mode-setup") ? t.titleSetup : t.titleOk;
      document.getElementById("v-conn").textContent = ok ? t.on : t.off;
      document.getElementById("v-conn").style.color = ok ? "var(--ok)" : "var(--err)";
      document.getElementById("v-last").textContent = s.last_report_at
        ? s.last_report_at.slice(11, 19) : t.never;
      document.getElementById("v-server").textContent =
        (s.server_url || "—").replace("http://", "").replace("https://", "");
      const errRow = document.getElementById("err-row");
      if (s.last_error && !ok) {
        errRow.style.display = "";
        document.getElementById("v-err").textContent = errText(s.last_error);
      } else errRow.style.display = "none";
      document.getElementById("v-cpu").textContent = pct(s.cpu_percent);
      document.getElementById("v-ram").textContent = pct(s.ram_percent);
      document.getElementById("v-disk").textContent = pct(s.disk_percent);
      setBar("cpu", s.cpu_percent); setBar("ram", s.ram_percent); setBar("disk", s.disk_percent);
    })
    .catch(function () {});
}

function errText(raw) {
  if (/HTTP 40[349]/.test(raw)) return t.errCode;
  if (/Connect|Timeout|Network|OSError|HTTP 5/.test(raw)) return t.errServer;
  return raw;
}

function fmtUptime(sec) {
  if (sec === null || sec === undefined) return null;
  let rest = Math.floor(Number(sec));
  const d = Math.floor(rest / 86400); rest %= 86400;
  const h = Math.floor(rest / 3600); rest %= 3600;
  const m = Math.floor(rest / 60);
  if (lang === "en") return d > 0 ? d + " d " + h + " h" : (h > 0 ? h + " h " + m + " min" : m + " min");
  if (lang === "am") return d > 0 ? d + " օր " + h + " ժ" : (h > 0 ? h + " ժ " + m + " ր" : m + " ր");
  return d > 0 ? d + " д. " + h + " ч." : (h > 0 ? h + " ч. " + m + " мин." : m + " мин.");
}
function kvRow(k, v, unit) {
  const text = (v === null || v === undefined || v === "") ? t.na : v + (unit || "");
  return '<div class="row"><span class="k">' + esc(k) + '</span><span class="v">' + esc(text) + '</span></div>';
}
let lastRendered = null;

function renderParams(snapshot, source) {
  lastRendered = { snapshot: snapshot, source: source };
  const box = document.getElementById("params");
  if (!snapshot) { box.innerHTML = '<div class="card loading">' + t.noParams + '</div>'; return; }
  const p = snapshot, io = (p.disk || {}).io || {}, mb = ((p.bios || {}).motherboard) || {};
  let html = source ? '<div class="src">' + esc(t[source]) + (p.collected_at ? " · " + esc(new Date(p.collected_at).toLocaleString(t.locale)) : "") + '</div>' : "";
  html += '<div class="sec card"><h3>' + t.secCpu + '</h3>'
    + kvRow(t.k_model, (p.cpu || {}).model) + kvRow(t.k_manufacturer, (p.cpu || {}).manufacturer)
    + kvRow(t.k_cores, (p.cpu || {}).physical_cores) + kvRow(t.k_threads, (p.cpu || {}).logical_processors)
    + kvRow(t.k_freq, (p.cpu || {}).frequency_MHz ? ((p.cpu.frequency_MHz / 1000).toFixed(2)) : null, t.ghz)
    + kvRow(t.k_load, (p.cpu || {}).usage_percent, " %") + '</div>';
  html += '<div class="sec card"><h3>' + t.secMem + '</h3>'
    + kvRow(t.k_total, fmtBytes((p.ram || {}).total_bytes))
    + kvRow(t.k_used, fmtBytes((p.ram || {}).used_bytes))
    + kvRow(t.k_free, fmtBytes((p.ram || {}).available_bytes))
    + kvRow(t.k_load, (p.ram || {}).usage_percent, " %") + '</div>';
  const parts = ((p.disk || {}).partitions || []).map(function (pt) {
    return "<tr><td>" + esc(pt.mountpoint || pt.device || "—") + "</td><td>" + esc(pt.filesystem || "—")
      + "</td><td>" + esc(fmtBytes(pt.total_bytes) || "—") + "</td><td>" + esc(fmtBytes(pt.used_bytes) || "—")
      + "</td><td>" + esc(pct(pt.usage_percent)) + "</td></tr>";
  }).join("");
  html += '<div class="sec card"><h3>' + t.secDisks + '</h3>'
    + '<table><thead><tr><th>' + t.thPart + '</th><th>' + t.thFs
    + '</th><th>' + t.thSize + '</th><th>' + t.thUsed
    + '</th><th>' + t.thLoad + '</th></tr></thead><tbody>' + parts + '</tbody></table></div>';
  const allNet = (p.network || {}).interfaces || [];
  const ifaces = (allNet.some(function (n) { return n.primary; }) ? allNet.filter(function (n) { return n.primary; }) : allNet).map(function (n) {
    return "<tr><td>" + esc(n.name || "—") + "</td><td>" + esc((n.ipv4 || []).join(", ") || "—")
      + "</td><td>" + esc(fmtBytes(n.rx_speed_Bps)) + t.perSec + " ↓ · " + esc(fmtBytes(n.tx_speed_Bps)) + t.perSec + " ↑"
      + "</td><td>" + esc(fmtBytes(n.rx_bytes) || "—")
      + " / " + esc(fmtBytes(n.tx_bytes) || "—") + "</td></tr>";
  }).join("");
  html += '<div class="sec card"><h3>' + t.secNet + '</h3>'
    + '<table><thead><tr><th>' + t.thIface + '</th><th>IPv4'
    + '</th><th>' + t.thSpeed + '</th><th>' + t.thTotal
    + '</th></tr></thead><tbody>' + ifaces + '</tbody></table></div>';
  const sys = p.system || {};
  html += '<div class="sec card"><h3>' + t.secSys + '</h3>'
    + kvRow(t.k_hostname, sys.hostname)
    + kvRow(t.k_os, sys.os ? sys.os + " " + (sys.windows_version || "") : null)
    + kvRow(t.k_arch, sys.architecture)
    + kvRow(t.k_manufacturer, sys.manufacturer)
    + kvRow(t.k_model, sys.model)
    + kvRow(t.k_uptime, fmtUptime(sys.uptime_seconds)) + '</div>';
  const bios = p.bios || {};
  html += '<div class="sec card"><h3>' + t.secBios + '</h3>'
    + kvRow(t.k_biosVersion, bios.version) + kvRow(t.k_biosVendor, bios.manufacturer)
    + kvRow(t.k_release, bios.release_date) + kvRow(t.k_serial, bios.serial_number)
    + kvRow(t.k_board, mb.model) + kvRow(t.k_boardVendor, mb.manufacturer) + '</div>';
  const gpus = p.gpu && p.gpu.adapters ? p.gpu.adapters : [];
  const gpuMissing = p.gpu && Array.isArray(p.gpu.adapters) && !p.gpu.adapters.length;
  html += '<div class="sec card"><h3>' + t.secGpu + '</h3>'
    + (gpus.length ? gpus.map(function (a) {
        return kvRow(t.k_adapter, a.name) + kvRow(t.k_driver, a.driver_version) + kvRow(t.k_vram, fmtBytes(a.adapter_ram_bytes))
          + kvRow(t.k_load, a.usage_percent, " %") + kvRow(t.k_temp, a.temperature_celsius, " °C");
      }).join('<div class="kv"></div>') : '<div class="row"><span class="k">' + t.k_adapter + '</span><span class="v">' + (gpuMissing ? t.gpuNone : t.na) + '</span></div>') + '</div>';
  const portList = p.ports ? p.ports.listening : null;
  html += '<div class="sec card"><h3>' + t.ports + '</h3>'
    + (Array.isArray(portList) && portList.length
      ? '<table><thead><tr><th>' + t.thProto + '</th><th>' + t.thPort + '</th><th>' + t.thProgram + '</th></tr></thead><tbody>' + portList.map(function (pt) {
          return "<tr><td>" + esc(pt.protocol) + "</td><td>" + esc(pt.port) + "</td><td>" + esc(pt.process || t.na) + "</td></tr>";
        }).join("") + '</tbody></table>'
      : '<div class="row"><span class="k">' + t.ports + '</span><span class="v">' + (Array.isArray(portList) ? "0" : t.na) + '</span></div>')
    + '</div>';
  const sensors = p.temperature && p.temperature.sensors ? p.temperature.sensors : [];
  html += '<div class="sec card"><h3>' + t.secTemp + '</h3>'
    + (sensors.length ? sensors.map(function (s2) {
        return '<div class="row"><span class="k">' + esc(s2.label || s2.chip || "—") + '</span><span class="v">' + esc(s2.current_celsius) + ' °C</span></div>';
      }).join("") : '<div class="row"><span class="k">' + t.sensors + '</span><span class="v">' + t.na + '</span></div>') + '</div>';
  box.innerHTML = html;
}

let paramsVisible = false;
let lastScan = null;

function showParams(button) {
  paramsVisible = true;
  button.textContent = t.back;
}

function hideParams() {
  paramsVisible = false;
  document.getElementById("params-btn").textContent = t.params;
  document.getElementById("params").innerHTML = "";
}

// Сканирование этого ПК самим приложением — работает и без подключения к серверу.
function runScan() {
  const box = document.getElementById("params");
  const scanBtn = document.getElementById("scan-btn");
  showParams(document.getElementById("params-btn"));
  scanBtn.disabled = true;
  box.innerHTML = '<div class="card loading">' + t.scanning + '</div>';
  fetch("/scan").then(function (r) { return r.json(); }).then(function (res) {
    lastScan = res.snapshot || null;
    renderParams(lastScan, "srcScan");
  }).catch(function () {
    renderParams(null);
  }).finally(function () { scanBtn.disabled = false; });
}

document.getElementById("params-btn").addEventListener("click", function () {
  if (paramsVisible) { hideParams(); return; }
  const button = this;
  fetch("/status.json").then(function (r) { return r.json(); }).then(function (s) {
    if (s.snapshot) { showParams(button); renderParams(s.snapshot, "srcService"); }
    else if (lastScan) { showParams(button); renderParams(lastScan, "srcScan"); }
    else runScan();
  }).catch(function () { runScan(); });
});

document.getElementById("scan-btn").addEventListener("click", runScan);

function setupState() {
  fetch("/state").then(function (r) { return r.json(); }).then(function (st) {
    if (st.installed) {
      document.body.classList.remove("mode-setup");
    } else {
      document.body.classList.add("mode-setup");
      if (st.server_url) document.getElementById("i-server").value = st.server_url;
    }
  }).catch(function () {});
}

function codeChars() {
  return document.getElementById("i-code").value.toUpperCase().replace(/[^A-Z0-9]/g, "");
}

// Код без адреса (6 символов) — показываем поле адреса для ручного ввода.
document.getElementById("i-code").addEventListener("input", function () {
  document.getElementById("server-box").classList.toggle("hidden", codeChars().length !== 6);
});

document.getElementById("reconnect-btn").addEventListener("click", function () {
  fetch("/setup/reconnect", { method: "POST" }).catch(function () {});
});

document.getElementById("i-install") && document.getElementById("i-install").addEventListener("click", function () {
  const button = this;
  const needServer = codeChars().length === 6;
  const serverUrl = needServer ? document.getElementById("i-server").value.trim() : "";
  const code = document.getElementById("i-code").value.trim();
  const errBox = document.getElementById("setup-err");
  errBox.style.display = "none";
  if (!code || (needServer && !serverUrl)) {
    errBox.textContent = t.fillAll;
    errBox.style.display = "block";
    return;
  }
  button.disabled = true;
  button.textContent = t.installing;
  fetch("/setup/install", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ server_url: serverUrl, pairing_code: code }),
  }).then(function (r) { return r.json(); }).then(function (res) {
    if (res.ok) {
      window.location.reload();
    } else {
      errBox.textContent = t["err_" + res.code] || (t.errInstall + (res.error ? ": " + res.error : ""));
      errBox.style.display = "block";
      button.disabled = false;
      button.textContent = t.install;
    }
  }).catch(function (e) {
    errBox.textContent = t.errInstall + ": " + String(e);
    errBox.style.display = "block";
    button.disabled = false;
    button.textContent = t.install;
  });
});

applyLang();
syncTrayLang();
setupState();
refresh();
setInterval(refresh, 2000);
</script>
</body>
</html>"""

_EMPTY_STATUS = {
    "updated_at": None, "connected": False, "agent_id": None, "hostname": None,
    "server_url": "", "last_report_at": None, "last_error": None,
    "cpu_percent": None, "ram_percent": None, "disk_percent": None, "snapshot": None,
}


def _read_status() -> dict:
    """Prefer the installed service status; fall back to the local one."""
    for candidate in (INSTALLED_STATUS_PATH, STATUS_PATH):
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (FileNotFoundError, ValueError, OSError):
            continue
    return dict(_EMPTY_STATUS)


def service_installed() -> bool:
    return (SERVICE_DIR / SERVICE_EXE_NAME).exists()


def read_installed_server_url() -> str | None:
    """Server URL from the installed service .env (after installation)."""
    env_path = SERVICE_DIR / ".env"
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("MONITORING_SERVER_URL="):
                return line.split("=", 1)[1].strip() or None
    except OSError:
        pass
    return None


def install_service(server_url: str, pairing_code: str) -> None:
    """Copy the embedded service to Program Files, configure, install, start."""
    if not is_admin():
        raise RuntimeError("need_admin")
    bundled = Path(getattr(sys, "_MEIPASS", CONFIG_DIR)) / "MonitoringAgentService"
    dest_root = Path("C:/Program Files/MonitoringAgent")
    dest_service = dest_root / "service"

    if not (bundled / SERVICE_EXE_NAME).exists():
        raise RuntimeError("missing_files")

    _remove_existing_service(dest_service)
    shutil.copytree(bundled, dest_service)

    env_text = (
        f"MONITORING_SERVER_URL={server_url}\n"
        f"MONITORING_PAIRING_CODE={pairing_code}\n"
        "MONITORING_REPORT_INTERVAL_SECONDS=5\n"
    )
    (dest_service / ".env").write_text(env_text, encoding="utf-8")

    service_exe = dest_service / SERVICE_EXE_NAME
    subprocess.run([str(service_exe), "install"], check=True, capture_output=True, cwd=str(dest_service))
    subprocess.run([str(service_exe), "start"], check=True, capture_output=True, cwd=str(dest_service))

    if getattr(sys, "frozen", False):
        startup = Path(os.getenv("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs/Startup"
        targets = [dest_root / "MonitoringAgentApp.exe"]
        if startup.is_dir():
            targets.append(startup / "MonitoringAgentApp.exe")
        for target in targets:
            try:
                if target.resolve() != Path(sys.executable).resolve():
                    shutil.copy2(sys.executable, target)
            except OSError:
                pass  # копия запущена (окно открыто из этой папки) — оставляем старую


def _remove_existing_service(dest_service: Path) -> None:
    """Stop and unregister a previous installation so reinstall works over it."""
    no_window = 0x08000000
    for command in (["sc", "stop", "MonitoringAgent"], ["sc", "delete", "MonitoringAgent"]):
        subprocess.run(command, capture_output=True, creationflags=no_window)
    import time

    for _ in range(30):
        if not dest_service.exists():
            return
        try:
            shutil.rmtree(dest_service)
            return
        except OSError:
            time.sleep(1)  # процесс службы ещё завершается
    raise RuntimeError("locked")


PREFS_PATH = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "MonitoringAgent" / "prefs.json"
UI_THEMES = ("sea", "light", "lavender", "graphite")


def read_prefs() -> dict:
    prefs = {"theme": "sea", "lang": "ru"}
    try:
        saved = json.loads(PREFS_PATH.read_text(encoding="utf-8"))
        if saved.get("theme") in UI_THEMES:
            prefs["theme"] = saved["theme"]
        if saved.get("lang") in ("ru", "am", "en"):
            prefs["lang"] = saved["lang"]
    except (OSError, ValueError, AttributeError):
        pass
    return prefs


def save_prefs(update: dict) -> dict:
    prefs = read_prefs()
    if update.get("theme") in UI_THEMES:
        prefs["theme"] = update["theme"]
    if update.get("lang") in ("ru", "am", "en"):
        prefs["lang"] = update["lang"]
    try:
        PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
        PREFS_PATH.write_text(json.dumps(prefs), encoding="utf-8")
    except OSError:
        pass
    return prefs


_SCAN_LOCK = threading.Lock()
_ERROR_CODES = {"bad_code", "need_server", "need_admin", "locked", "missing_files"}
_TRAY_TEXT = {"ru": ("Открыть", "Выход"), "am": ("Բացել", "Ելք"), "en": ("Open", "Exit")}
_UI_LANG = "ru"


def scan_computer() -> dict:
    """Full local snapshot with the agent's own collectors (no server needed)."""
    import time

    from collector.metrics import MetricsCollector

    with _SCAN_LOCK:
        collector = MetricsCollector()
        collector.establish_rate_baseline()
        time.sleep(1.0)  # окно для скорости сети и дисков
        return collector.collect().to_dict()


class _StatusHandler(BaseHTTPRequestHandler):
    """Serve the app page, live status, and the setup/install endpoint."""

    def _json(self, data: dict, code: int = 200) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802 - http.server naming
        if self.path.startswith("/status.json"):
            self._json(_read_status())
        elif self.path.startswith("/scan"):
            try:
                self._json({"ok": True, "snapshot": scan_computer()})
            except Exception as error:  # noqa: BLE001 - shown as «нет данных»
                self._json({"ok": False, "snapshot": None, "error": error.__class__.__name__}, 500)
        elif self.path.startswith("/state"):
            self._json({
                "installed": service_installed() and "--setup" not in sys.argv,
                "server_url": read_installed_server_url(),
            })
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            prefs = read_prefs()
            page = _HTML.replace('<html lang="ru">', f'<html lang="ru" data-theme="{prefs["theme"]}" '
                                                    f'data-lang="{prefs["lang"]}">', 1)
            self.wfile.write(page.encode("utf-8"))

    def do_POST(self) -> None:  # noqa: N802 - http.server naming
        if self.path.startswith("/lang"):
            global _UI_LANG
            length = int(self.headers.get("Content-Length", 0))
            value = self.rfile.read(length).decode("ascii", "ignore").strip()
            if value in _TRAY_TEXT:
                _UI_LANG = value
            self._json({"ok": True})
            return
        if self.path.startswith("/prefs"):
            # _UI_LANG объявлен global выше, в ветке /lang
            length = int(self.headers.get("Content-Length", 0))
            try:
                update = json.loads(self.rfile.read(length) or b"{}")
            except ValueError:
                update = {}
            prefs = save_prefs(update if isinstance(update, dict) else {})
            _UI_LANG = prefs["lang"]
            self._json(prefs)
            return
        if self.path.startswith("/setup/reconnect"):
            # Повторная установка поверх старой: перезапуск с правами админа в режиме ввода кода.
            self._json({"ok": True})
            if getattr(sys, "frozen", False):
                ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, "--setup", None, 1)
                threading.Timer(0.5, lambda: os._exit(0)).start()
            return
        if not self.path.startswith("/setup/install"):
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
            pairing_code, packed_url = parse_connection_code(str(payload.get("pairing_code", "")))
            server_url = packed_url or str(payload.get("server_url", "")).strip()
            if not server_url:
                raise ValueError("need_server")
            if not server_url.startswith(("http://", "https://")):
                server_url = "http://" + server_url
            install_service(server_url, pairing_code)
            self._json({"ok": True})
        except Exception as error:  # noqa: BLE001 - surfaced to the user
            message = str(error)
            if message in _ERROR_CODES:
                self._json({"ok": False, "code": message}, 400)
            else:
                self._json({"ok": False, "code": "install_failed",
                            "error": f"{error.__class__.__name__}: {error}"}, 500)

    def log_message(self, *args) -> None:  # keep the console clean
        pass


def start_server() -> ThreadingHTTPServer:
    """Bind the local status server, walking the port range if busy."""
    last_error: Exception | None = None
    # На Windows SO_REUSEADDR даёт второму экземпляру тот же порт — запросы уходят не в то окно.
    ThreadingHTTPServer.allow_reuse_address = False
    for port in PORT_RANGE:
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), _StatusHandler)
        except OSError as error:
            last_error = error
            continue
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server
    raise RuntimeError(f"Unable to bind the status server: {last_error}")


def _tray_image(connected: bool):
    """User app tray icon: monitor base + colored status dot (green/red)."""
    from PIL import Image, ImageDraw

    candidates = [
        Path(getattr(sys, "_MEIPASS", CONFIG_DIR)) / "icon-user.png",
        CONFIG_DIR / "icon-user.png",
        CONFIG_DIR.parent / "branding" / "icon-user.png",
    ]
    base = None
    for candidate in candidates:
        try:
            base = Image.open(candidate).convert("RGBA").resize((64, 64))
            break
        except OSError:
            continue
    if base is None:
        base = Image.new("RGBA", (64, 64), (7, 12, 28, 255))
        draw = ImageDraw.Draw(base)
        draw.ellipse((12, 12, 52, 52), fill=(95, 211, 160, 255) if connected else (17, 34, 51, 255))
    color = (95, 211, 160, 255) if connected else (255, 77, 109, 255)
    draw = ImageDraw.Draw(base)
    draw.ellipse((44, 44, 62, 62), fill=color, outline=(7, 12, 28, 255), width=2)
    return base


def _run_tray(stop: threading.Event, url: str) -> None:
    import pystray

    def on_open(_, item):
        for window in webview.windows:
            window.show()

    def on_exit(_, item):
        stop.set()
        os._exit(0)

    icon = pystray.Icon(
        "MonitoringAgentApp",
        _tray_image(_read_status().get("connected", False)),
        APP_NAME,
        menu=pystray.Menu(
            pystray.MenuItem(lambda item: _TRAY_TEXT[_UI_LANG][0], on_open, default=True),
            pystray.MenuItem(lambda item: _TRAY_TEXT[_UI_LANG][1], on_exit),
        ),
    )

    def _updater():
        """Repaint the tray dot as the connection state changes."""
        last = None
        while not stop.is_set():
            connected = bool(_read_status().get("connected"))
            if connected != last:
                icon.icon = _tray_image(connected)
                last = connected
            stop.wait(3)

    threading.Thread(target=_updater, daemon=True).start()
    icon.run(setup=lambda i: setattr(i, "visible", True))


def main() -> None:
    # Первый запуск (до установки службы): UAC для прав админа.
    # После установки служба сама стартует с Windows и уже имеет права —
    # повторные UAC-запросы при каждом открытии приложения не нужны.
    needs_setup = not service_installed() or "--setup" in sys.argv
    if getattr(sys, "frozen", False) and needs_setup and not is_admin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv[1:]), None, 1
        )
        return
    server = start_server()
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    stop = threading.Event()
    threading.Thread(target=_run_tray, args=(stop, url), daemon=True).start()
    webview.create_window(APP_NAME, url, width=WINDOW_SIZE[0], height=WINDOW_SIZE[1], min_size=(380, 560))
    webview.start()


if __name__ == "__main__":
    main()
