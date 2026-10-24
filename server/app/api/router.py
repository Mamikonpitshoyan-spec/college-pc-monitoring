"""Top-level HTTP route composition."""

from fastapi import APIRouter, Depends

from app.api.auth import require_admin_api

from app.api.agent import router as agent_router
from app.api.auth import router as auth_router
from app.api.devices import router as devices_router
from app.api.download import router as download_router
from app.api.monitoring import router as monitoring_router
from app.api.pairing import router as pairing_router

api_router = APIRouter()
api_router.include_router(agent_router)
api_router.include_router(auth_router)
api_router.include_router(devices_router, dependencies=[Depends(require_admin_api)])
api_router.include_router(monitoring_router, dependencies=[Depends(require_admin_api)])
api_router.include_router(pairing_router)
api_router.include_router(download_router)


@api_router.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Return server-process health without aggregating device health."""
    return {"status": "ok", "stage": "9"}
