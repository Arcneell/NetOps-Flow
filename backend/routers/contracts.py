"""
Contracts Router - Maintenance, insurance, and leasing contract management.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import date, timedelta
import logging

from backend.core.database import get_db
from backend.core.security import get_current_active_user, has_permission
from backend import models, schemas

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/contracts", tags=["Contracts"])


def check_contract_permission(current_user: models.User):
    """Check if user has contracts permission (tech with contracts, admin, superadmin)."""
    if not has_permission(current_user, "contracts"):
        raise HTTPException(status_code=403, detail="Permission denied")


def get_user_entity_filter(current_user: models.User):
    """Get entity filter for multi-tenant queries."""
    if current_user.role == "admin" and not current_user.entity_id:
        return None
    return current_user.entity_id


# ==================== CONTRACTS ====================

@router.get("/", response_model=List[schemas.ContractFull])
def list_contracts(
    skip: int = 0,
    limit: int = 100,
    contract_type: str = None,
    supplier_id: int = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """List all contracts with optional filters."""
    check_contract_permission(current_user)

    query = db.query(models.Contract)

    entity_filter = get_user_entity_filter(current_user)
    if entity_filter:
        query = query.filter(models.Contract.entity_id == entity_filter)

    if contract_type:
        query = query.filter(models.Contract.contract_type == contract_type)

    if supplier_id:
        query = query.filter(models.Contract.supplier_id == supplier_id)

    if active_only:
        today = date.today()
        query = query.filter(
            models.Contract.start_date <= today,
            models.Contract.end_date >= today
        )

    return query.order_by(models.Contract.end_date).offset(skip).limit(limit).all()


@router.get("/expiring", response_model=List[schemas.ExpirationAlert])
def get_expiring_contracts(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get contracts expiring within specified days."""
    check_contract_permission(current_user)

    today = date.today()
    threshold = today + timedelta(days=days)

    query = db.query(models.Contract).filter(
        models.Contract.end_date >= today,
        models.Contract.end_date <= threshold
    )

    entity_filter = get_user_entity_filter(current_user)
    if entity_filter:
        query = query.filter(models.Contract.entity_id == entity_filter)

    contracts = query.order_by(models.Contract.end_date).all()

    alerts = []
    for contract in contracts:
        days_remaining = (contract.end_date - today).days
        severity = "critical" if days_remaining <= 7 else "warning" if days_remaining <= 14 else "info"

        alerts.append(schemas.ExpirationAlert(
            type="contract",
            item_id=contract.id,
            item_name=contract.name,
            expiry_date=contract.end_date,
            days_remaining=days_remaining,
            severity=severity
        ))

    return alerts


@router.get("/{contract_id}", response_model=schemas.ContractFull)
def get_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get a specific contract."""
    check_contract_permission(current_user)

    contract = db.query(models.Contract).filter(
        models.Contract.id == contract_id
    ).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    entity_filter = get_user_entity_filter(current_user)
    if entity_filter and contract.entity_id != entity_filter:
        raise HTTPException(status_code=403, detail="Access denied")

    return contract


@router.get("/{contract_id}/equipment")
def get_contract_equipment(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get equipment covered by this contract."""
    check_contract_permission(current_user)

    contract = db.query(models.Contract).filter(
        models.Contract.id == contract_id
    ).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    equipment_links = db.query(models.ContractEquipment).filter(
        models.ContractEquipment.contract_id == contract_id
    ).all()

    equipment_list = []
    for link in equipment_links:
        eq = db.query(models.Equipment).filter(
            models.Equipment.id == link.equipment_id
        ).first()
        if eq:
            equipment_list.append({
                "id": eq.id,
                "name": eq.name,
                "serial_number": eq.serial_number,
                "status": eq.status,
                "link_notes": link.notes
            })

    return {
        "contract_id": contract_id,
        "contract_name": contract.name,
        "equipment": equipment_list
    }


@router.post("/", response_model=schemas.Contract)
def create_contract(
    contract: schemas.ContractCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Create a new contract."""
    check_contract_permission(current_user)

    # Validate dates
    if contract.end_date <= contract.start_date:
        raise HTTPException(
            status_code=400,
            detail="End date must be after start date"
        )

    # Check for duplicate contract number
    if contract.contract_number:
        existing = db.query(models.Contract).filter(
            models.Contract.contract_number == contract.contract_number
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Contract number already exists"
            )

    contract_data = contract.model_dump()
    if not contract_data.get("entity_id") and current_user.entity_id:
        contract_data["entity_id"] = current_user.entity_id

    db_contract = models.Contract(**contract_data)
    db.add(db_contract)
    db.commit()
    db.refresh(db_contract)

    logger.info(f"Contract '{contract.name}' created by '{current_user.username}'")
    return db_contract


@router.put("/{contract_id}", response_model=schemas.Contract)
def update_contract(
    contract_id: int,
    contract: schemas.ContractCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Update a contract."""
    check_contract_permission(current_user)

    db_contract = db.query(models.Contract).filter(
        models.Contract.id == contract_id
    ).first()
    if not db_contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if contract.end_date <= contract.start_date:
        raise HTTPException(
            status_code=400,
            detail="End date must be after start date"
        )

    for key, value in contract.model_dump().items():
        setattr(db_contract, key, value)

    db.commit()
    db.refresh(db_contract)

    logger.info(f"Contract '{db_contract.name}' updated by '{current_user.username}'")
    return db_contract


@router.delete("/{contract_id}")
def delete_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Delete a contract (admin only)."""
    db_contract = db.query(models.Contract).filter(
        models.Contract.id == contract_id
    ).first()
    if not db_contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    # Delete equipment links first
    db.query(models.ContractEquipment).filter(
        models.ContractEquipment.contract_id == contract_id
    ).delete()

    db.delete(db_contract)
    db.commit()

    logger.info(f"Contract '{db_contract.name}' deleted by '{current_user.username}'")
    return {"ok": True}


# ==================== CONTRACT-EQUIPMENT LINKING ====================

@router.post("/{contract_id}/equipment/{equipment_id}")
def link_equipment_to_contract(
    contract_id: int,
    equipment_id: int,
    notes: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Link equipment to a contract."""
    check_contract_permission(current_user)

    contract = db.query(models.Contract).filter(
        models.Contract.id == contract_id
    ).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    equipment = db.query(models.Equipment).filter(
        models.Equipment.id == equipment_id
    ).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    # Check if already linked
    existing = db.query(models.ContractEquipment).filter(
        models.ContractEquipment.contract_id == contract_id,
        models.ContractEquipment.equipment_id == equipment_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Equipment already linked to this contract"
        )

    link = models.ContractEquipment(
        contract_id=contract_id,
        equipment_id=equipment_id,
        notes=notes
    )
    db.add(link)
    db.commit()

    logger.info(
        f"Equipment '{equipment.name}' linked to contract '{contract.name}' "
        f"by '{current_user.username}'"
    )
    return {"ok": True}


@router.delete("/{contract_id}/equipment/{equipment_id}")
def unlink_equipment_from_contract(
    contract_id: int,
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Unlink equipment from a contract."""
    check_contract_permission(current_user)

    link = db.query(models.ContractEquipment).filter(
        models.ContractEquipment.contract_id == contract_id,
        models.ContractEquipment.equipment_id == equipment_id
    ).first()
    if not link:
        raise HTTPException(
            status_code=404,
            detail="Equipment not linked to this contract"
        )

    db.delete(link)
    db.commit()

    return {"ok": True}
