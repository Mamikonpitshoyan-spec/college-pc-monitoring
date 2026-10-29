"""Administrator login and first-run password setup pages."""

from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates

from app.database.session import get_db
from app.services import admin_auth
from app.services.agent_service import utc_now

router = APIRouter(tags=["auth"])

_SESSION_COOKIE = admin_auth.SESSION_COOKIE
_templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))
_templates.env.globals["ui_prefs"] = __import__("app.api.monitoring", fromlist=["x"]).current_ui_prefs


def require_admin_page(request: Request, database: Session = Depends(get_db)):
    """Page dependency: redirects to /login when the session cookie is absent."""
    if not admin_auth.is_password_set(database):
        # Первый запуск: сначала создаётся пароль администратора.
        raise HTTPException(status_code=302, headers={"Location": "/setup"})
    if admin_auth.session_valid(database, request.cookies.get(_SESSION_COOKIE)):
        return None
    # FastAPI отбрасывает значения из dependencies=[...] — редирект бросаем.
    raise HTTPException(status_code=302, headers={"Location": "/login"})


def require_admin_api(request: Request, database: Session = Depends(get_db)):
    """API dependency: 401 JSON when the session cookie is absent."""
    if admin_auth.session_valid(database, request.cookies.get(_SESSION_COOKIE)):
        return None
    raise HTTPException(status_code=401, detail="Administrator login required.")


def _no_password_guard(database: Session):
    """First run: no password yet → send to /setup. Already set → /login."""
    if not admin_auth.is_password_set(database):
        return RedirectResponse("/setup", status_code=302)
    return None


@router.get("/login", include_in_schema=False)
def login_page(request: Request, database: Session = Depends(get_db)):
    guard = _no_password_guard(database)
    if guard:
        return guard
    return _templates.TemplateResponse(request, "login.html", {"is_setup": False, "error": request.query_params.get("error")})


@router.post("/login", include_in_schema=False)
def login_submit(
    database: Session = Depends(get_db),
    password: str = Form(default=""),
):
    if admin_auth.verify_password(database, password):
        token = admin_auth.create_session(database)
        response = RedirectResponse("/", status_code=302)
        response.set_cookie(_SESSION_COOKIE, token, max_age=30 * 24 * 3600, httponly=True, samesite="lax")
        return response
    return RedirectResponse("/login?error=1", status_code=302)


@router.get("/setup", include_in_schema=False)
def setup_page(request: Request, database: Session = Depends(get_db)):
    if admin_auth.is_password_set(database):
        return RedirectResponse("/login", status_code=302)
    return _templates.TemplateResponse(request, "setup.html", {"is_setup": True, "error": request.query_params.get("error")})


@router.post("/setup", include_in_schema=False)
def setup_submit(
    database: Session = Depends(get_db),
    password: str = Form(default=""),
    confirm: str = Form(default=""),
):
    if len(password) < 4 or password != confirm:
        return RedirectResponse("/setup?error=1", status_code=302)
    admin_auth.set_password(database, password)
    token = admin_auth.create_session(database)
    response = RedirectResponse("/", status_code=302)
    response.set_cookie(_SESSION_COOKIE, token, max_age=30 * 24 * 3600, httponly=True, samesite="lax")
    return response


@router.get("/logout", include_in_schema=False)
def logout(database: Session = Depends(get_db)):
    admin_auth.destroy_session(database, None)
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie(_SESSION_COOKIE)
    return response
