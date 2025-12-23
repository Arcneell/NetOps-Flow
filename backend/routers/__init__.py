# API Routers
from backend.routers.auth import router as auth_router
from backend.routers.users import router as users_router
from backend.routers.ipam import router as ipam_router
from backend.routers.topology import router as topology_router
from backend.routers.scripts import router as scripts_router
from backend.routers.inventory import router as inventory_router
from backend.routers.dashboard import router as dashboard_router

__all__ = [
    "auth_router",
    "users_router",
    "ipam_router",
    "topology_router",
    "scripts_router",
    "inventory_router",
    "dashboard_router",
]
