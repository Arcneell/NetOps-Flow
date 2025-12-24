"""
Entities Router - Multi-tenant entity management.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import logging

from backend.core.database import get_db
from backend.core.security import get_current_active_user, get_current_admin_user
from backend import models, schemas

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/entities", tags=["Entities"])


# ==================== ENTITIES ====================

@router.get("/", response_model=List[schemas.Entity])
def list_entities(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """List all entities (admin only)."""
    return db.query(models.Entity).order_by(models.Entity.name).all()


@router.get("/current", response_model=schemas.Entity)
def get_current_entity(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get current user's entity."""
    if not current_user.entity_id:
        raise HTTPException(status_code=404, detail="User has no entity assigned")

    entity = db.query(models.Entity).filter(
        models.Entity.id == current_user.entity_id
    ).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    return entity


@router.get("/{entity_id}", response_model=schemas.Entity)
def get_entity(
    entity_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Get a specific entity (admin only)."""
    entity = db.query(models.Entity).filter(
        models.Entity.id == entity_id
    ).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    return entity


@router.get("/{entity_id}/stats")
def get_entity_stats(
    entity_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Get statistics for an entity."""
    entity = db.query(models.Entity).filter(
        models.Entity.id == entity_id
    ).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    users_count = db.query(models.User).filter(
        models.User.entity_id == entity_id
    ).count()

    equipment_count = db.query(models.Equipment).filter(
        models.Equipment.entity_id == entity_id
    ).count()

    subnets_count = db.query(models.Subnet).filter(
        models.Subnet.entity_id == entity_id
    ).count()

    locations_count = db.query(models.Location).filter(
        models.Location.entity_id == entity_id
    ).count()

    racks_count = db.query(models.Rack).filter(
        models.Rack.entity_id == entity_id
    ).count()

    contracts_count = db.query(models.Contract).filter(
        models.Contract.entity_id == entity_id
    ).count()

    software_count = db.query(models.Software).filter(
        models.Software.entity_id == entity_id
    ).count()

    return {
        "entity_id": entity_id,
        "entity_name": entity.name,
        "users": users_count,
        "equipment": equipment_count,
        "subnets": subnets_count,
        "locations": locations_count,
        "racks": racks_count,
        "contracts": contracts_count,
        "software": software_count
    }


@router.post("/", response_model=schemas.Entity)
def create_entity(
    entity: schemas.EntityCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Create a new entity (admin only)."""
    # Check for duplicate name
    existing = db.query(models.Entity).filter(
        models.Entity.name == entity.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Entity name already exists")

    db_entity = models.Entity(**entity.model_dump())
    db.add(db_entity)
    db.commit()
    db.refresh(db_entity)

    logger.info(f"Entity '{entity.name}' created by '{current_user.username}'")
    return db_entity


@router.put("/{entity_id}", response_model=schemas.Entity)
def update_entity(
    entity_id: int,
    entity: schemas.EntityCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Update an entity (admin only)."""
    db_entity = db.query(models.Entity).filter(
        models.Entity.id == entity_id
    ).first()
    if not db_entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    # Check for duplicate name (excluding self)
    existing = db.query(models.Entity).filter(
        models.Entity.name == entity.name,
        models.Entity.id != entity_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Entity name already exists")

    for key, value in entity.model_dump().items():
        setattr(db_entity, key, value)

    db.commit()
    db.refresh(db_entity)

    logger.info(f"Entity '{db_entity.name}' updated by '{current_user.username}'")
    return db_entity


@router.delete("/{entity_id}")
def delete_entity(
    entity_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Delete an entity (admin only). Entity must be empty."""
    db_entity = db.query(models.Entity).filter(
        models.Entity.id == entity_id
    ).first()
    if not db_entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    # Check for associated data
    users_count = db.query(models.User).filter(
        models.User.entity_id == entity_id
    ).count()
    if users_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete entity with {users_count} users"
        )

    equipment_count = db.query(models.Equipment).filter(
        models.Equipment.entity_id == entity_id
    ).count()
    if equipment_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete entity with {equipment_count} equipment"
        )

    db.delete(db_entity)
    db.commit()

    logger.info(f"Entity '{db_entity.name}' deleted by '{current_user.username}'")
    return {"ok": True}
