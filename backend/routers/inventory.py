"""
Inventory Router - Equipment management.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from backend.core.database import get_db
from backend.core.security import (
    get_current_active_user,
    get_current_admin_user,
    encrypt_value,
)
from backend import models, schemas

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/inventory", tags=["Inventory"])


def check_inventory_permission(current_user: models.User):
    """Check if user has inventory permission."""
    if current_user.role != "admin" and not current_user.permissions.get("inventory"):
        raise HTTPException(status_code=403, detail="Permission denied")


def get_user_entity_filter(current_user: models.User):
    """Get entity filter for multi-tenant queries."""
    if current_user.role == "admin" and not current_user.entity_id:
        return None  # Admin without entity sees all
    return current_user.entity_id


# --- Manufacturers ---

@router.get("/manufacturers/", response_model=List[schemas.Manufacturer])
def list_manufacturers(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    check_inventory_permission(current_user)
    return db.query(models.Manufacturer).order_by(models.Manufacturer.name).all()


@router.post("/manufacturers/", response_model=schemas.Manufacturer)
def create_manufacturer(
    manufacturer: schemas.ManufacturerCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    check_inventory_permission(current_user)
    existing = db.query(models.Manufacturer).filter(
        models.Manufacturer.name == manufacturer.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Manufacturer already exists")

    db_manufacturer = models.Manufacturer(**manufacturer.model_dump())
    db.add(db_manufacturer)
    db.commit()
    db.refresh(db_manufacturer)
    return db_manufacturer


@router.put("/manufacturers/{manufacturer_id}", response_model=schemas.Manufacturer)
def update_manufacturer(
    manufacturer_id: int,
    manufacturer: schemas.ManufacturerCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    check_inventory_permission(current_user)
    db_manufacturer = db.query(models.Manufacturer).filter(
        models.Manufacturer.id == manufacturer_id
    ).first()
    if not db_manufacturer:
        raise HTTPException(status_code=404, detail="Manufacturer not found")

    for key, value in manufacturer.model_dump().items():
        setattr(db_manufacturer, key, value)
    db.commit()
    db.refresh(db_manufacturer)
    return db_manufacturer


@router.delete("/manufacturers/{manufacturer_id}")
def delete_manufacturer(
    manufacturer_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    db_manufacturer = db.query(models.Manufacturer).filter(
        models.Manufacturer.id == manufacturer_id
    ).first()
    if not db_manufacturer:
        raise HTTPException(status_code=404, detail="Manufacturer not found")

    if db.query(models.EquipmentModel).filter(
        models.EquipmentModel.manufacturer_id == manufacturer_id
    ).count() > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete manufacturer with associated models"
        )

    db.delete(db_manufacturer)
    db.commit()
    return {"ok": True}


# --- Equipment Types ---

@router.get("/types/", response_model=List[schemas.EquipmentType])
def list_equipment_types(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    check_inventory_permission(current_user)
    return db.query(models.EquipmentType).order_by(models.EquipmentType.name).all()


@router.post("/types/", response_model=schemas.EquipmentType)
def create_equipment_type(
    equipment_type: schemas.EquipmentTypeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    check_inventory_permission(current_user)
    existing = db.query(models.EquipmentType).filter(
        models.EquipmentType.name == equipment_type.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Equipment type already exists")

    db_type = models.EquipmentType(**equipment_type.model_dump())
    db.add(db_type)
    db.commit()
    db.refresh(db_type)
    return db_type


@router.put("/types/{type_id}", response_model=schemas.EquipmentType)
def update_equipment_type(
    type_id: int,
    equipment_type: schemas.EquipmentTypeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    check_inventory_permission(current_user)
    db_type = db.query(models.EquipmentType).filter(
        models.EquipmentType.id == type_id
    ).first()
    if not db_type:
        raise HTTPException(status_code=404, detail="Equipment type not found")

    for key, value in equipment_type.model_dump().items():
        setattr(db_type, key, value)
    db.commit()
    db.refresh(db_type)
    return db_type


@router.delete("/types/{type_id}")
def delete_equipment_type(
    type_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    db_type = db.query(models.EquipmentType).filter(
        models.EquipmentType.id == type_id
    ).first()
    if not db_type:
        raise HTTPException(status_code=404, detail="Equipment type not found")

    if db.query(models.EquipmentModel).filter(
        models.EquipmentModel.equipment_type_id == type_id
    ).count() > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete type with associated models"
        )

    db.delete(db_type)
    db.commit()
    return {"ok": True}


# --- Equipment Models ---

@router.get("/models/", response_model=List[schemas.EquipmentModelFull])
def list_equipment_models(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    check_inventory_permission(current_user)
    return db.query(models.EquipmentModel).order_by(models.EquipmentModel.name).all()


@router.post("/models/", response_model=schemas.EquipmentModel)
def create_equipment_model(
    model: schemas.EquipmentModelCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    check_inventory_permission(current_user)

    if not db.query(models.Manufacturer).filter(
        models.Manufacturer.id == model.manufacturer_id
    ).first():
        raise HTTPException(status_code=400, detail="Manufacturer not found")

    if not db.query(models.EquipmentType).filter(
        models.EquipmentType.id == model.equipment_type_id
    ).first():
        raise HTTPException(status_code=400, detail="Equipment type not found")

    db_model = models.EquipmentModel(**model.model_dump())
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return db_model


@router.put("/models/{model_id}", response_model=schemas.EquipmentModel)
def update_equipment_model(
    model_id: int,
    model: schemas.EquipmentModelCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    check_inventory_permission(current_user)
    db_model = db.query(models.EquipmentModel).filter(
        models.EquipmentModel.id == model_id
    ).first()
    if not db_model:
        raise HTTPException(status_code=404, detail="Equipment model not found")

    for key, value in model.model_dump().items():
        setattr(db_model, key, value)
    db.commit()
    db.refresh(db_model)
    return db_model


@router.delete("/models/{model_id}")
def delete_equipment_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    db_model = db.query(models.EquipmentModel).filter(
        models.EquipmentModel.id == model_id
    ).first()
    if not db_model:
        raise HTTPException(status_code=404, detail="Equipment model not found")

    if db.query(models.Equipment).filter(
        models.Equipment.model_id == model_id
    ).count() > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete model with associated equipment"
        )

    db.delete(db_model)
    db.commit()
    return {"ok": True}


# --- Locations ---

@router.get("/locations/", response_model=List[schemas.Location])
def list_locations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    check_inventory_permission(current_user)
    return db.query(models.Location).order_by(
        models.Location.site,
        models.Location.building,
        models.Location.room
    ).all()


@router.post("/locations/", response_model=schemas.Location)
def create_location(
    location: schemas.LocationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    check_inventory_permission(current_user)
    db_location = models.Location(**location.model_dump())
    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    return db_location


@router.put("/locations/{location_id}", response_model=schemas.Location)
def update_location(
    location_id: int,
    location: schemas.LocationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    check_inventory_permission(current_user)
    db_location = db.query(models.Location).filter(
        models.Location.id == location_id
    ).first()
    if not db_location:
        raise HTTPException(status_code=404, detail="Location not found")

    for key, value in location.model_dump().items():
        setattr(db_location, key, value)
    db.commit()
    db.refresh(db_location)
    return db_location


@router.delete("/locations/{location_id}")
def delete_location(
    location_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    db_location = db.query(models.Location).filter(
        models.Location.id == location_id
    ).first()
    if not db_location:
        raise HTTPException(status_code=404, detail="Location not found")

    if db.query(models.Equipment).filter(
        models.Equipment.location_id == location_id
    ).count() > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete location with associated equipment"
        )

    db.delete(db_location)
    db.commit()
    return {"ok": True}


# --- Suppliers ---

@router.get("/suppliers/", response_model=List[schemas.Supplier])
def list_suppliers(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    check_inventory_permission(current_user)
    return db.query(models.Supplier).order_by(models.Supplier.name).all()


@router.post("/suppliers/", response_model=schemas.Supplier)
def create_supplier(
    supplier: schemas.SupplierCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    check_inventory_permission(current_user)
    existing = db.query(models.Supplier).filter(
        models.Supplier.name == supplier.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Supplier already exists")

    db_supplier = models.Supplier(**supplier.model_dump())
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    return db_supplier


@router.put("/suppliers/{supplier_id}", response_model=schemas.Supplier)
def update_supplier(
    supplier_id: int,
    supplier: schemas.SupplierCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    check_inventory_permission(current_user)
    db_supplier = db.query(models.Supplier).filter(
        models.Supplier.id == supplier_id
    ).first()
    if not db_supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    for key, value in supplier.model_dump().items():
        setattr(db_supplier, key, value)
    db.commit()
    db.refresh(db_supplier)
    return db_supplier


@router.delete("/suppliers/{supplier_id}")
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    db_supplier = db.query(models.Supplier).filter(
        models.Supplier.id == supplier_id
    ).first()
    if not db_supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    if db.query(models.Equipment).filter(
        models.Equipment.supplier_id == supplier_id
    ).count() > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete supplier with associated equipment"
        )

    db.delete(db_supplier)
    db.commit()
    return {"ok": True}


# --- Equipment ---

@router.get("/equipment/", response_model=List[schemas.EquipmentFull])
def list_equipment(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    type_id: Optional[int] = None,
    location_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    check_inventory_permission(current_user)
    query = db.query(models.Equipment)

    # Apply entity filter for multi-tenant isolation
    entity_filter = get_user_entity_filter(current_user)
    if entity_filter:
        query = query.filter(models.Equipment.entity_id == entity_filter)

    if status:
        query = query.filter(models.Equipment.status == status)
    if type_id:
        query = query.join(models.EquipmentModel).filter(
            models.EquipmentModel.equipment_type_id == type_id
        )
    if location_id:
        query = query.filter(models.Equipment.location_id == location_id)

    return query.order_by(models.Equipment.name).offset(skip).limit(limit).all()


@router.get("/equipment/executable/", response_model=List[schemas.EquipmentFull])
def list_executable_equipment(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get equipment configured for remote execution."""
    if current_user.role != "admin" and not current_user.permissions.get("scripts"):
        raise HTTPException(status_code=403, detail="Permission denied")

    query = db.query(models.Equipment).join(
        models.EquipmentModel
    ).join(
        models.EquipmentType
    ).filter(
        models.EquipmentType.supports_remote_execution == True,
        models.Equipment.remote_ip != None,
        models.Equipment.remote_username != None
    )

    # Apply entity filter for multi-tenant isolation
    entity_filter = get_user_entity_filter(current_user)
    if entity_filter:
        query = query.filter(models.Equipment.entity_id == entity_filter)

    return query.order_by(models.Equipment.name).all()


@router.get("/equipment/{equipment_id}", response_model=schemas.EquipmentFull)
def get_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    check_inventory_permission(current_user)
    equipment = db.query(models.Equipment).filter(
        models.Equipment.id == equipment_id
    ).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    # Verify entity access
    entity_filter = get_user_entity_filter(current_user)
    if entity_filter and equipment.entity_id != entity_filter:
        raise HTTPException(status_code=403, detail="Access denied to this equipment")

    return equipment


@router.post("/equipment/", response_model=schemas.Equipment)
def create_equipment(
    equipment: schemas.EquipmentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    check_inventory_permission(current_user)

    valid_statuses = ["in_service", "in_stock", "retired", "maintenance"]
    if equipment.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )

    if equipment.serial_number:
        existing = db.query(models.Equipment).filter(
            models.Equipment.serial_number == equipment.serial_number
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Serial number already exists")

    if equipment.asset_tag:
        existing = db.query(models.Equipment).filter(
            models.Equipment.asset_tag == equipment.asset_tag
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Asset tag already exists")

    # Encrypt password if provided
    equipment_data = equipment.model_dump()
    if equipment_data.get("remote_password"):
        equipment_data["remote_password"] = encrypt_value(equipment_data["remote_password"])

    # Set entity_id if not provided
    if not equipment_data.get("entity_id") and current_user.entity_id:
        equipment_data["entity_id"] = current_user.entity_id

    db_equipment = models.Equipment(**equipment_data)
    db.add(db_equipment)
    db.commit()
    db.refresh(db_equipment)

    logger.info(f"Equipment '{equipment.name}' created by '{current_user.username}'")
    return db_equipment


@router.put("/equipment/{equipment_id}", response_model=schemas.Equipment)
def update_equipment(
    equipment_id: int,
    equipment: schemas.EquipmentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    check_inventory_permission(current_user)
    db_equipment = db.query(models.Equipment).filter(
        models.Equipment.id == equipment_id
    ).first()
    if not db_equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    # Verify entity access
    entity_filter = get_user_entity_filter(current_user)
    if entity_filter and db_equipment.entity_id != entity_filter:
        raise HTTPException(status_code=403, detail="Access denied to this equipment")

    update_data = equipment.model_dump(exclude_unset=True)

    # Encrypt password if being updated
    if "remote_password" in update_data and update_data["remote_password"]:
        update_data["remote_password"] = encrypt_value(update_data["remote_password"])

    for key, value in update_data.items():
        setattr(db_equipment, key, value)

    db.commit()
    db.refresh(db_equipment)

    logger.info(f"Equipment '{db_equipment.name}' updated by '{current_user.username}'")
    return db_equipment


@router.delete("/equipment/{equipment_id}")
def delete_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    db_equipment = db.query(models.Equipment).filter(
        models.Equipment.id == equipment_id
    ).first()
    if not db_equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    # Unlink IPs
    db.query(models.IPAddress).filter(
        models.IPAddress.equipment_id == equipment_id
    ).update({"equipment_id": None})

    db.delete(db_equipment)
    db.commit()

    logger.info(f"Equipment '{db_equipment.name}' deleted by '{current_user.username}'")
    return {"ok": True}


# --- Equipment-IP Linking ---

@router.post("/equipment/{equipment_id}/link-ip")
def link_ip_to_equipment(
    equipment_id: int,
    link_request: schemas.IPLinkRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    check_inventory_permission(current_user)

    equipment = db.query(models.Equipment).filter(
        models.Equipment.id == equipment_id
    ).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    ip = db.query(models.IPAddress).filter(
        models.IPAddress.id == link_request.ip_address_id
    ).first()
    if not ip:
        raise HTTPException(status_code=404, detail="IP address not found")

    if ip.equipment_id and ip.equipment_id != equipment_id:
        raise HTTPException(
            status_code=400,
            detail="IP address is already linked to another equipment"
        )

    ip.equipment_id = equipment_id
    db.commit()

    logger.info(f"IP '{ip.address}' linked to '{equipment.name}' by '{current_user.username}'")
    return {"ok": True, "message": f"IP {ip.address} linked to {equipment.name}"}


@router.delete("/equipment/{equipment_id}/unlink-ip/{ip_id}")
def unlink_ip_from_equipment(
    equipment_id: int,
    ip_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    check_inventory_permission(current_user)

    ip = db.query(models.IPAddress).filter(
        models.IPAddress.id == ip_id,
        models.IPAddress.equipment_id == equipment_id
    ).first()
    if not ip:
        raise HTTPException(
            status_code=404,
            detail="IP address not found or not linked to this equipment"
        )

    ip.equipment_id = None
    db.commit()

    logger.info(f"IP '{ip.address}' unlinked by '{current_user.username}'")
    return {"ok": True}


@router.get("/available-ips/", response_model=List[schemas.IPAddress])
def get_available_ips(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get IPs not linked to any equipment."""
    check_inventory_permission(current_user)

    query = db.query(models.IPAddress).filter(
        models.IPAddress.equipment_id == None
    )

    # Apply entity filter for multi-tenant isolation
    entity_filter = get_user_entity_filter(current_user)
    if entity_filter:
        # Join with subnet to filter by entity
        query = query.join(models.Subnet).filter(
            models.Subnet.entity_id == entity_filter
        )

    return query.all()
