"""
DCIM Router - Rack and PDU management for datacenter infrastructure.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
import logging

from backend.core.database import get_db
from backend.core.security import get_current_active_user, get_current_admin_user
from backend import models, schemas

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dcim", tags=["DCIM"])


def check_dcim_permission(current_user: models.User):
    """Check if user has DCIM/inventory permission."""
    if current_user.role != "admin" and not current_user.permissions.get("inventory"):
        raise HTTPException(status_code=403, detail="Permission denied")


def get_user_entity_filter(current_user: models.User):
    """Get entity filter for multi-tenant queries."""
    if current_user.role == "admin" and not current_user.entity_id:
        return None  # Admin without entity sees all
    return current_user.entity_id


# ==================== RACKS ====================

@router.get("/racks/", response_model=List[schemas.RackFull])
def list_racks(
    location_id: int = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """List all racks, optionally filtered by location."""
    check_dcim_permission(current_user)

    query = db.query(models.Rack)

    entity_filter = get_user_entity_filter(current_user)
    if entity_filter:
        query = query.filter(models.Rack.entity_id == entity_filter)

    if location_id:
        query = query.filter(models.Rack.location_id == location_id)

    return query.order_by(models.Rack.name).all()


@router.get("/racks/{rack_id}", response_model=schemas.RackFull)
def get_rack(
    rack_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get a specific rack with its equipment."""
    check_dcim_permission(current_user)

    rack = db.query(models.Rack).filter(models.Rack.id == rack_id).first()
    if not rack:
        raise HTTPException(status_code=404, detail="Rack not found")

    entity_filter = get_user_entity_filter(current_user)
    if entity_filter and rack.entity_id != entity_filter:
        raise HTTPException(status_code=403, detail="Access denied to this rack")

    return rack


@router.get("/racks/{rack_id}/layout", response_model=schemas.RackLayoutResponse)
def get_rack_layout(
    rack_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get rack layout showing equipment placement with full details."""
    check_dcim_permission(current_user)

    rack = db.query(models.Rack).filter(models.Rack.id == rack_id).first()
    if not rack:
        raise HTTPException(status_code=404, detail="Rack not found")

    # Get equipment in this rack with optimized joins
    equipment = db.query(models.Equipment).options(
        joinedload(models.Equipment.model).joinedload(models.EquipmentModel.manufacturer),
        joinedload(models.Equipment.model).joinedload(models.EquipmentModel.equipment_type)
    ).filter(
        models.Equipment.rack_id == rack_id,
        models.Equipment.position_u.isnot(None)
    ).all()

    # Get unassigned equipment (rack_id set but position_u is null)
    unassigned = db.query(models.Equipment).options(
        joinedload(models.Equipment.model).joinedload(models.EquipmentModel.manufacturer),
        joinedload(models.Equipment.model).joinedload(models.EquipmentModel.equipment_type)
    ).filter(
        models.Equipment.rack_id == rack_id,
        models.Equipment.position_u.is_(None)
    ).all()

    # Get management IPs for equipment
    equipment_ips = {}
    for eq in equipment + unassigned:
        ip = db.query(models.IPAddress).filter(
            models.IPAddress.equipment_id == eq.id
        ).first()
        if ip:
            equipment_ips[eq.id] = ip.ip_address

    # Build layout with full details
    layout = []
    for u in range(1, rack.height_u + 1):
        slot = {"u": u, "equipment": None}
        for eq in equipment:
            if eq.position_u <= u < eq.position_u + eq.height_u:
                slot["equipment"] = {
                    "id": eq.id,
                    "name": eq.name,
                    "height_u": eq.height_u,
                    "is_start": eq.position_u == u,
                    "status": eq.status,
                    "serial_number": eq.serial_number,
                    "asset_tag": eq.asset_tag,
                    "model_name": eq.model.name if eq.model else None,
                    "manufacturer_name": eq.model.manufacturer.name if eq.model and eq.model.manufacturer else None,
                    "management_ip": equipment_ips.get(eq.id)
                }
                break
        layout.append(slot)

    # Build unassigned equipment list
    unassigned_list = []
    for eq in unassigned:
        unassigned_list.append({
            "id": eq.id,
            "name": eq.name,
            "height_u": eq.height_u,
            "status": eq.status,
            "serial_number": eq.serial_number,
            "asset_tag": eq.asset_tag,
            "model_name": eq.model.name if eq.model else None,
            "manufacturer_name": eq.model.manufacturer.name if eq.model and eq.model.manufacturer else None,
            "management_ip": equipment_ips.get(eq.id)
        })

    return {
        "rack": {
            "id": rack.id,
            "name": rack.name,
            "height_u": rack.height_u
        },
        "layout": layout,
        "pdus": [{"id": p.id, "name": p.name} for p in rack.pdus],
        "unassigned_equipment": unassigned_list
    }


@router.post("/racks/{rack_id}/place-equipment")
def place_equipment_in_rack(
    rack_id: int,
    equipment_id: int,
    position_u: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Place equipment in a specific position in the rack."""
    check_dcim_permission(current_user)

    # Verify rack exists
    rack = db.query(models.Rack).filter(models.Rack.id == rack_id).first()
    if not rack:
        raise HTTPException(status_code=404, detail="Rack not found")

    # Verify equipment exists
    equipment = db.query(models.Equipment).filter(models.Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    # Validate position
    if position_u < 1 or position_u > rack.height_u:
        raise HTTPException(status_code=400, detail=f"Position must be between 1 and {rack.height_u}")

    if equipment.height_u and (position_u + equipment.height_u - 1) > rack.height_u:
        raise HTTPException(
            status_code=400,
            detail=f"Equipment height ({equipment.height_u}U) exceeds rack capacity at position {position_u}"
        )

    # Check for conflicts with existing equipment
    existing = db.query(models.Equipment).filter(
        models.Equipment.rack_id == rack_id,
        models.Equipment.position_u.isnot(None)
    ).all()

    for eq in existing:
        if eq.id == equipment_id:
            continue
        # Check if ranges overlap
        eq_end = eq.position_u + eq.height_u - 1
        new_end = position_u + equipment.height_u - 1
        if not (new_end < eq.position_u or position_u > eq_end):
            raise HTTPException(
                status_code=400,
                detail=f"Position conflicts with {eq.name} at U{eq.position_u}"
            )

    # Update equipment
    equipment.rack_id = rack_id
    equipment.position_u = position_u
    db.commit()

    logger.info(f"Equipment '{equipment.name}' placed in rack '{rack.name}' at U{position_u} by '{current_user.username}'")
    return {"ok": True, "message": f"Equipment placed at U{position_u}"}


@router.post("/racks/", response_model=schemas.Rack)
def create_rack(
    rack: schemas.RackCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Create a new rack."""
    check_dcim_permission(current_user)

    # Verify location exists
    location = db.query(models.Location).filter(
        models.Location.id == rack.location_id
    ).first()
    if not location:
        raise HTTPException(status_code=400, detail="Location not found")

    rack_data = rack.model_dump()
    if not rack_data.get("entity_id") and current_user.entity_id:
        rack_data["entity_id"] = current_user.entity_id

    db_rack = models.Rack(**rack_data)
    db.add(db_rack)
    db.commit()
    db.refresh(db_rack)

    logger.info(f"Rack '{rack.name}' created by '{current_user.username}'")
    return db_rack


@router.put("/racks/{rack_id}", response_model=schemas.Rack)
def update_rack(
    rack_id: int,
    rack: schemas.RackCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Update a rack."""
    check_dcim_permission(current_user)

    db_rack = db.query(models.Rack).filter(models.Rack.id == rack_id).first()
    if not db_rack:
        raise HTTPException(status_code=404, detail="Rack not found")

    for key, value in rack.model_dump().items():
        setattr(db_rack, key, value)

    db.commit()
    db.refresh(db_rack)
    return db_rack


@router.delete("/racks/{rack_id}")
def delete_rack(
    rack_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Delete a rack (admin only)."""
    db_rack = db.query(models.Rack).filter(models.Rack.id == rack_id).first()
    if not db_rack:
        raise HTTPException(status_code=404, detail="Rack not found")

    # Check for equipment in rack
    equipment_count = db.query(models.Equipment).filter(
        models.Equipment.rack_id == rack_id
    ).count()
    if equipment_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete rack with {equipment_count} equipment items"
        )

    db.delete(db_rack)
    db.commit()

    logger.info(f"Rack '{db_rack.name}' deleted by '{current_user.username}'")
    return {"ok": True}


# ==================== PDUs ====================

@router.get("/pdus/", response_model=List[schemas.PDU])
def list_pdus(
    rack_id: int = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """List all PDUs, optionally filtered by rack."""
    check_dcim_permission(current_user)

    query = db.query(models.PDU)

    if rack_id:
        query = query.filter(models.PDU.rack_id == rack_id)

    return query.order_by(models.PDU.name).all()


@router.get("/pdus/{pdu_id}", response_model=schemas.PDU)
def get_pdu(
    pdu_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get a specific PDU."""
    check_dcim_permission(current_user)

    pdu = db.query(models.PDU).filter(models.PDU.id == pdu_id).first()
    if not pdu:
        raise HTTPException(status_code=404, detail="PDU not found")

    return pdu


@router.get("/pdus/{pdu_id}/ports")
def get_pdu_ports(
    pdu_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get PDU port allocation."""
    check_dcim_permission(current_user)

    pdu = db.query(models.PDU).filter(models.PDU.id == pdu_id).first()
    if not pdu:
        raise HTTPException(status_code=404, detail="PDU not found")

    # Get equipment connected to this PDU
    primary_equipment = db.query(models.Equipment).filter(
        models.Equipment.pdu_id == pdu_id
    ).all()

    redundant_equipment = db.query(models.Equipment).filter(
        models.Equipment.redundant_pdu_id == pdu_id
    ).all()

    ports = []
    for eq in primary_equipment:
        if eq.pdu_port:
            ports.append({
                "port": eq.pdu_port,
                "equipment_id": eq.id,
                "equipment_name": eq.name,
                "is_redundant": False
            })

    for eq in redundant_equipment:
        if eq.redundant_pdu_port:
            ports.append({
                "port": eq.redundant_pdu_port,
                "equipment_id": eq.id,
                "equipment_name": eq.name,
                "is_redundant": True
            })

    return {
        "pdu": {"id": pdu.id, "name": pdu.name, "total_ports": pdu.total_ports},
        "used_ports": len(ports),
        "ports": ports
    }


@router.post("/pdus/", response_model=schemas.PDU)
def create_pdu(
    pdu: schemas.PDUCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Create a new PDU."""
    check_dcim_permission(current_user)

    db_pdu = models.PDU(**pdu.model_dump())
    db.add(db_pdu)
    db.commit()
    db.refresh(db_pdu)

    logger.info(f"PDU '{pdu.name}' created by '{current_user.username}'")
    return db_pdu


@router.put("/pdus/{pdu_id}", response_model=schemas.PDU)
def update_pdu(
    pdu_id: int,
    pdu: schemas.PDUCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Update a PDU."""
    check_dcim_permission(current_user)

    db_pdu = db.query(models.PDU).filter(models.PDU.id == pdu_id).first()
    if not db_pdu:
        raise HTTPException(status_code=404, detail="PDU not found")

    for key, value in pdu.model_dump().items():
        setattr(db_pdu, key, value)

    db.commit()
    db.refresh(db_pdu)
    return db_pdu


@router.delete("/pdus/{pdu_id}")
def delete_pdu(
    pdu_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Delete a PDU (admin only)."""
    db_pdu = db.query(models.PDU).filter(models.PDU.id == pdu_id).first()
    if not db_pdu:
        raise HTTPException(status_code=404, detail="PDU not found")

    # Check for equipment using this PDU
    equipment_count = db.query(models.Equipment).filter(
        (models.Equipment.pdu_id == pdu_id) |
        (models.Equipment.redundant_pdu_id == pdu_id)
    ).count()
    if equipment_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete PDU with {equipment_count} connected equipment"
        )

    db.delete(db_pdu)
    db.commit()

    logger.info(f"PDU '{db_pdu.name}' deleted by '{current_user.username}'")
    return {"ok": True}
