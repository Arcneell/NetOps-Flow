"""
Audit Logging Utilities
Centralized audit trail for all critical operations.
"""
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from backend import models

logger = logging.getLogger(__name__)


def log_audit_event(
    db: Session,
    user: models.User,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    changes: Optional[Dict[str, Any]] = None,
    extra_data: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
) -> None:
    """
    Log an audit event to the database.

    Args:
        db: Database session
        user: User performing the action
        action: Action type (CREATE, UPDATE, DELETE, LOGIN, LOGOUT, etc.)
        resource_type: Type of resource (equipment, subnet, user, etc.)
        resource_id: ID of the affected resource
        changes: Dictionary of changes (for UPDATE actions)
        extra_data: Additional context information
        ip_address: Client IP address
    """
    try:
        audit_entry = models.AuditLog(
            user_id=user.id if user else None,
            username=user.username if user else "system",
            action=action.upper(),
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            entity_id=user.entity_id if user else None,
            ip_address=ip_address,
            changes=changes or {},
            extra_data=extra_data or {}
        )
        db.add(audit_entry)
        db.commit()
        logger.info(
            f"Audit log: {action} on {resource_type}#{resource_id} by {user.username if user else 'system'}"
        )
    except Exception as e:
        logger.error(f"Failed to create audit log entry: {e}")
        # Don't fail the main operation if audit logging fails
        db.rollback()


def get_audit_logs(
    db: Session,
    limit: int = 100,
    offset: int = 0,
    user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    action: Optional[str] = None,
    entity_id: Optional[int] = None
) -> list[models.AuditLog]:
    """
    Retrieve audit logs with optional filtering.

    Args:
        db: Database session
        limit: Maximum number of logs to return
        offset: Offset for pagination
        user_id: Filter by user ID
        resource_type: Filter by resource type
        action: Filter by action type
        entity_id: Filter by entity ID

    Returns:
        List of audit log entries
    """
    query = db.query(models.AuditLog)

    if user_id:
        query = query.filter(models.AuditLog.user_id == user_id)
    if resource_type:
        query = query.filter(models.AuditLog.resource_type == resource_type)
    if action:
        query = query.filter(models.AuditLog.action == action.upper())
    if entity_id:
        query = query.filter(models.AuditLog.entity_id == entity_id)

    return query.order_by(models.AuditLog.timestamp.desc()).limit(limit).offset(offset).all()
