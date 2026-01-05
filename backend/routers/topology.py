"""
Topology Router - Network topology visualization with physical connectivity.
With Redis caching for performance optimization.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
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


def check_topology_permission(current_user: models.User):
    """Check if user has topology permission (tech with topology, admin, superadmin)."""
    if not has_permission(current_user, "topology"):
        raise HTTPException(status_code=403, detail="Permission denied")


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
        "label": "Gateway",
        "type": "gateway",
        "icon": "pi-globe",
        "color": "#6366f1",
        "size": 50
    })

    for subnet in subnets:
        subnet_node_id = f"subnet_{subnet.id}"

        # Count IPs by status
        active_count = sum(1 for ip in subnet.ips if ip.status == "active")
        total_count = len(subnet.ips)

        nodes.append({
            "id": subnet_node_id,
            "label": subnet.name or subnet.cidr,
            "sublabel": str(subnet.cidr),
            "type": "subnet",
            "icon": "pi-sitemap",
            "color": "#3b82f6",
            "size": 40,
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
            "animated": True
        })

        # Add IP nodes
        for ip in subnet.ips:
            ip_node_id = f"ip_{ip.id}"

            # Determine color based on status
            color_map = {
                "active": "#10b981",
                "reserved": "#f59e0b",
                "available": "#6b7280"
            }
            color = color_map.get(ip.status, "#6b7280")

            nodes.append({
                "id": ip_node_id,
                "label": str(ip.address),
                "sublabel": ip.hostname or ip.status,
                "type": "ip",
                "icon": "pi-circle-fill",
                "color": color,
                "size": 20,
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
                "type": "contains"
            })

    result = {"nodes": nodes, "edges": edges}
    cache_set(cache_key, result, TOPOLOGY_CACHE_TTL)
    return result


@router.get("/physical")
def get_physical_topology(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get physical network topology (equipment and port connections)."""
    check_topology_permission(current_user)

    cache_key = build_cache_key("topology", "physical")
    cached_data = cache_get(cache_key)
    if cached_data:
        return cached_data

    nodes = []
    edges = []
    equipment_ids = set()
    equipment_by_rack = {}  # Group equipment by rack
    equipment_by_location = {}  # Group equipment by location (no rack)
    connected_equipment = set()  # Track equipment with port connections

    # Get all equipment with network ports
    equipment_list = db.query(models.Equipment).options(
        joinedload(models.Equipment.model).joinedload(models.EquipmentModel.equipment_type),
        joinedload(models.Equipment.model).joinedload(models.EquipmentModel.manufacturer),
        joinedload(models.Equipment.network_ports),
        joinedload(models.Equipment.location),
        joinedload(models.Equipment.rack)
    ).filter(
        models.Equipment.status.in_(["in_service", "maintenance"])
    ).all()

    # Icon mapping for equipment types
    icon_map = {
        "pi-server": "pi-server",
        "pi-desktop": "pi-desktop",
        "pi-sitemap": "pi-sitemap",
        "pi-share-alt": "pi-share-alt",
        "pi-wifi": "pi-wifi",
        "pi-database": "pi-database",
        "pi-shield": "pi-shield",
        "pi-bolt": "pi-bolt"
    }

    # Status color mapping
    status_colors = {
        "in_service": "#10b981",
        "maintenance": "#f59e0b",
        "in_stock": "#6b7280",
        "retired": "#ef4444"
    }

    for eq in equipment_list:
        equipment_ids.add(eq.id)

        # Group by rack or location
        if eq.rack_id:
            if eq.rack_id not in equipment_by_rack:
                equipment_by_rack[eq.rack_id] = {"rack": eq.rack, "equipment": []}
            equipment_by_rack[eq.rack_id]["equipment"].append(eq)
        elif eq.location_id:
            if eq.location_id not in equipment_by_location:
                equipment_by_location[eq.location_id] = {"location": eq.location, "equipment": []}
            equipment_by_location[eq.location_id]["equipment"].append(eq)

        # Get equipment type info
        eq_type_name = "Unknown"
        icon = "pi-box"
        if eq.model and eq.model.equipment_type:
            eq_type_name = eq.model.equipment_type.name
            icon = icon_map.get(eq.model.equipment_type.icon, "pi-box")

        # Get location info
        location_str = ""
        if eq.location:
            parts = [eq.location.site]
            if eq.location.building:
                parts.append(eq.location.building)
            if eq.location.room:
                parts.append(eq.location.room)
            location_str = " > ".join(parts)

        # Count ports
        port_connected = sum(1 for p in eq.network_ports if p.connected_to_id)
        total_ports = len(eq.network_ports)

        nodes.append({
            "id": f"equipment_{eq.id}",
            "label": eq.name,
            "sublabel": eq_type_name,
            "type": "equipment",
            "equipmentType": eq_type_name.lower().replace(" ", "_"),
            "icon": icon,
            "color": status_colors.get(eq.status, "#6b7280"),
            "size": 30,
            "rackId": eq.rack_id,
            "locationId": eq.location_id,
            "data": {
                "id": eq.id,
                "name": eq.name,
                "status": eq.status,
                "type": eq_type_name,
                "manufacturer": eq.model.manufacturer.name if eq.model and eq.model.manufacturer else None,
                "model": eq.model.name if eq.model else None,
                "location": location_str,
                "rack": eq.rack.name if eq.rack else None,
                "position_u": eq.position_u,
                "serial_number": eq.serial_number,
                "ip_address": eq.remote_ip,
                "ports_connected": port_connected,
                "ports_total": total_ports
            }
        })

    # Get all port connections
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

        # Track connected equipment
        connected_equipment.add(port.equipment_id)
        connected_equipment.add(target_port.equipment_id)

        # Avoid duplicate connections
        connection_key = tuple(sorted([port.id, port.connected_to_id]))
        if connection_key in seen_connections:
            continue
        seen_connections.add(connection_key)

        # Determine edge style based on port type
        edge_style = "solid"
        if port.port_type == "fiber":
            edge_style = "dashed"

        # Determine edge color based on speed
        edge_color = "#94a3b8"
        if port.speed:
            speed_colors = {
                "100M": "#94a3b8",
                "1G": "#3b82f6",
                "10G": "#8b5cf6",
                "25G": "#ec4899",
                "40G": "#f59e0b",
                "100G": "#10b981"
            }
            edge_color = speed_colors.get(port.speed, "#94a3b8")

        edges.append({
            "id": f"edge_{port.id}_{target_port.id}",
            "source": f"equipment_{port.equipment_id}",
            "target": f"equipment_{target_port.equipment_id}",
            "type": "connection",
            "style": edge_style,
            "color": edge_color,
            "label": port.speed or "",
            "data": {
                "source_port": port.name,
                "target_port": target_port.name,
                "port_type": port.port_type,
                "speed": port.speed
            }
        })

    # Add rack nodes and connect equipment to their racks
    for rack_id, rack_data in equipment_by_rack.items():
        rack = rack_data["rack"]
        rack_node_id = f"rack_{rack_id}"

        # Add rack node
        nodes.append({
            "id": rack_node_id,
            "label": rack.name,
            "sublabel": f"{rack.height_u}U",
            "type": "rack",
            "icon": "pi-server",
            "color": "#8b5cf6",
            "size": 45,
            "data": {
                "id": rack.id,
                "name": rack.name,
                "total_u": rack.height_u,
                "equipment_count": len(rack_data["equipment"])
            }
        })

        # Connect unconnected equipment to their rack
        for eq in rack_data["equipment"]:
            if eq.id not in connected_equipment:
                edges.append({
                    "id": f"edge_rack_{rack_id}_eq_{eq.id}",
                    "source": rack_node_id,
                    "target": f"equipment_{eq.id}",
                    "type": "placement",
                    "style": "dotted",
                    "color": "#8b5cf680",
                    "data": {
                        "relationship": "housed_in",
                        "position_u": eq.position_u
                    }
                })

    # Add location nodes for equipment without racks
    for loc_id, loc_data in equipment_by_location.items():
        location = loc_data["location"]
        loc_node_id = f"location_{loc_id}"

        # Only add location node if it has unconnected equipment
        unconnected_in_loc = [eq for eq in loc_data["equipment"] if eq.id not in connected_equipment]
        if unconnected_in_loc:
            loc_name = location.site
            if location.room:
                loc_name = f"{location.site} - {location.room}"

            nodes.append({
                "id": loc_node_id,
                "label": loc_name,
                "sublabel": "Location",
                "type": "location",
                "icon": "pi-building",
                "color": "#06b6d4",
                "size": 40,
                "data": {
                    "id": location.id,
                    "site": location.site,
                    "building": location.building,
                    "room": location.room,
                    "equipment_count": len(loc_data["equipment"])
                }
            })

            # Connect unconnected equipment to their location
            for eq in unconnected_in_loc:
                edges.append({
                    "id": f"edge_loc_{loc_id}_eq_{eq.id}",
                    "source": loc_node_id,
                    "target": f"equipment_{eq.id}",
                    "type": "placement",
                    "style": "dotted",
                    "color": "#06b6d480",
                    "data": {
                        "relationship": "located_at"
                    }
                })

    result = {"nodes": nodes, "edges": edges}
    cache_set(cache_key, result, TOPOLOGY_CACHE_TTL)
    return result


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

    for ip in ip_equipment_map:
        edges.append({
            "id": f"edge_ip_{ip.id}_eq_{ip.equipment_id}",
            "source": f"ip_{ip.id}",
            "target": f"equipment_{ip.equipment_id}",
            "type": "assigned",
            "style": "dotted",
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
        "sublabel": f"{rack.total_u}U",
        "type": "rack",
        "icon": "pi-server",
        "color": "#8b5cf6",
        "size": 50,
        "data": {
            "id": rack.id,
            "name": rack.name,
            "total_u": rack.total_u
        }
    })

    equipment_ids = set()
    status_colors = {
        "in_service": "#10b981",
        "maintenance": "#f59e0b",
        "in_stock": "#6b7280",
        "retired": "#ef4444"
    }

    for eq in equipment_list:
        equipment_ids.add(eq.id)

        eq_type_name = "Unknown"
        if eq.model and eq.model.equipment_type:
            eq_type_name = eq.model.equipment_type.name

        nodes.append({
            "id": f"equipment_{eq.id}",
            "label": eq.name,
            "sublabel": f"U{eq.position_u or '?'} - {eq_type_name}",
            "type": "equipment",
            "icon": "pi-box",
            "color": status_colors.get(eq.status, "#6b7280"),
            "size": 30,
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
            "type": "placement"
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
                            "label": port.name,
                            "color": "#10b981"
                        })

    return {
        "rack": {
            "id": rack.id,
            "name": rack.name,
            "total_u": rack.total_u
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
