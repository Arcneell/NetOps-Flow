"""
Audit Log Router
API endpoints for accessing audit logs (admin only).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from backend.core.database import get_db
from backend.core.security import get_current_user
from backend.core.audit import get_audit_logs
from backend import models

router = APIRouter(prefix="/audit", tags=["Audit Logs"])


class AuditLogResponse(BaseModel):
    """Audit log entry response schema."""
    id: int
    timestamp: datetime
    username: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    entity_id: Optional[int] = None
    ip_address: Optional[str] = None
    changes: Optional[dict] = None
    extra_data: Optional[dict] = None

    class Config:
        from_attributes = True


@router.get("/", response_model=List[AuditLogResponse])
def list_audit_logs(
    limit: int = 100,
    offset: int = 0,
    resource_type: Optional[str] = None,
    action: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Retrieve audit logs (admin only).

    Filters:
    - resource_type: Type of resource (equipment, subnet, user, etc.)
    - action: Action type (CREATE, UPDATE, DELETE, LOGIN, LOGOUT)
    - limit: Maximum number of results (default: 100, max: 500)
    - offset: Pagination offset
    """
    # Only admins can access audit logs
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can access audit logs"
        )

    # Limit maximum results
    if limit > 500:
        limit = 500

    # Regular users see only their entity's logs, admins see all
    entity_filter = None if current_user.role == "admin" else current_user.entity_id

    logs = get_audit_logs(
        db=db,
        limit=limit,
        offset=offset,
        resource_type=resource_type,
        action=action,
        entity_id=entity_filter
    )

    return logs


@router.get("/stats")
def get_audit_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get audit log statistics (admin only).
    Returns counts by action type and resource type.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can access audit statistics"
        )

    from sqlalchemy import func

    # Count by action
    action_counts = db.query(
        models.AuditLog.action,
        func.count(models.AuditLog.id).label("count")
    ).group_by(models.AuditLog.action).all()

    # Count by resource type
    resource_counts = db.query(
        models.AuditLog.resource_type,
        func.count(models.AuditLog.id).label("count")
    ).group_by(models.AuditLog.resource_type).all()

    # Total logs
    total_logs = db.query(func.count(models.AuditLog.id)).scalar()

    return {
        "total_logs": total_logs,
        "by_action": {action: count for action, count in action_counts},
        "by_resource": {resource: count for resource, count in resource_counts}
    }
