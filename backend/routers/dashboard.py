"""
Dashboard Router - Statistics, alerts and overview.
With Redis caching for performance optimization.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta, date, timezone

from backend.core.database import get_db
from backend.core.security import get_current_active_user
from backend.core.cache import cache_get, cache_set, build_cache_key
from backend import models

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# Cache expiration in seconds (5 minutes)
DASHBOARD_CACHE_TTL = 300


@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get comprehensive dashboard statistics with caching."""

    # Try to get from cache first
    cache_key = build_cache_key("dashboard", "stats")
    cached_data = cache_get(cache_key)
    if cached_data:
        return cached_data

    # Basic counts
    subnets_count = db.query(models.Subnet).count()
    ips_total = db.query(models.IPAddress).count()
    ips_active = db.query(models.IPAddress).filter(models.IPAddress.status == "active").count()
    scripts_count = db.query(models.Script).count()
    executions_count = db.query(models.ScriptExecution).count()
    equipment_count = db.query(models.Equipment).count()

    # Equipment by status
    equipment_in_service = db.query(models.Equipment).filter(models.Equipment.status == "in_service").count()
    equipment_in_stock = db.query(models.Equipment).filter(models.Equipment.status == "in_stock").count()
    equipment_maintenance = db.query(models.Equipment).filter(models.Equipment.status == "maintenance").count()
    equipment_retired = db.query(models.Equipment).filter(models.Equipment.status == "retired").count()

    # DCIM
    racks_count = db.query(models.Rack).count()
    pdus_count = db.query(models.PDU).count()

    # Contracts
    contracts_total = db.query(models.Contract).count()
    today = date.today()
    contracts_active = db.query(models.Contract).filter(
        and_(models.Contract.start_date <= today, models.Contract.end_date >= today)
    ).count()

    # Contracts expiring in next 30 days
    thirty_days = today + timedelta(days=30)
    contracts_expiring = db.query(models.Contract).filter(
        and_(
            models.Contract.end_date >= today,
            models.Contract.end_date <= thirty_days
        )
    ).count()

    # Software & Licenses
    software_count = db.query(models.Software).count()
    licenses_count = db.query(models.SoftwareLicense).count()
    installations_count = db.query(models.SoftwareInstallation).count()

    # License compliance calculation
    software_with_licenses = db.query(
        models.Software.id,
        func.coalesce(func.sum(models.SoftwareLicense.quantity), 0).label('total_licenses')
    ).outerjoin(models.SoftwareLicense).group_by(models.Software.id).subquery()

    software_with_installations = db.query(
        models.Software.id,
        func.count(models.SoftwareInstallation.id).label('total_installations')
    ).outerjoin(models.SoftwareInstallation).group_by(models.Software.id).subquery()

    # Count violations (installations > licenses)
    license_violations = 0
    for software in db.query(models.Software).all():
        total_licenses = sum(l.quantity for l in software.licenses)
        total_installations = len(software.installations)
        if total_installations > total_licenses and total_licenses > 0:
            license_violations += 1

    # Expiring licenses (next 30 days)
    licenses_expiring = db.query(models.SoftwareLicense).filter(
        and_(
            models.SoftwareLicense.expiry_date >= today,
            models.SoftwareLicense.expiry_date <= thirty_days
        )
    ).count()

    # Network ports
    network_ports_count = db.query(models.NetworkPort).count()
    ports_connected = db.query(models.NetworkPort).filter(
        models.NetworkPort.connected_to_id.isnot(None)
    ).count()

    # Locations & Suppliers
    locations_count = db.query(models.Location).count()
    suppliers_count = db.query(models.Supplier).count()
    manufacturers_count = db.query(models.Manufacturer).count()

    # Users
    users_count = db.query(models.User).filter(models.User.is_active == True).count()

    # Recent script executions (last 7 days)
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_executions = db.query(models.ScriptExecution).filter(
        models.ScriptExecution.started_at >= seven_days_ago
    ).count()

    executions_success = db.query(models.ScriptExecution).filter(
        and_(
            models.ScriptExecution.started_at >= seven_days_ago,
            models.ScriptExecution.status == "success"
        )
    ).count()

    executions_failed = db.query(models.ScriptExecution).filter(
        and_(
            models.ScriptExecution.started_at >= seven_days_ago,
            models.ScriptExecution.status == "failure"
        )
    ).count()

    # Warranty expiring (next 30 days)
    now = datetime.now(timezone.utc)
    warranty_expiring = db.query(models.Equipment).filter(
        and_(
            models.Equipment.warranty_expiry >= now,
            models.Equipment.warranty_expiry <= now + timedelta(days=30)
        )
    ).count()

    stats = {
        # Network
        "subnets": subnets_count,
        "ips_total": ips_total,
        "ips_active": ips_active,

        # Scripts
        "scripts": scripts_count,
        "executions": executions_count,
        "recent_executions": recent_executions,
        "executions_success": executions_success,
        "executions_failed": executions_failed,

        # Equipment
        "equipment": equipment_count,
        "equipment_in_service": equipment_in_service,
        "equipment_in_stock": equipment_in_stock,
        "equipment_maintenance": equipment_maintenance,
        "equipment_retired": equipment_retired,
        "warranty_expiring": warranty_expiring,

        # DCIM
        "racks": racks_count,
        "pdus": pdus_count,

        # Contracts
        "contracts_total": contracts_total,
        "contracts_active": contracts_active,
        "contracts_expiring": contracts_expiring,

        # Software
        "software": software_count,
        "licenses": licenses_count,
        "installations": installations_count,
        "license_violations": license_violations,
        "licenses_expiring": licenses_expiring,

        # Network
        "network_ports": network_ports_count,
        "ports_connected": ports_connected,

        # Configuration
        "locations": locations_count,
        "suppliers": suppliers_count,
        "manufacturers": manufacturers_count,

        # Users
        "users": users_count
    }

    # Cache the result
    cache_set(cache_key, stats, DASHBOARD_CACHE_TTL)

    return stats


@router.get("/alerts")
def get_alerts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get dashboard alerts for contracts, licenses, warranties expiring soon."""
    alerts = []
    today = date.today()
    now = datetime.now(timezone.utc)
    thirty_days = today + timedelta(days=30)
    thirty_days_dt = now + timedelta(days=30)

    # Expiring contracts
    expiring_contracts = db.query(models.Contract).filter(
        and_(
            models.Contract.end_date >= today,
            models.Contract.end_date <= thirty_days
        )
    ).order_by(models.Contract.end_date).limit(5).all()

    for contract in expiring_contracts:
        days_remaining = (contract.end_date - today).days
        alerts.append({
            "type": "contract",
            "severity": "danger" if days_remaining <= 7 else "warning",
            "title": contract.name,
            "message": f"{days_remaining} days remaining",
            "link": f"/contracts?id={contract.id}",
            "id": contract.id
        })

    # Expiring licenses
    expiring_licenses = db.query(models.SoftwareLicense).filter(
        and_(
            models.SoftwareLicense.expiry_date >= today,
            models.SoftwareLicense.expiry_date <= thirty_days
        )
    ).order_by(models.SoftwareLicense.expiry_date).limit(5).all()

    for license in expiring_licenses:
        days_remaining = (license.expiry_date - today).days
        software_id = license.software.id if license.software else None
        alerts.append({
            "type": "license",
            "severity": "danger" if days_remaining <= 7 else "warning",
            "title": license.software.name if license.software else "License",
            "message": f"{days_remaining} days remaining",
            "link": f"/software?id={software_id}" if software_id else "/software",
            "id": license.id
        })

    # Expiring warranties
    expiring_warranties = db.query(models.Equipment).filter(
        and_(
            models.Equipment.warranty_expiry >= now,
            models.Equipment.warranty_expiry <= thirty_days_dt
        )
    ).order_by(models.Equipment.warranty_expiry).limit(5).all()

    for eq in expiring_warranties:
        days_remaining = (eq.warranty_expiry.date() - today).days
        alerts.append({
            "type": "warranty",
            "severity": "danger" if days_remaining <= 7 else "warning",
            "title": eq.name,
            "message": f"{days_remaining} days remaining",
            "link": f"/inventory?equipment={eq.id}",
            "id": eq.id
        })

    # License violations
    for software in db.query(models.Software).all():
        total_licenses = sum(l.quantity for l in software.licenses)
        total_installations = len(software.installations)
        if total_installations > total_licenses and total_licenses > 0:
            alerts.append({
                "type": "violation",
                "severity": "danger",
                "title": software.name,
                "message": f"{total_installations} installs / {total_licenses} licenses",
                "link": f"/software?id={software.id}",
                "id": software.id
            })

    # Equipment in maintenance
    maintenance_equipment = db.query(models.Equipment).filter(
        models.Equipment.status == "maintenance"
    ).limit(5).all()

    for eq in maintenance_equipment:
        alerts.append({
            "type": "maintenance",
            "severity": "info",
            "title": eq.name,
            "message": "In maintenance",
            "link": f"/inventory?equipment={eq.id}",
            "id": eq.id
        })

    return alerts[:15]  # Limit to 15 alerts


@router.get("/recent-activity")
def get_recent_activity(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get recent activity (script executions, equipment changes)."""
    activities = []

    # Recent script executions
    recent_executions = db.query(models.ScriptExecution).order_by(
        models.ScriptExecution.started_at.desc()
    ).limit(10).all()

    for exec in recent_executions:
        activities.append({
            "type": "execution",
            "icon": "pi-play" if exec.status == "running" else ("pi-check" if exec.status == "success" else "pi-times"),
            "color": "blue" if exec.status == "running" else ("green" if exec.status == "success" else "red"),
            "title": exec.script.name if exec.script else "Unknown Script",
            "description": f"Status: {exec.status}",
            "timestamp": exec.started_at.isoformat() if exec.started_at else None,
            "link": "/scripts"
        })

    # Recent equipment
    recent_equipment = db.query(models.Equipment).order_by(
        models.Equipment.created_at.desc()
    ).limit(5).all()

    for eq in recent_equipment:
        activities.append({
            "type": "equipment",
            "icon": "pi-box",
            "color": "cyan",
            "title": eq.name,
            "description": f"Added to inventory",
            "timestamp": eq.created_at.isoformat() if eq.created_at else None,
            "link": "/inventory"
        })

    # Sort by timestamp
    activities.sort(key=lambda x: x["timestamp"] or "", reverse=True)

    return activities[:10]
