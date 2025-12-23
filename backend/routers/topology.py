"""
Topology Router - Network topology visualization.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from backend.core.database import get_db
from backend.core.security import get_current_active_user
from backend import models

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/topology", tags=["Topology"])


@router.get("")
def get_topology(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get network topology data for visualization."""
    if current_user.role != "admin" and not current_user.permissions.get("topology"):
        raise HTTPException(status_code=403, detail="Permission denied")

    subnets = db.query(models.Subnet).all()

    nodes = []
    edges = []

    # Add internet node
    nodes.append({
        "id": "internet",
        "label": "Internet",
        "group": "internet",
        "shape": "cloud"
    })

    for subnet in subnets:
        subnet_node_id = f"subnet_{subnet.id}"

        # Add subnet node
        nodes.append({
            "id": subnet_node_id,
            "label": f"{subnet.name}\n{subnet.cidr}",
            "group": "subnet",
            "shape": "box"
        })

        # Connect subnet to internet
        edges.append({"from": "internet", "to": subnet_node_id})

        # Add IP nodes
        for ip in subnet.ips:
            ip_node_id = f"ip_{ip.id}"
            label = str(ip.address)
            if ip.hostname:
                label += f"\n({ip.hostname})"

            color = "#10b981" if ip.status == "active" else "#64748b"

            nodes.append({
                "id": ip_node_id,
                "label": label,
                "group": "ip",
                "shape": "dot",
                "color": color
            })

            # Connect IP to subnet
            edges.append({"from": subnet_node_id, "to": ip_node_id})

    return {"nodes": nodes, "edges": edges}
