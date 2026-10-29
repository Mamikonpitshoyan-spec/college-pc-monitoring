"""HTML dashboard pages served from Jinja2 templates."""

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.auth import require_admin_page  # noqa: E402
from app.api.monitoring import current_ui_prefs

router = APIRouter(tags=["pages"], dependencies=[Depends(require_admin_page)])

_TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
templates.env.globals["ui_prefs"] = current_ui_prefs


def _page(request: Request, template: str, page_name: str, **context) -> HTMLResponse:
    context.setdefault("page_name", page_name)
    return templates.TemplateResponse(request, template, context)


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard_page(request: Request) -> HTMLResponse:
    """Admin dashboard with the live device table."""
    return _page(request, "dashboard.html", "dashboard")


@router.get("/devices", response_class=HTMLResponse, include_in_schema=False)
def devices_page(request: Request) -> HTMLResponse:
    """Device management page: the full table with row controls."""
    return _page(request, "devices.html", "devices")


@router.get("/devices/{device_id}", response_class=HTMLResponse, include_in_schema=False)
def device_page(request: Request, device_id: int) -> HTMLResponse:
    """Full scanned-parameter view for one device."""
    return _page(request, "device.html", "device", device_id=device_id)


@router.get("/alerts", response_class=HTMLResponse, include_in_schema=False)
def alerts_page(request: Request) -> HTMLResponse:
    """Alert list (open and resolved)."""
    return _page(request, "alerts.html", "alerts")


@router.get("/events", response_class=HTMLResponse, include_in_schema=False)
def events_page(request: Request) -> HTMLResponse:
    """Event log."""
    return _page(request, "events.html", "events")


@router.get("/analytics", response_class=HTMLResponse, include_in_schema=False)
def analytics_page(request: Request) -> HTMLResponse:
    """Metric history charts per device."""
    return _page(request, "analytics.html", "analytics")


@router.get("/settings", response_class=HTMLResponse, include_in_schema=False)
def settings_page(request: Request) -> HTMLResponse:
    """System thresholds and configuration summary."""
    return _page(request, "settings.html", "settings")
