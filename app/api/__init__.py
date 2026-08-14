from app.api.health import router as health_router
from app.api.readings import router as readings_router
from app.api.status import router as status_router

__all__ = ["health_router", "readings_router", "status_router"]
