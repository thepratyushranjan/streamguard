# Routes module
from api.routes.root import router as root_router
from api.routes.health import router as health_router
from api.routes.events import router as events_router
from api.routes.vector import router as vector_router
from api.routes.system_health import router as system_health_router

__all__ = [
    "root_router",
    "health_router",
    "events_router",
    "vector_router",
    "system_health_router",
]
