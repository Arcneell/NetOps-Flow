"""
Topology Router - Network topology visualization with physical connectivity.
With Redis caching for performance optimization.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import Optional
import logging

from backend.core.database import get_db
from backend.core.security import get_current_active_user, has_permission
from backend.core.cache import cache_get, cache_set, build_cache_key
from backend import models

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/topology", tags=["Topology"])

# Cache expiration in seconds (5 minutes)
TOPOLOGY_CACHE_TTL = 300

# Equipment type hierarchy for network layout
NETWORK_LAYERS = {
    "core": ["router", "core switch", "core router", "backbone"],
    "distribution": ["switch", "distribution switch", "layer 3 switch", "firewall"],
    "access": ["access switch", "access point", "wifi"],
    "endpoint": ["server", "storage", "workstation", "desktop", "laptop", "printer"]
}

# Icons for equipment types
EQUIPMENT_ICONS = {
    "server": "server",
    "switch": "switch",
    "router": "router",
    "firewall": "firewall",
    "storage": "storage",
    "access point": "wifi",
    "workstation": "desktop",
    "desktop": "desktop",
    "laptop": "laptop"
}

# Colors for equipment types (professional network diagram colors)
EQUIPMENT_COLORS = {
    "router": "#7c3aed",      # Purple - Core
    "core switch": "#7c3aed",
    "switch": "#2563eb",      # Blue - Distribution/Access
    "firewall": "#dc2626",    # Red - Security
    "server": "#059669",      # Green - Servers
    "storage": "#0891b2",     # Cyan - Storage
    "access point": "#f59e0b", # Amber - Wireless
    "workstation": "#64748b",  # Slate - Endpoints
    "desktop": "#64748b",
    "default": "#6b7280"
}


def check_topology_permission(current_user: models.User):
    """Check if user has topology permission (tech with topology, admin, superadmin)."""
    if not has_permission(current_user, "topology"):
        raise HTTPException(status_code=403, detail="Permission denied")


def get_equipment_layer(equipment_type: str) -> str:
    """Determine network layer based on equipment type."""
    eq_type_lower = equipment_type.lower() if equipment_type else ""
    for layer, types in NETWORK_LAYERS.items():
        if any(t in eq_type_lower for t in types):
            return layer
    return "endpoint"


def get_equipment_color(equipment_type: str) -> str:
    """Get color for equipment type."""
    eq_type_lower = equipment_type.lower() if equipment_type else ""
    for type_name, color in EQUIPMENT_COLORS.items():
        if type_name in eq_type_lower:
            return color
    return EQUIPMENT_COLORS["default"]


@router.get("/stats")
def get_topology_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get topology statistics for dashboard widgets."""
    check_topology_permission(current_user)

    # Cache key
    cache_key = build_cache_key("topology", "stats")
    cached_data = cache_get(cache_key)
    if cached_data:
        return cached_data

    # Count subnets
    subnets_count = db.query(models.Subnet).count()

    # Count IPs by status
    ips_total = db.query(models.IPAddress).count()
    ips_active = db.query(models.IPAddress).filter(models.IPAddress.status == "active").count()
    ips_reserved = db.query(models.IPAddress).filter(models.IPAddress.status == "reserved").count()

    # Count equipment by status
    equipment_total = db.query(models.Equipment).count()
    equipment_active = db.query(models.Equipment).filter(models.Equipment.status == "in_service").count()

    # Count network ports and connections
    ports_total = db.query(models.NetworkPort).count()
    ports_connected = db.query(models.NetworkPort).filter(
        models.NetworkPort.connected_to_id.isnot(None)
    ).count()

    # Count equipment types
    equipment_by_type = {}
    equipment_types = db.query(models.EquipmentType).all()
    for eq_type in equipment_types:
        count = db.query(models.Equipment).join(models.EquipmentModel).filter(
            models.EquipmentModel.equipment_type_id == eq_type.id
        ).count()
        if count > 0:
            equipment_by_type[eq_type.name] = count

    result = {
        "subnets": subnets_count,
        "ips": {
            "total": ips_total,
            "active": ips_active,
            "reserved": ips_reserved,
            "available": ips_total - ips_active - ips_reserved
        },
        "equipment": {
            "total": equipment_total,
            "active": equipment_active,
            "by_type": equipment_by_type
        },
        "ports": {
            "total": ports_total,
            "connected": ports_connected,
            "unconnected": ports_total - ports_connected
        }
    }

    cache_set(cache_key, result, TOPOLOGY_CACHE_TTL)
    return result


@router.get("/logical")
def get_logical_topology(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get logical network topology (subnets and IPs)."""
    check_topology_permission(current_user)

    cache_key = build_cache_key("topology", "logical")
    cached_data = cache_get(cache_key)
    if cached_data:
        return cached_data

    subnets = db.query(models.Subnet).options(
        joinedload(models.Subnet.ips)
    ).all()

    nodes = []
    edges = []

    # Add internet/gateway node as center
    nodes.append({
        "id": "gateway",
        "label": "Internet",
        "type": "gateway",
        "shape": "diamond",
        "color": "#6366f1",
        "size": 50,
        "level": 0,
        "data": {}
    })

    for subnet in subnets:
        subnet_node_id = f"subnet_{subnet.id}"

        # Count IPs by status
        active_count = sum(1 for ip in subnet.ips if ip.status == "active")
        total_count = len(subnet.ips)

        nodes.append({
            "id": subnet_node_id,
            "label": subnet.name or str(subnet.cidr),
            "sublabel": str(subnet.cidr),
            "type": "subnet",
            "shape": "box",
            "color": "#3b82f6",
            "size": 35,
            "level": 1,
            "data": {
                "id": subnet.id,
                "cidr": str(subnet.cidr),
                "name": subnet.name,
                "description": subnet.description,
                "ips_active": active_count,
                "ips_total": total_count
            }
        })

        # Connect to gateway
        edges.append({
            "id": f"edge_gateway_{subnet_node_id}",
            "source": "gateway",
            "target": subnet_node_id,
            "type": "network",
            "width": 3,
            "color": "#6366f1"
        })

        # Only add active IPs (not all IPs to avoid clutter)
        for ip in subnet.ips:
            if ip.status != "active":
                continue

            ip_node_id = f"ip_{ip.id}"

            nodes.append({
                "id": ip_node_id,
                "label": str(ip.address),
                "sublabel": ip.hostname or "",
                "type": "ip",
                "shape": "dot",
                "color": "#10b981",
                "size": 15,
                "level": 2,
                "data": {
                    "id": ip.id,
                    "address": str(ip.address),
                    "hostname": ip.hostname,
                    "status": ip.status,
                    "mac_address": ip.mac_address,
                    "equipment_id": ip.equipment_id
                }
            })

            edges.append({
                "id": f"edge_{subnet_node_id}_{ip_node_id}",
                "source": subnet_node_id,
                "target": ip_node_id,
                "type": "contains",
                "width": 1,
                "color": "#94a3b8"
            })

    result = {"nodes": nodes, "edges": edges}
    cache_set(cache_key, result, TOPOLOGY_CACHE_TTL)
    return result


@router.get("/physical")
def get_physical_topology(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get physical network topology - equipment connected by ports."""
    check_topology_permission(current_user)

    cache_key = build_cache_key("topology", "physical")
    cached_data = cache_get(cache_key)
    if cached_data:
        return cached_data

    nodes = []
    edges = []
    equipment_ids = set()
    equipment_map = {}  # id -> equipment data
    connected_equipment = set()

    # Get all equipment with network ports that have connections
    equipment_list = db.query(models.Equipment).options(
        joinedload(models.Equipment.model).joinedload(models.EquipmentModel.equipment_type),
        joinedload(models.Equipment.model).joinedload(models.EquipmentModel.manufacturer),
        joinedload(models.Equipment.network_ports),
        joinedload(models.Equipment.location)
    ).filter(
        models.Equipment.status.in_(["in_service", "maintenance"])
    ).all()

    # Build equipment map
    for eq in equipment_list:
        equipment_ids.add(eq.id)
        eq_type_name = eq.model.equipment_type.name if eq.model and eq.model.equipment_type else "Unknown"
        equipment_map[eq.id] = {
            "equipment": eq,
            "type": eq_type_name,
            "layer": get_equipment_layer(eq_type_name),
            "color": get_equipment_color(eq_type_name),
            "has_connections": False
        }

    # Find all port connections and mark connected equipment
    port_connections = db.query(models.NetworkPort).filter(
        models.NetworkPort.connected_to_id.isnot(None),
        models.NetworkPort.equipment_id.in_(equipment_ids)
    ).all()

    seen_connections = set()

    for port in port_connections:
        target_port = db.query(models.NetworkPort).filter(
            models.NetworkPort.id == port.connected_to_id
        ).first()

        if not target_port or target_port.equipment_id not in equipment_ids:
            continue

        # Mark both as connected
        connected_equipment.add(port.equipment_id)
        connected_equipment.add(target_port.equipment_id)
        equipment_map[port.equipment_id]["has_connections"] = True
        equipment_map[target_port.equipment_id]["has_connections"] = True

        # Avoid duplicate connections
        connection_key = tuple(sorted([port.id, port.connected_to_id]))
        if connection_key in seen_connections:
            continue
        seen_connections.add(connection_key)

        # Determine edge color based on speed
        speed = port.speed or ""
        if "100G" in speed:
            edge_color = "#10b981"
            edge_width = 5
        elif "40G" in speed or "25G" in speed:
            edge_color = "#8b5cf6"
            edge_width = 4
        elif "10G" in speed:
            edge_color = "#3b82f6"
            edge_width = 3
        elif "1G" in speed:
            edge_color = "#64748b"
            edge_width = 2
        else:
            edge_color = "#94a3b8"
            edge_width = 1

        # Edge label shows port names
        edge_label = f"{port.name} ↔ {target_port.name}"

        edges.append({
            "id": f"edge_{port.id}_{target_port.id}",
            "source": f"equipment_{port.equipment_id}",
            "target": f"equipment_{target_port.equipment_id}",
            "type": "connection",
            "width": edge_width,
            "color": edge_color,
            "label": port.speed or "",
            "dashes": port.port_type == "fiber",
            "data": {
                "source_port": port.name,
                "target_port": target_port.name,
                "port_type": port.port_type,
                "speed": port.speed
            }
        })

    # Assign levels based on network layer
    layer_levels = {"core": 0, "distribution": 1, "access": 2, "endpoint": 3}

    # Create nodes - only for equipment with connections
    for eq_id, eq_data in equipment_map.items():
        if not eq_data["has_connections"]:
            continue

        eq = eq_data["equipment"]
        eq_type = eq_data["type"]
        layer = eq_data["layer"]
        color = eq_data["color"]

        # Get location info
        location_str = ""
        if eq.location:
            parts = [eq.location.site]
            if eq.location.room:
                parts.append(eq.location.room)
            location_str = " / ".join(parts)

        # Count ports
        port_connected = sum(1 for p in eq.network_ports if p.connected_to_id)
        total_ports = len(eq.network_ports)

        # Determine shape based on type
        if "router" in eq_type.lower():
            shape = "diamond"
        elif "switch" in eq_type.lower():
            shape = "box"
        elif "firewall" in eq_type.lower():
            shape = "hexagon"
        elif "server" in eq_type.lower():
            shape = "box"
        else:
            shape = "ellipse"

        nodes.append({
            "id": f"equipment_{eq.id}",
            "label": eq.name,
            "sublabel": eq_type,
            "type": "equipment",
            "equipmentType": eq_type.lower().replace(" ", "_"),
            "shape": shape,
            "color": color,
            "size": 35 if layer in ["core", "distribution"] else 25,
            "level": layer_levels.get(layer, 3),
            "layer": layer,
            "data": {
                "id": eq.id,
                "name": eq.name,
                "status": eq.status,
                "type": eq_type,
                "manufacturer": eq.model.manufacturer.name if eq.model and eq.model.manufacturer else None,
                "model": eq.model.name if eq.model else None,
                "location": location_str,
                "serial_number": eq.serial_number,
                "ip_address": eq.remote_ip,
                "ports_connected": port_connected,
                "ports_total": total_ports
            }
        })

    result = {"nodes": nodes, "edges": edges}
    cache_set(cache_key, result, TOPOLOGY_CACHE_TTL)
    return result


@router.get("/site/{site_name}")
def get_site_topology(
    site_name: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get topology for a specific site."""
    check_topology_permission(current_user)

    # Get locations for this site
    locations = db.query(models.Location).filter(
        models.Location.site == site_name
    ).all()

    if not locations:
        raise HTTPException(status_code=404, detail="Site not found")

    location_ids = [loc.id for loc in locations]

    # Get equipment at these locations
    equipment_list = db.query(models.Equipment).options(
        joinedload(models.Equipment.model).joinedload(models.EquipmentModel.equipment_type),
        joinedload(models.Equipment.network_ports),
        joinedload(models.Equipment.location)
    ).filter(
        models.Equipment.location_id.in_(location_ids),
        models.Equipment.status.in_(["in_service", "maintenance"])
    ).all()

    nodes = []
    edges = []
    equipment_ids = set(eq.id for eq in equipment_list)

    # Group by room
    rooms = {}
    for eq in equipment_list:
        room = eq.location.room if eq.location else "Unknown"
        if room not in rooms:
            rooms[room] = []
        rooms[room].append(eq)

    layer_levels = {"core": 0, "distribution": 1, "access": 2, "endpoint": 3}

    for eq in equipment_list:
        eq_type = eq.model.equipment_type.name if eq.model and eq.model.equipment_type else "Unknown"
        layer = get_equipment_layer(eq_type)
        color = get_equipment_color(eq_type)

        port_connected = sum(1 for p in eq.network_ports if p.connected_to_id)

        nodes.append({
            "id": f"equipment_{eq.id}",
            "label": eq.name,
            "sublabel": eq_type,
            "type": "equipment",
            "shape": "box",
            "color": color,
            "size": 30,
            "level": layer_levels.get(layer, 3),
            "group": eq.location.room if eq.location else "Unknown",
            "data": {
                "id": eq.id,
                "name": eq.name,
                "type": eq_type,
                "room": eq.location.room if eq.location else None,
                "ports_connected": port_connected
            }
        })

        # Add connections
        for port in eq.network_ports:
            if port.connected_to_id:
                target_port = db.query(models.NetworkPort).filter(
                    models.NetworkPort.id == port.connected_to_id
                ).first()

                if target_port and target_port.equipment_id in equipment_ids:
                    edge_key = tuple(sorted([eq.id, target_port.equipment_id]))
                    edge_id = f"conn_{edge_key[0]}_{edge_key[1]}"

                    if not any(e.get("id") == edge_id for e in edges):
                        edges.append({
                            "id": edge_id,
                            "source": f"equipment_{eq.id}",
                            "target": f"equipment_{target_port.equipment_id}",
                            "type": "connection",
                            "label": port.speed or "",
                            "width": 2,
                            "color": "#64748b"
                        })

    return {
        "site": site_name,
        "rooms": list(rooms.keys()),
        "nodes": nodes,
        "edges": edges
    }


@router.get("/sites")
def get_topology_sites(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get list of sites with equipment counts for topology."""
    check_topology_permission(current_user)

    sites = db.query(
        models.Location.site,
        func.count(models.Equipment.id).label("equipment_count")
    ).join(
        models.Equipment,
        models.Equipment.location_id == models.Location.id
    ).filter(
        models.Equipment.status.in_(["in_service", "maintenance"])
    ).group_by(models.Location.site).all()

    return [
        {"name": site, "equipment_count": count}
        for site, count in sites
    ]


@router.get("/combined")
def get_combined_topology(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get combined logical and physical topology."""
    check_topology_permission(current_user)

    cache_key = build_cache_key("topology", "combined")
    cached_data = cache_get(cache_key)
    if cached_data:
        return cached_data

    # Get both topologies
    logical = get_logical_topology.__wrapped__(db=db, current_user=current_user)
    physical = get_physical_topology.__wrapped__(db=db, current_user=current_user)

    # Merge nodes and edges
    nodes = logical["nodes"] + physical["nodes"]
    edges = logical["edges"] + physical["edges"]

    # Add connections between IPs and equipment
    ip_equipment_map = db.query(models.IPAddress).filter(
        models.IPAddress.equipment_id.isnot(None)
    ).all()

    # Get set of equipment node IDs
    equipment_node_ids = {n["id"] for n in physical["nodes"]}

    for ip in ip_equipment_map:
        eq_node_id = f"equipment_{ip.equipment_id}"
        if eq_node_id in equipment_node_ids:
            edges.append({
                "id": f"edge_ip_{ip.id}_eq_{ip.equipment_id}",
                "source": f"ip_{ip.id}",
                "target": eq_node_id,
                "type": "assigned",
                "dashes": True,
                "width": 1,
                "color": "#8b5cf6"
            })

    result = {"nodes": nodes, "edges": edges}
    cache_set(cache_key, result, TOPOLOGY_CACHE_TTL)
    return result


@router.get("/rack/{rack_id}")
def get_rack_topology(
    rack_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get topology for equipment within a specific rack."""
    check_topology_permission(current_user)

    rack = db.query(models.Rack).filter(models.Rack.id == rack_id).first()
    if not rack:
        raise HTTPException(status_code=404, detail="Rack not found")

    equipment_list = db.query(models.Equipment).options(
        joinedload(models.Equipment.model).joinedload(models.EquipmentModel.equipment_type),
        joinedload(models.Equipment.network_ports)
    ).filter(
        models.Equipment.rack_id == rack_id
    ).all()

    nodes = []
    edges = []

    # Add rack as central node
    nodes.append({
        "id": f"rack_{rack.id}",
        "label": rack.name,
        "sublabel": f"{rack.height_u}U",
        "type": "rack",
        "shape": "box",
        "color": "#8b5cf6",
        "size": 50,
        "level": 0,
        "data": {
            "id": rack.id,
            "name": rack.name,
            "height_u": rack.height_u
        }
    })

    equipment_ids = set()

    for eq in equipment_list:
        equipment_ids.add(eq.id)

        eq_type_name = eq.model.equipment_type.name if eq.model and eq.model.equipment_type else "Unknown"
        color = get_equipment_color(eq_type_name)

        nodes.append({
            "id": f"equipment_{eq.id}",
            "label": eq.name,
            "sublabel": f"U{eq.position_u or '?'} - {eq_type_name}",
            "type": "equipment",
            "shape": "box",
            "color": color,
            "size": 30,
            "level": 1,
            "data": {
                "id": eq.id,
                "name": eq.name,
                "position_u": eq.position_u,
                "height_u": eq.height_u,
                "status": eq.status,
                "type": eq_type_name
            }
        })

        edges.append({
            "id": f"edge_rack_{rack.id}_eq_{eq.id}",
            "source": f"rack_{rack.id}",
            "target": f"equipment_{eq.id}",
            "type": "placement",
            "dashes": True,
            "width": 1,
            "color": "#8b5cf680"
        })

    # Add connections between equipment in rack
    for eq in equipment_list:
        for port in eq.network_ports:
            if port.connected_to_id:
                target_port = db.query(models.NetworkPort).filter(
                    models.NetworkPort.id == port.connected_to_id
                ).first()

                if target_port and target_port.equipment_id in equipment_ids:
                    edge_key = tuple(sorted([eq.id, target_port.equipment_id]))
                    edge_id = f"conn_{edge_key[0]}_{edge_key[1]}"

                    if not any(e.get("id") == edge_id for e in edges):
                        edges.append({
                            "id": edge_id,
                            "source": f"equipment_{eq.id}",
                            "target": f"equipment_{target_port.equipment_id}",
                            "type": "connection",
                            "label": port.speed or "",
                            "width": 2,
                            "color": "#10b981"
                        })

    return {
        "rack": {
            "id": rack.id,
            "name": rack.name,
            "height_u": rack.height_u
        },
        "nodes": nodes,
        "edges": edges
    }


# Keep legacy endpoint for backward compatibility
@router.get("")
def get_topology(
    include_physical: bool = Query(False, description="Include physical port connections"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Legacy endpoint - redirects to logical or combined topology."""
    if include_physical:
        return get_combined_topology(db=db, current_user=current_user)
    return get_logical_topology(db=db, current_user=current_user)
