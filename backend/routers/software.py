"""
Software & License Router - Software inventory and license compliance.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, case, and_
from typing import List, Optional
from datetime import date, timedelta
import logging

from backend.core.database import get_db
from backend.core.security import get_current_active_user, check_permission_or_raise, encrypt_value
from backend import models, schemas

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/software", tags=["Software & Licenses"])


def check_software_permission(current_user: models.User):
    """Check if user has software permission (tech with software, admin, superadmin)."""
    check_permission_or_raise(current_user, "software", "manage software and licenses")


def get_user_entity_filter(current_user: models.User):
    """Get entity filter for multi-tenant queries."""
    if current_user.role == "admin" and not current_user.entity_id:
        return None
    return current_user.entity_id


# ==================== SOFTWARE CATALOG ====================

@router.get("/", response_model=schemas.PaginatedSoftwareResponse)
def list_software(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """List all software with compliance status (optimized with single query)."""
    check_software_permission(current_user)

    # Subquery for total licenses per software
    license_subq = db.query(
        models.SoftwareLicense.software_id,
        func.coalesce(func.sum(models.SoftwareLicense.quantity), 0).label('total_licenses')
    ).group_by(models.SoftwareLicense.software_id).subquery()

    # Subquery for total installations per software
    installation_subq = db.query(
        models.SoftwareInstallation.software_id,
        func.count(models.SoftwareInstallation.id).label('total_installations')
    ).group_by(models.SoftwareInstallation.software_id).subquery()

    # Main query with LEFT JOINs to subqueries
    query = db.query(
        models.Software,
        func.coalesce(license_subq.c.total_licenses, 0).label('total_licenses'),
        func.coalesce(installation_subq.c.total_installations, 0).label('total_installations')
    ).outerjoin(
        license_subq, models.Software.id == license_subq.c.software_id
    ).outerjoin(
        installation_subq, models.Software.id == installation_subq.c.software_id
    )

    entity_filter = get_user_entity_filter(current_user)
    if entity_filter:
        query = query.filter(models.Software.entity_id == entity_filter)

    if category:
        query = query.filter(models.Software.category == category)

    # Get total count for pagination
    total = query.count()

    # Get paginated results
    results = query.order_by(models.Software.name).offset(skip).limit(limit).all()

    items = []
    for sw, total_licenses, total_installations in results:
        # Determine compliance status
        if total_licenses == 0:
            compliance = "unknown"
        elif total_installations > total_licenses:
            compliance = "violation"
        elif total_installations > total_licenses * 0.9:
            compliance = "warning"
        else:
            compliance = "compliant"

        items.append(schemas.SoftwareWithCompliance(
            **{k: v for k, v in sw.__dict__.items() if not k.startswith('_')},
            total_licenses=int(total_licenses),
            total_installations=int(total_installations),
            compliance_status=compliance
        ))

    return schemas.PaginatedSoftwareResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/compliance")
def get_compliance_overview(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get overall license compliance status (optimized with single query)."""
    check_software_permission(current_user)

    # Subquery for total licenses per software
    license_subq = db.query(
        models.SoftwareLicense.software_id,
        func.coalesce(func.sum(models.SoftwareLicense.quantity), 0).label('total_licenses')
    ).group_by(models.SoftwareLicense.software_id).subquery()

    # Subquery for total installations per software
    installation_subq = db.query(
        models.SoftwareInstallation.software_id,
        func.count(models.SoftwareInstallation.id).label('total_installations')
    ).group_by(models.SoftwareInstallation.software_id).subquery()

    # Main query with LEFT JOINs
    query = db.query(
        models.Software.id,
        models.Software.name,
        func.coalesce(license_subq.c.total_licenses, 0).label('total_licenses'),
        func.coalesce(installation_subq.c.total_installations, 0).label('total_installations')
    ).outerjoin(
        license_subq, models.Software.id == license_subq.c.software_id
    ).outerjoin(
        installation_subq, models.Software.id == installation_subq.c.software_id
    )

    entity_filter = get_user_entity_filter(current_user)
    if entity_filter:
        query = query.filter(models.Software.entity_id == entity_filter)

    # Only include software with licenses
    query = query.filter(license_subq.c.total_licenses > 0)

    results = query.all()

    compliant = 0
    warning = 0
    violation = 0
    violations = []

    for sw_id, sw_name, total_licenses, total_installations in results:
        total_licenses = int(total_licenses)
        total_installations = int(total_installations)

        if total_installations > total_licenses:
            violation += 1
            violations.append({
                "software_id": sw_id,
                "software_name": sw_name,
                "licensed": total_licenses,
                "installed": total_installations,
                "over_by": total_installations - total_licenses
            })
        elif total_installations > total_licenses * 0.9:
            warning += 1
        else:
            compliant += 1

    return {
        "compliant": compliant,
        "warning": warning,
        "violation": violation,
        "violations": violations
    }


@router.get("/{software_id}", response_model=schemas.Software)
def get_software(
    software_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get specific software."""
    check_software_permission(current_user)

    software = db.query(models.Software).filter(
        models.Software.id == software_id
    ).first()
    if not software:
        raise HTTPException(status_code=404, detail="Software not found")

    return software


@router.post("/", response_model=schemas.Software)
def create_software(
    software: schemas.SoftwareCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Create a new software entry."""
    check_software_permission(current_user)

    software_data = software.model_dump()
    if not software_data.get("entity_id") and current_user.entity_id:
        software_data["entity_id"] = current_user.entity_id

    db_software = models.Software(**software_data)
    db.add(db_software)
    db.commit()
    db.refresh(db_software)

    logger.info(f"Software '{software.name}' created by '{current_user.username}'")
    return db_software


@router.put("/{software_id}", response_model=schemas.Software)
def update_software(
    software_id: int,
    software: schemas.SoftwareCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Update software."""
    check_software_permission(current_user)

    db_software = db.query(models.Software).filter(
        models.Software.id == software_id
    ).first()
    if not db_software:
        raise HTTPException(status_code=404, detail="Software not found")

    for key, value in software.model_dump().items():
        setattr(db_software, key, value)

    db.commit()
    db.refresh(db_software)
    return db_software


@router.delete("/{software_id}")
def delete_software(
    software_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Delete software (software permission required)."""
    check_software_permission(current_user)
    db_software = db.query(models.Software).filter(
        models.Software.id == software_id
    ).first()
    if not db_software:
        raise HTTPException(status_code=404, detail="Software not found")

    db.delete(db_software)
    db.commit()

    logger.info(f"Software '{db_software.name}' deleted by '{current_user.username}'")
    return {"ok": True}


# ==================== LICENSES ====================

@router.get("/{software_id}/licenses", response_model=List[schemas.SoftwareLicense])
def list_licenses(
    software_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """List licenses for a software."""
    check_software_permission(current_user)

    return db.query(models.SoftwareLicense).filter(
        models.SoftwareLicense.software_id == software_id
    ).all()


@router.get("/licenses/expiring", response_model=List[schemas.ExpirationAlert])
def get_expiring_licenses(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get licenses expiring within specified days (optimized with join)."""
    check_software_permission(current_user)

    today = date.today()
    threshold = today + timedelta(days=days)

    # Use joinedload to fetch software in single query
    licenses = db.query(models.SoftwareLicense).options(
        joinedload(models.SoftwareLicense.software)
    ).filter(
        models.SoftwareLicense.expiry_date.isnot(None),
        models.SoftwareLicense.expiry_date >= today,
        models.SoftwareLicense.expiry_date <= threshold
    ).order_by(models.SoftwareLicense.expiry_date).limit(limit).all()

    alerts = []
    for lic in licenses:
        days_remaining = (lic.expiry_date - today).days
        severity = "critical" if days_remaining <= 7 else "warning" if days_remaining <= 14 else "info"

        alerts.append(schemas.ExpirationAlert(
            type="license",
            item_id=lic.id,
            item_name=lic.software.name if lic.software else f"License #{lic.id}",
            expiry_date=lic.expiry_date,
            days_remaining=days_remaining,
            severity=severity
        ))

    return alerts


@router.post("/{software_id}/licenses", response_model=schemas.SoftwareLicense)
def create_license(
    software_id: int,
    license: schemas.SoftwareLicenseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Create a new license."""
    check_software_permission(current_user)

    # Verify software exists
    software = db.query(models.Software).filter(
        models.Software.id == software_id
    ).first()
    if not software:
        raise HTTPException(status_code=404, detail="Software not found")

    license_data = license.model_dump()
    license_data["software_id"] = software_id

    # Encrypt license key if provided
    if license_data.get("license_key"):
        license_data["license_key"] = encrypt_value(license_data["license_key"])

    db_license = models.SoftwareLicense(**license_data)
    db.add(db_license)
    db.commit()
    db.refresh(db_license)

    logger.info(
        f"License for '{software.name}' created by '{current_user.username}'"
    )
    return db_license


@router.delete("/licenses/{license_id}")
def delete_license(
    license_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Delete a license (software permission required)."""
    check_software_permission(current_user)
    db_license = db.query(models.SoftwareLicense).filter(
        models.SoftwareLicense.id == license_id
    ).first()
    if not db_license:
        raise HTTPException(status_code=404, detail="License not found")

    db.delete(db_license)
    db.commit()

    return {"ok": True}


# ==================== INSTALLATIONS ====================

@router.get("/{software_id}/installations", response_model=List[schemas.SoftwareInstallation])
def list_installations(
    software_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """List installations for a software."""
    check_software_permission(current_user)

    return db.query(models.SoftwareInstallation).filter(
        models.SoftwareInstallation.software_id == software_id
    ).all()


@router.post("/{software_id}/installations", response_model=schemas.SoftwareInstallation)
def create_installation(
    software_id: int,
    installation: schemas.SoftwareInstallationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Record a software installation."""
    check_software_permission(current_user)

    # Verify software exists
    software = db.query(models.Software).filter(
        models.Software.id == software_id
    ).first()
    if not software:
        raise HTTPException(status_code=404, detail="Software not found")

    # Verify equipment exists
    equipment = db.query(models.Equipment).filter(
        models.Equipment.id == installation.equipment_id
    ).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    # Check if already installed
    existing = db.query(models.SoftwareInstallation).filter(
        models.SoftwareInstallation.software_id == software_id,
        models.SoftwareInstallation.equipment_id == installation.equipment_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Software already installed on this equipment"
        )

    installation_data = installation.model_dump()
    installation_data["software_id"] = software_id

    db_installation = models.SoftwareInstallation(**installation_data)
    db.add(db_installation)
    db.commit()
    db.refresh(db_installation)

    logger.info(
        f"'{software.name}' installation on '{equipment.name}' "
        f"recorded by '{current_user.username}'"
    )
    return db_installation


@router.delete("/installations/{installation_id}")
def delete_installation(
    installation_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Remove an installation record."""
    check_software_permission(current_user)

    db_installation = db.query(models.SoftwareInstallation).filter(
        models.SoftwareInstallation.id == installation_id
    ).first()
    if not db_installation:
        raise HTTPException(status_code=404, detail="Installation not found")

    db.delete(db_installation)
    db.commit()

    return {"ok": True}
