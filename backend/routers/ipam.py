"""
IPAM Router - IP Address Management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func
from typing import List
import ipaddress
import logging

from backend.core.database import get_db
from backend.core.security import get_current_active_user, has_permission
from backend import models, schemas
from worker.tasks import scan_subnet_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/subnets", tags=["IPAM"])


def check_ipam_permission(current_user: models.User):
    """Check if user has IPAM permission (tech with ipam, admin, superadmin)."""
    if not has_permission(current_user, "ipam"):
        raise HTTPException(status_code=403, detail="Permission denied")

def get_entity_filter(current_user: models.User) -> int | None:
    """Entity scope for reads. Admin without entity sees all."""
    if current_user.role == "admin" and not current_user.entity_id:
        return None
    return current_user.entity_id


def get_entity_for_write(current_user: models.User) -> int | None:
    """
    Entity to stamp on new records.
    - If user has an entity, use it.
    - Admin/superadmin without entity write global (None).
    - Tech without entity writes global (keeps seamless, matches current request).
    """
    return current_user.entity_id


@router.post("/", response_model=schemas.Subnet)
def create_subnet(
    subnet: schemas.SubnetCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Create a new subnet."""
    check_ipam_permission(current_user)
    entity_id = get_entity_for_write(current_user)

    try:
        ipaddress.ip_network(subnet.cidr)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid CIDR format")

    db_subnet = models.Subnet(
        cidr=subnet.cidr,
        name=subnet.name,
        description=subnet.description,
        entity_id=entity_id
    )
    db.add(db_subnet)
    db.commit()
    db.refresh(db_subnet)

    logger.info(f"Subnet '{subnet.cidr}' created by '{current_user.username}'")
    return db_subnet


@router.get("/", response_model=List[schemas.SubnetWithEquipment])
def read_subnets(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """List all subnets with IP counts (tech with ipam, admin, superadmin)."""
    check_ipam_permission(current_user)
    entity_filter = get_entity_filter(current_user)

    # Subquery for IP count per subnet
    ip_count_subq = db.query(
        models.IPAddress.subnet_id,
        func.count(models.IPAddress.id).label('ip_count')
    ).group_by(models.IPAddress.subnet_id).subquery()

    query = db.query(
        models.Subnet,
        func.coalesce(ip_count_subq.c.ip_count, 0).label('ip_count')
    ).outerjoin(
        ip_count_subq, models.Subnet.id == ip_count_subq.c.subnet_id
    )

    if entity_filter is not None:
        query = query.filter(
            or_(
                models.Subnet.entity_id == entity_filter,
                models.Subnet.entity_id == None  # noqa: E711
            )
        )

    results = query.offset(skip).limit(limit).all()

    # Convert to response format
    subnets = []
    for subnet, ip_count in results:
        subnets.append(schemas.SubnetWithEquipment(
            id=subnet.id,
            cidr=subnet.cidr,
            name=subnet.name,
            description=subnet.description,
            ip_count=ip_count
        ))

    return subnets


@router.put("/{subnet_id}", response_model=schemas.Subnet)
def update_subnet(
    subnet_id: int,
    subnet_update: schemas.SubnetUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Update a subnet (name and description only, CIDR cannot be changed)."""
    check_ipam_permission(current_user)
    entity_filter = get_entity_filter(current_user)

    subnet_query = db.query(models.Subnet).filter(models.Subnet.id == subnet_id)
    if entity_filter is not None:
        subnet_query = subnet_query.filter(
            or_(
                models.Subnet.entity_id == entity_filter,
                models.Subnet.entity_id == None  # noqa: E711
            )
        )
    db_subnet = subnet_query.first()
    if not db_subnet:
        raise HTTPException(status_code=404, detail="Subnet not found")

    # Update fields
    if subnet_update.name is not None:
        db_subnet.name = subnet_update.name
    if subnet_update.description is not None:
        db_subnet.description = subnet_update.description

    db.commit()
    db.refresh(db_subnet)

    logger.info(f"Subnet '{db_subnet.cidr}' updated by '{current_user.username}'")
    return db_subnet


@router.get("/{subnet_id}/ips/", response_model=schemas.PaginatedIPResponse)
def get_subnet_ips(
    subnet_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get paginated IP addresses for a subnet."""
    check_ipam_permission(current_user)
    entity_filter = get_entity_filter(current_user)

    # Verify subnet access
    subnet_query = db.query(models.Subnet).filter(models.Subnet.id == subnet_id)
    if entity_filter is not None:
        subnet_query = subnet_query.filter(
            or_(
                models.Subnet.entity_id == entity_filter,
                models.Subnet.entity_id == None  # noqa: E711
            )
        )
    subnet = subnet_query.first()
    if not subnet:
        raise HTTPException(status_code=404, detail="Subnet not found")

    # Get total count
    total = db.query(func.count(models.IPAddress.id)).filter(
        models.IPAddress.subnet_id == subnet_id
    ).scalar() or 0

    # Get paginated IPs with equipment
    ips = db.query(models.IPAddress).options(
        joinedload(models.IPAddress.equipment)
    ).filter(
        models.IPAddress.subnet_id == subnet_id
    ).order_by(models.IPAddress.address).offset(skip).limit(limit).all()

    return schemas.PaginatedIPResponse(
        items=ips,
        total=total,
        skip=skip,
        limit=limit
    )


@router.post("/{subnet_id}/ips/", response_model=schemas.IPAddress)
def create_ip_for_subnet(
    subnet_id: int,
    ip: schemas.IPAddressCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Allocate an IP address in a subnet."""
    check_ipam_permission(current_user)
    entity_filter = get_entity_filter(current_user)

    subnet_query = db.query(models.Subnet).filter(models.Subnet.id == subnet_id)
    if entity_filter is not None:
        subnet_query = subnet_query.filter(
            or_(
                models.Subnet.entity_id == entity_filter,
                models.Subnet.entity_id == None  # noqa: E711
            )
        )
    subnet = subnet_query.first()
    if not subnet:
        raise HTTPException(status_code=404, detail="Subnet not found")

    net = ipaddress.ip_network(subnet.cidr)
    try:
        addr = ipaddress.ip_address(ip.address)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid IP address format")

    if addr not in net:
        raise HTTPException(
            status_code=400,
            detail=f"IP {ip.address} does not belong to subnet {subnet.cidr}"
        )

    # Check for duplicate
    existing = db.query(models.IPAddress).filter(
        models.IPAddress.address == ip.address
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="IP address already exists")

    db_ip = models.IPAddress(**ip.model_dump(), subnet_id=subnet_id)
    db.add(db_ip)
    db.commit()
    db.refresh(db_ip)

    logger.info(f"IP '{ip.address}' allocated in subnet '{subnet.cidr}' by '{current_user.username}'")
    return db_ip


@router.post("/{subnet_id}/scan")
def scan_subnet(
    subnet_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Start a subnet scan task."""
    check_ipam_permission(current_user)
    entity_filter = get_entity_filter(current_user)

    subnet_query = db.query(models.Subnet).filter(models.Subnet.id == subnet_id)
    if entity_filter is not None:
        subnet_query = subnet_query.filter(
            or_(
                models.Subnet.entity_id == entity_filter,
                models.Subnet.entity_id == None  # noqa: E711
            )
        )
    subnet = subnet_query.first()
    if not subnet:
        raise HTTPException(status_code=404, detail="Subnet not found")

    task = scan_subnet_task.delay(subnet_id)
    logger.info(f"Subnet scan started for '{subnet.cidr}' by '{current_user.username}'")

    return {"message": "Scan started", "task_id": task.id}


@router.delete("/{subnet_id}")
def delete_subnet(
    subnet_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Delete a subnet and all its IPs (ipam permission required)."""
    check_ipam_permission(current_user)
    entity_filter = get_entity_filter(current_user)

    subnet_query = db.query(models.Subnet).filter(models.Subnet.id == subnet_id)
    if entity_filter is not None:
        subnet_query = subnet_query.filter(
            or_(
                models.Subnet.entity_id == entity_filter,
                models.Subnet.entity_id == None  # noqa: E711
            )
        )
    subnet = subnet_query.first()
    if not subnet:
        raise HTTPException(status_code=404, detail="Subnet not found")

    cidr = subnet.cidr
    db.delete(subnet)
    db.commit()

    logger.info(f"Subnet '{cidr}' deleted by '{current_user.username}'")
    return {"ok": True, "message": f"Subnet {cidr} deleted"}


@router.delete("/{subnet_id}/ips/{ip_id}")
def delete_ip(
    subnet_id: int,
    ip_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Delete an IP address from a subnet."""
    check_ipam_permission(current_user)
    entity_filter = get_entity_filter(current_user)

    query = db.query(models.IPAddress).join(models.Subnet).filter(
        models.IPAddress.id == ip_id,
        models.IPAddress.subnet_id == subnet_id,
    )
    if entity_filter is not None:
        query = query.filter(
            or_(
                models.Subnet.entity_id == entity_filter,
                models.Subnet.entity_id == None  # noqa: E711
            )
        )
    ip = query.first()

    if not ip:
        raise HTTPException(status_code=404, detail="IP address not found")

    address = ip.address
    db.delete(ip)
    db.commit()

    logger.info(f"IP '{address}' deleted by '{current_user.username}'")
    return {"ok": True}
