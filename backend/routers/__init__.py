# API Routers
from backend.routers.auth import router as auth_router
from backend.routers.users import router as users_router
from backend.routers.ipam import router as ipam_router
from backend.routers.topology import router as topology_router
from backend.routers.scripts import router as scripts_router
from backend.routers.inventory import router as inventory_router
from backend.routers.dashboard import router as dashboard_router
from backend.routers.dcim import router as dcim_router
from backend.routers.contracts import router as contracts_router
from backend.routers.software import router as software_router
from backend.routers.network_ports import router as network_ports_router
from backend.routers.attachments import router as attachments_router
from backend.routers.entities import router as entities_router

__all__ = [
    "auth_router",
    "users_router",
    "ipam_router",
    "topology_router",
    "scripts_router",
    "inventory_router",
    "dashboard_router",
    "dcim_router",
    "contracts_router",
    "software_router",
    "network_ports_router",
    "attachments_router",
    "entities_router",
]
