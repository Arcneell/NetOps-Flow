"""
IPAM Router - IP Address Management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
import ipaddress
import logging

from backend.core.database import get_db
from backend.core.security import get_current_active_user, get_current_admin_user
from backend import models, schemas
from worker.tasks import scan_subnet_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/subnets", tags=["IPAM"])


def check_ipam_permission(current_user: models.User):
    """Check if user has IPAM permission."""
    if current_user.role != "admin" and not current_user.permissions.get("ipam"):
        raise HTTPException(status_code=403, detail="Permission denied")


@router.post("/", response_model=schemas.Subnet)
def create_subnet(
    subnet: schemas.SubnetCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Create a new subnet."""
    check_ipam_permission(current_user)

    try:
        ipaddress.ip_network(subnet.cidr)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid CIDR format")

    db_subnet = models.Subnet(
        cidr=subnet.cidr,
        name=subnet.name,
        description=subnet.description
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
    """List all subnets with their IPs."""
    if (current_user.role != "admin" and
        not current_user.permissions.get("ipam") and
        not current_user.permissions.get("topology")):
        raise HTTPException(status_code=403, detail="Permission denied")

    subnets = db.query(models.Subnet).options(
        joinedload(models.Subnet.ips).joinedload(models.IPAddress.equipment)
    ).offset(skip).limit(limit).all()

    return subnets


@router.post("/{subnet_id}/ips/", response_model=schemas.IPAddress)
def create_ip_for_subnet(
    subnet_id: int,
    ip: schemas.IPAddressCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Allocate an IP address in a subnet."""
    check_ipam_permission(current_user)

    subnet = db.query(models.Subnet).filter(models.Subnet.id == subnet_id).first()
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

    subnet = db.query(models.Subnet).filter(models.Subnet.id == subnet_id).first()
    if not subnet:
        raise HTTPException(status_code=404, detail="Subnet not found")

    task = scan_subnet_task.delay(subnet_id)
    logger.info(f"Subnet scan started for '{subnet.cidr}' by '{current_user.username}'")

    return {"message": "Scan started", "task_id": task.id}


@router.delete("/{subnet_id}")
def delete_subnet(
    subnet_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Delete a subnet and all its IPs (admin only)."""
    subnet = db.query(models.Subnet).filter(models.Subnet.id == subnet_id).first()
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

    ip = db.query(models.IPAddress).filter(
        models.IPAddress.id == ip_id,
        models.IPAddress.subnet_id == subnet_id
    ).first()

    if not ip:
        raise HTTPException(status_code=404, detail="IP address not found")

    address = ip.address
    db.delete(ip)
    db.commit()

    logger.info(f"IP '{address}' deleted by '{current_user.username}'")
    return {"ok": True}
