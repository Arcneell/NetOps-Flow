"""
Topology Router - Network topology visualization with physical connectivity.
With Redis caching for performance optimization.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
import logging

from backend.core.database import get_db
from backend.core.security import get_current_active_user
from backend.core.cache import cache_get, cache_set, build_cache_key
from backend import models

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/topology", tags=["Topology"])

# Cache expiration in seconds (5 minutes)
TOPOLOGY_CACHE_TTL = 300


@router.get("")
def get_topology(
    include_physical: bool = Query(False, description="Include physical port connections"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get network topology data for visualization with caching."""
    if current_user.role != "admin" and not current_user.permissions.get("topology"):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Try to get from cache first
    cache_key = build_cache_key("topology", "network", include_physical=include_physical)
    cached_data = cache_get(cache_key)
    if cached_data:
        return cached_data

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

    # Include physical connections if requested
    if include_physical:
        physical_data = _get_physical_topology(db)
        nodes.extend(physical_data["nodes"])
        edges.extend(physical_data["edges"])

    result = {"nodes": nodes, "edges": edges}

    # Cache the result
    cache_set(cache_key, result, TOPOLOGY_CACHE_TTL)

    return result


@router.get("/physical")
def get_physical_topology(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get physical network topology (equipment and port connections) with caching."""
    if current_user.role != "admin" and not current_user.permissions.get("topology"):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Try to get from cache first
    cache_key = build_cache_key("topology", "physical")
    cached_data = cache_get(cache_key)
    if cached_data:
        return cached_data

    result = _get_physical_topology(db)

    # Cache the result
    cache_set(cache_key, result, TOPOLOGY_CACHE_TTL)

    return result


def _get_physical_topology(db: Session):
    """Build physical topology data from equipment and port connections."""
    nodes = []
    edges = []
    equipment_ids = set()

    # Get all network ports with connections
    connected_ports = db.query(models.NetworkPort).filter(
        models.NetworkPort.connected_to_id.isnot(None)
    ).all()

    seen_connections = set()

    for port in connected_ports:
        # Add source equipment node
        source_eq = db.query(models.Equipment).filter(
            models.Equipment.id == port.equipment_id
        ).first()

        if source_eq and source_eq.id not in equipment_ids:
            equipment_ids.add(source_eq.id)

            # Get equipment type icon
            icon = "server"
            if source_eq.model and source_eq.model.equipment_type:
                icon_map = {
                    "pi-server": "server",
                    "pi-desktop": "desktop",
                    "pi-sitemap": "switch",
                    "pi-wifi": "router",
                    "pi-database": "database"
                }
                icon = icon_map.get(source_eq.model.equipment_type.icon, "box")

            nodes.append({
                "id": f"equipment_{source_eq.id}",
                "label": source_eq.name,
                "group": "equipment",
                "shape": "box",
                "icon": icon,
                "color": "#3b82f6" if source_eq.status == "in_service" else "#6b7280"
            })

        # Add target equipment node
        target_port = db.query(models.NetworkPort).filter(
            models.NetworkPort.id == port.connected_to_id
        ).first()

        if target_port:
            target_eq = db.query(models.Equipment).filter(
                models.Equipment.id == target_port.equipment_id
            ).first()

            if target_eq and target_eq.id not in equipment_ids:
                equipment_ids.add(target_eq.id)

                icon = "server"
                if target_eq.model and target_eq.model.equipment_type:
                    icon_map = {
                        "pi-server": "server",
                        "pi-desktop": "desktop",
                        "pi-sitemap": "switch",
                        "pi-wifi": "router",
                        "pi-database": "database"
                    }
                    icon = icon_map.get(target_eq.model.equipment_type.icon, "box")

                nodes.append({
                    "id": f"equipment_{target_eq.id}",
                    "label": target_eq.name,
                    "group": "equipment",
                    "shape": "box",
                    "icon": icon,
                    "color": "#3b82f6" if target_eq.status == "in_service" else "#6b7280"
                })

            # Add edge (avoid duplicates)
            connection_key = tuple(sorted([port.id, port.connected_to_id]))
            if connection_key not in seen_connections:
                seen_connections.add(connection_key)

                edge_label = f"{port.name} <-> {target_port.name}"
                if port.speed:
                    edge_label += f"\n({port.speed})"

                edges.append({
                    "from": f"equipment_{port.equipment_id}",
                    "to": f"equipment_{target_port.equipment_id}",
                    "label": edge_label,
                    "group": "physical",
                    "dashes": port.port_type == "fiber"
                })

    return {"nodes": nodes, "edges": edges}


@router.get("/rack/{rack_id}")
def get_rack_topology(
    rack_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get topology for equipment within a specific rack."""
    if current_user.role != "admin" and not current_user.permissions.get("topology"):
        raise HTTPException(status_code=403, detail="Permission denied")

    rack = db.query(models.Rack).filter(models.Rack.id == rack_id).first()
    if not rack:
        raise HTTPException(status_code=404, detail="Rack not found")

    # Get equipment in rack
    equipment_list = db.query(models.Equipment).filter(
        models.Equipment.rack_id == rack_id
    ).all()

    nodes = []
    edges = []

    # Add rack as central node
    nodes.append({
        "id": f"rack_{rack.id}",
        "label": rack.name,
        "group": "rack",
        "shape": "box",
        "color": "#8b5cf6"
    })

    equipment_ids = set()

    for eq in equipment_list:
        equipment_ids.add(eq.id)
        nodes.append({
            "id": f"equipment_{eq.id}",
            "label": f"{eq.name}\nU{eq.position_u or '?'}",
            "group": "equipment",
            "shape": "box",
            "color": "#3b82f6" if eq.status == "in_service" else "#6b7280"
        })

        edges.append({
            "from": f"rack_{rack.id}",
            "to": f"equipment_{eq.id}",
            "group": "placement"
        })

    # Add connections between equipment in rack
    for eq in equipment_list:
        ports = db.query(models.NetworkPort).filter(
            models.NetworkPort.equipment_id == eq.id,
            models.NetworkPort.connected_to_id.isnot(None)
        ).all()

        for port in ports:
            target_port = db.query(models.NetworkPort).filter(
                models.NetworkPort.id == port.connected_to_id
            ).first()

            if target_port and target_port.equipment_id in equipment_ids:
                edge_key = tuple(sorted([eq.id, target_port.equipment_id]))
                edge_id = f"conn_{edge_key[0]}_{edge_key[1]}"

                if not any(e.get("id") == edge_id for e in edges):
                    edges.append({
                        "id": edge_id,
                        "from": f"equipment_{eq.id}",
                        "to": f"equipment_{target_port.equipment_id}",
                        "label": f"{port.name}",
                        "group": "physical",
                        "color": "#10b981"
                    })

    return {"rack": rack.name, "nodes": nodes, "edges": edges}
