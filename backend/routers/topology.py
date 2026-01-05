"""
Topology Router - Network topology visualization.
Shows all equipment organized by location/rack, with port connections as links.
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

TOPOLOGY_CACHE_TTL = 300

# Colors by equipment type
TYPE_COLORS = {
    "router": "#7c3aed",
    "switch": "#2563eb",
    "firewall": "#dc2626",
    "server": "#059669",
    "storage": "#0891b2",
    "access point": "#f59e0b",
    "workstation": "#64748b",
    "pdu": "#78716c",
    "ups": "#a855f7",
}

# Colors by status
STATUS_COLORS = {
    "in_service": "#10b981",
    "maintenance": "#f59e0b",
    "in_stock": "#64748b",
    "retired": "#ef4444",
}


def check_topology_permission(current_user: models.User):
    if not has_permission(current_user, "topology"):
        raise HTTPException(status_code=403, detail="Permission denied")


def get_type_color(eq_type: str) -> str:
    """Get color based on equipment type."""
    if not eq_type:
        return "#6b7280"
    eq_type_lower = eq_type.lower()
    for key, color in TYPE_COLORS.items():
        if key in eq_type_lower:
            return color
    return "#6b7280"


@router.get("/stats")
def get_topology_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get topology statistics."""
    check_topology_permission(current_user)

    cache_key = build_cache_key("topology", "stats")
    cached = cache_get(cache_key)
    if cached:
        return cached

    result = {
        "subnets": db.query(models.Subnet).count(),
        "ips": {
            "total": db.query(models.IPAddress).count(),
            "active": db.query(models.IPAddress).filter(models.IPAddress.status == "active").count(),
            "reserved": db.query(models.IPAddress).filter(models.IPAddress.status == "reserved").count(),
        },
        "equipment": {
            "total": db.query(models.Equipment).count(),
            "active": db.query(models.Equipment).filter(models.Equipment.status == "in_service").count(),
        },
        "ports": {
            "total": db.query(models.NetworkPort).count(),
            "connected": db.query(models.NetworkPort).filter(models.NetworkPort.connected_to_id.isnot(None)).count(),
        },
        "sites": db.query(func.count(func.distinct(models.Location.site))).scalar() or 0,
        "racks": db.query(models.Rack).count(),
    }
    result["ips"]["available"] = result["ips"]["total"] - result["ips"]["active"] - result["ips"]["reserved"]
    result["ports"]["unconnected"] = result["ports"]["total"] - result["ports"]["connected"]

    cache_set(cache_key, result, TOPOLOGY_CACHE_TTL)
    return result


@router.get("/logical")
def get_logical_topology(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Logical topology: Subnets and their active IPs."""
    check_topology_permission(current_user)

    cache_key = build_cache_key("topology", "logical")
    cached = cache_get(cache_key)
    if cached:
        return cached

    subnets = db.query(models.Subnet).options(joinedload(models.Subnet.ips)).all()

    nodes = [{
        "id": "internet",
        "label": "Internet",
        "type": "gateway",
        "shape": "diamond",
        "color": "#6366f1",
        "size": 45,
    }]
    edges = []

    for subnet in subnets:
        subnet_id = f"subnet_{subnet.id}"
        active_ips = [ip for ip in subnet.ips if ip.status == "active"]

        nodes.append({
            "id": subnet_id,
            "label": subnet.name or str(subnet.cidr),
            "sublabel": str(subnet.cidr),
            "type": "subnet",
            "shape": "box",
            "color": "#3b82f6",
            "size": 35,
            "data": {
                "id": subnet.id,
                "cidr": str(subnet.cidr),
                "name": subnet.name,
                "active_ips": len(active_ips),
                "total_ips": len(subnet.ips),
            }
        })

        edges.append({
            "id": f"internet_to_{subnet_id}",
            "source": "internet",
            "target": subnet_id,
            "color": "#6366f1",
            "width": 2,
        })

        # Show only active IPs
        for ip in active_ips:
            ip_id = f"ip_{ip.id}"
            nodes.append({
                "id": ip_id,
                "label": str(ip.address),
                "sublabel": ip.hostname or "",
                "type": "ip",
                "shape": "dot",
                "color": "#10b981",
                "size": 12,
                "data": {
                    "id": ip.id,
                    "address": str(ip.address),
                    "hostname": ip.hostname,
                    "status": ip.status,
                }
            })
            edges.append({
                "id": f"{subnet_id}_to_{ip_id}",
                "source": subnet_id,
                "target": ip_id,
                "color": "#94a3b8",
                "width": 1,
            })

    result = {"nodes": nodes, "edges": edges}
    cache_set(cache_key, result, TOPOLOGY_CACHE_TTL)
    return result


@router.get("/physical")
def get_physical_topology(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Physical topology: All equipment grouped by site/location.
    Shows all equipment, with port connections as links between them.
    """
    check_topology_permission(current_user)

    cache_key = build_cache_key("topology", "physical")
    cached = cache_get(cache_key)
    if cached:
        return cached

    # Get all active equipment
    equipment_list = db.query(models.Equipment).options(
        joinedload(models.Equipment.model).joinedload(models.EquipmentModel.equipment_type),
        joinedload(models.Equipment.model).joinedload(models.EquipmentModel.manufacturer),
        joinedload(models.Equipment.network_ports),
        joinedload(models.Equipment.location),
        joinedload(models.Equipment.rack)
    ).filter(
        models.Equipment.status.in_(["in_service", "maintenance"])
    ).all()

    if not equipment_list:
        return {"nodes": [], "edges": [], "groups": []}

    nodes = []
    edges = []
    equipment_ids = set()

    # Group equipment by site
    sites = {}
    for eq in equipment_list:
        equipment_ids.add(eq.id)
        site_name = eq.location.site if eq.location else "Unassigned"
        if site_name not in sites:
            sites[site_name] = []
        sites[site_name].append(eq)

    # Create nodes for each equipment
    for eq in equipment_list:
        eq_type = eq.model.equipment_type.name if eq.model and eq.model.equipment_type else "Unknown"
        site_name = eq.location.site if eq.location else "Unassigned"
        room = eq.location.room if eq.location else None

        # Count port connections
        connected_ports = sum(1 for p in eq.network_ports if p.connected_to_id)
        total_ports = len(eq.network_ports)

        nodes.append({
            "id": f"eq_{eq.id}",
            "label": eq.name,
            "sublabel": eq_type,
            "type": "equipment",
            "equipmentType": eq_type.lower().replace(" ", "_"),
            "shape": "box",
            "color": get_type_color(eq_type),
            "borderColor": STATUS_COLORS.get(eq.status, "#6b7280"),
            "size": 30,
            "group": site_name,
            "data": {
                "id": eq.id,
                "name": eq.name,
                "type": eq_type,
                "status": eq.status,
                "manufacturer": eq.model.manufacturer.name if eq.model and eq.model.manufacturer else None,
                "model": eq.model.name if eq.model else None,
                "site": site_name,
                "room": room,
                "rack": eq.rack.name if eq.rack else None,
                "position_u": eq.position_u,
                "ip_address": eq.remote_ip,
                "serial_number": eq.serial_number,
                "ports_connected": connected_ports,
                "ports_total": total_ports,
            }
        })

    # Create edges for port connections
    seen_connections = set()
    for eq in equipment_list:
        for port in eq.network_ports:
            if not port.connected_to_id:
                continue

            # Avoid duplicate edges
            conn_key = tuple(sorted([port.id, port.connected_to_id]))
            if conn_key in seen_connections:
                continue
            seen_connections.add(conn_key)

            # Find target port and equipment
            target_port = db.query(models.NetworkPort).filter(
                models.NetworkPort.id == port.connected_to_id
            ).first()

            if not target_port or target_port.equipment_id not in equipment_ids:
                continue

            # Edge styling based on speed
            speed = port.speed or ""
            if "100G" in speed:
                width, color = 5, "#10b981"
            elif "40G" in speed or "25G" in speed:
                width, color = 4, "#8b5cf6"
            elif "10G" in speed:
                width, color = 3, "#3b82f6"
            elif "1G" in speed:
                width, color = 2, "#64748b"
            else:
                width, color = 1, "#94a3b8"

            edges.append({
                "id": f"conn_{port.id}_{target_port.id}",
                "source": f"eq_{port.equipment_id}",
                "target": f"eq_{target_port.equipment_id}",
                "label": speed,
                "color": color,
                "width": width,
                "dashes": port.port_type == "fiber",
                "data": {
                    "source_port": port.name,
                    "target_port": target_port.name,
                    "port_type": port.port_type,
                    "speed": speed,
                }
            })

    # Create groups for clustering
    groups = [{"id": site, "label": site, "count": len(eqs)} for site, eqs in sites.items()]

    result = {"nodes": nodes, "edges": edges, "groups": groups}
    cache_set(cache_key, result, TOPOLOGY_CACHE_TTL)
    return result


@router.get("/sites")
def get_sites(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get list of sites with equipment counts."""
    check_topology_permission(current_user)

    sites = db.query(
        models.Location.site,
        func.count(models.Equipment.id).label("count")
    ).join(
        models.Equipment, models.Equipment.location_id == models.Location.id
    ).filter(
        models.Equipment.status.in_(["in_service", "maintenance"])
    ).group_by(models.Location.site).all()

    return [{"name": site, "equipment_count": count} for site, count in sites]


@router.get("/site/{site_name}")
def get_site_topology(
    site_name: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get topology for a specific site."""
    check_topology_permission(current_user)

    locations = db.query(models.Location).filter(models.Location.site == site_name).all()
    if not locations:
        raise HTTPException(status_code=404, detail="Site not found")

    location_ids = [loc.id for loc in locations]

    equipment_list = db.query(models.Equipment).options(
        joinedload(models.Equipment.model).joinedload(models.EquipmentModel.equipment_type),
        joinedload(models.Equipment.network_ports),
        joinedload(models.Equipment.location),
        joinedload(models.Equipment.rack)
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

    for eq in equipment_list:
        eq_type = eq.model.equipment_type.name if eq.model and eq.model.equipment_type else "Unknown"
        room = eq.location.room if eq.location else "Unknown"

        nodes.append({
            "id": f"eq_{eq.id}",
            "label": eq.name,
            "sublabel": eq_type,
            "type": "equipment",
            "shape": "box",
            "color": get_type_color(eq_type),
            "size": 28,
            "group": room,
            "data": {
                "id": eq.id,
                "name": eq.name,
                "type": eq_type,
                "status": eq.status,
                "room": room,
                "rack": eq.rack.name if eq.rack else None,
            }
        })

        # Port connections
        for port in eq.network_ports:
            if port.connected_to_id:
                target_port = db.query(models.NetworkPort).filter(
                    models.NetworkPort.id == port.connected_to_id
                ).first()

                if target_port and target_port.equipment_id in equipment_ids:
                    edge_key = tuple(sorted([eq.id, target_port.equipment_id]))
                    edge_id = f"conn_{edge_key[0]}_{edge_key[1]}"

                    if not any(e["id"] == edge_id for e in edges):
                        edges.append({
                            "id": edge_id,
                            "source": f"eq_{eq.id}",
                            "target": f"eq_{target_port.equipment_id}",
                            "label": port.speed or "",
                            "color": "#64748b",
                            "width": 2,
                        })

    groups = [{"id": room, "label": room, "count": len(eqs)} for room, eqs in rooms.items()]

    return {"site": site_name, "nodes": nodes, "edges": edges, "groups": groups}


@router.get("/combined")
def get_combined_topology(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Combined logical + physical topology."""
    check_topology_permission(current_user)

    cache_key = build_cache_key("topology", "combined")
    cached = cache_get(cache_key)
    if cached:
        return cached

    logical = get_logical_topology.__wrapped__(db=db, current_user=current_user)
    physical = get_physical_topology.__wrapped__(db=db, current_user=current_user)

    nodes = logical["nodes"] + physical["nodes"]
    edges = logical["edges"] + physical["edges"]

    # Link IPs to equipment
    ip_equipment = db.query(models.IPAddress).filter(
        models.IPAddress.equipment_id.isnot(None)
    ).all()

    physical_eq_ids = {n["id"] for n in physical["nodes"]}

    for ip in ip_equipment:
        eq_id = f"eq_{ip.equipment_id}"
        if eq_id in physical_eq_ids:
            edges.append({
                "id": f"ip_{ip.id}_to_{eq_id}",
                "source": f"ip_{ip.id}",
                "target": eq_id,
                "color": "#8b5cf6",
                "width": 1,
                "dashes": True,
            })

    result = {"nodes": nodes, "edges": edges, "groups": physical.get("groups", [])}
    cache_set(cache_key, result, TOPOLOGY_CACHE_TTL)
    return result


@router.get("")
def get_topology_legacy(
    include_physical: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Legacy endpoint."""
    if include_physical:
        return get_combined_topology(db=db, current_user=current_user)
    return get_logical_topology(db=db, current_user=current_user)
