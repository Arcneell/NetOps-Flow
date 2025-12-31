"""
Network Ports Router - Physical connectivity and patching management.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import logging

from backend.core.database import get_db
from backend.core.security import get_current_active_user, has_permission
from backend import models, schemas

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/network-ports", tags=["Network Ports"])


def check_network_permission(current_user: models.User):
    """Check if user has network_ports permission (tech with network_ports, admin, superadmin)."""
    if not has_permission(current_user, "network_ports"):
        raise HTTPException(status_code=403, detail="Permission denied")


# ==================== NETWORK PORTS ====================

@router.get("/", response_model=List[schemas.NetworkPortFull])
def list_network_ports(
    equipment_id: int = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """List network ports, optionally filtered by equipment."""
    check_network_permission(current_user)

    query = db.query(models.NetworkPort)

    if equipment_id:
        query = query.filter(models.NetworkPort.equipment_id == equipment_id)

    return query.order_by(
        models.NetworkPort.equipment_id,
        models.NetworkPort.name
    ).offset(skip).limit(limit).all()


@router.get("/equipment/{equipment_id}", response_model=List[schemas.NetworkPortFull])
def get_equipment_ports(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get all ports for an equipment."""
    check_network_permission(current_user)

    equipment = db.query(models.Equipment).filter(
        models.Equipment.id == equipment_id
    ).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    return db.query(models.NetworkPort).filter(
        models.NetworkPort.equipment_id == equipment_id
    ).order_by(models.NetworkPort.name).all()


@router.get("/{port_id}", response_model=schemas.NetworkPortFull)
def get_network_port(
    port_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get a specific network port."""
    check_network_permission(current_user)

    port = db.query(models.NetworkPort).filter(
        models.NetworkPort.id == port_id
    ).first()
    if not port:
        raise HTTPException(status_code=404, detail="Network port not found")

    return port


@router.post("/", response_model=schemas.NetworkPort)
def create_network_port(
    port: schemas.NetworkPortCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Create a new network port."""
    check_network_permission(current_user)

    # Verify equipment exists
    equipment = db.query(models.Equipment).filter(
        models.Equipment.id == port.equipment_id
    ).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    # Check for duplicate port name on equipment
    existing = db.query(models.NetworkPort).filter(
        models.NetworkPort.equipment_id == port.equipment_id,
        models.NetworkPort.name == port.name
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Port name already exists on this equipment"
        )

    db_port = models.NetworkPort(**port.model_dump())
    db.add(db_port)
    db.commit()
    db.refresh(db_port)

    logger.info(
        f"Port '{port.name}' created on '{equipment.name}' "
        f"by '{current_user.username}'"
    )
    return db_port


@router.put("/{port_id}", response_model=schemas.NetworkPort)
def update_network_port(
    port_id: int,
    port: schemas.NetworkPortCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Update a network port."""
    check_network_permission(current_user)

    db_port = db.query(models.NetworkPort).filter(
        models.NetworkPort.id == port_id
    ).first()
    if not db_port:
        raise HTTPException(status_code=404, detail="Network port not found")

    for key, value in port.model_dump().items():
        setattr(db_port, key, value)

    db.commit()
    db.refresh(db_port)
    return db_port


@router.delete("/{port_id}")
def delete_network_port(
    port_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Delete a network port."""
    check_network_permission(current_user)

    db_port = db.query(models.NetworkPort).filter(
        models.NetworkPort.id == port_id
    ).first()
    if not db_port:
        raise HTTPException(status_code=404, detail="Network port not found")

    # Clear any connections pointing to this port
    db.query(models.NetworkPort).filter(
        models.NetworkPort.connected_to_id == port_id
    ).update({"connected_to_id": None})

    db.delete(db_port)
    db.commit()

    return {"ok": True}


# ==================== PORT CONNECTIONS (PATCHING) ====================

@router.post("/{port_id}/connect/{target_port_id}")
def connect_ports(
    port_id: int,
    target_port_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Connect two network ports (bidirectional)."""
    check_network_permission(current_user)

    if port_id == target_port_id:
        raise HTTPException(status_code=400, detail="Cannot connect port to itself")

    source_port = db.query(models.NetworkPort).filter(
        models.NetworkPort.id == port_id
    ).first()
    if not source_port:
        raise HTTPException(status_code=404, detail="Source port not found")

    target_port = db.query(models.NetworkPort).filter(
        models.NetworkPort.id == target_port_id
    ).first()
    if not target_port:
        raise HTTPException(status_code=404, detail="Target port not found")

    # Check if ports are already connected elsewhere
    if source_port.connected_to_id and source_port.connected_to_id != target_port_id:
        raise HTTPException(
            status_code=400,
            detail="Source port is already connected to another port"
        )
    if target_port.connected_to_id and target_port.connected_to_id != port_id:
        raise HTTPException(
            status_code=400,
            detail="Target port is already connected to another port"
        )

    # Create bidirectional connection
    source_port.connected_to_id = target_port_id
    target_port.connected_to_id = port_id

    db.commit()

    source_eq = db.query(models.Equipment).filter(
        models.Equipment.id == source_port.equipment_id
    ).first()
    target_eq = db.query(models.Equipment).filter(
        models.Equipment.id == target_port.equipment_id
    ).first()

    logger.info(
        f"Connected {source_eq.name}:{source_port.name} <-> "
        f"{target_eq.name}:{target_port.name} by '{current_user.username}'"
    )

    return {
        "ok": True,
        "connection": {
            "source": {"equipment": source_eq.name, "port": source_port.name},
            "target": {"equipment": target_eq.name, "port": target_port.name}
        }
    }


@router.delete("/{port_id}/disconnect")
def disconnect_port(
    port_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Disconnect a port from its connection."""
    check_network_permission(current_user)

    port = db.query(models.NetworkPort).filter(
        models.NetworkPort.id == port_id
    ).first()
    if not port:
        raise HTTPException(status_code=404, detail="Port not found")

    if not port.connected_to_id:
        raise HTTPException(status_code=400, detail="Port is not connected")

    # Get the other end
    target_port = db.query(models.NetworkPort).filter(
        models.NetworkPort.id == port.connected_to_id
    ).first()

    # Clear both ends
    port.connected_to_id = None
    if target_port:
        target_port.connected_to_id = None

    db.commit()

    logger.info(f"Port {port_id} disconnected by '{current_user.username}'")

    return {"ok": True}


@router.get("/connections/all")
def get_all_connections(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get all port connections for topology visualization."""
    check_network_permission(current_user)

    # Get ports that have connections
    connected_ports = db.query(models.NetworkPort).filter(
        models.NetworkPort.connected_to_id.isnot(None)
    ).all()

    connections = []
    seen = set()

    for port in connected_ports:
        # Avoid duplicates (since connections are bidirectional)
        connection_key = tuple(sorted([port.id, port.connected_to_id]))
        if connection_key in seen:
            continue
        seen.add(connection_key)

        source_eq = db.query(models.Equipment).filter(
            models.Equipment.id == port.equipment_id
        ).first()

        target_port = db.query(models.NetworkPort).filter(
            models.NetworkPort.id == port.connected_to_id
        ).first()

        if target_port:
            target_eq = db.query(models.Equipment).filter(
                models.Equipment.id == target_port.equipment_id
            ).first()

            connections.append({
                "source": {
                    "port_id": port.id,
                    "port_name": port.name,
                    "equipment_id": source_eq.id if source_eq else None,
                    "equipment_name": source_eq.name if source_eq else None
                },
                "target": {
                    "port_id": target_port.id,
                    "port_name": target_port.name,
                    "equipment_id": target_eq.id if target_eq else None,
                    "equipment_name": target_eq.name if target_eq else None
                }
            })

    return {"connections": connections}
