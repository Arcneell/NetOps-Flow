"""
Ticket Management Router for Helpdesk functionality.
Provides full CRUD operations with SLA tracking and workflow management.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid
import os
import logging

from backend.core.database import get_db
from backend.core.security import get_current_user
from backend import models, schemas

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tickets", tags=["tickets"])


def generate_ticket_number() -> str:
    """Generate unique ticket number: TKT-YYYYMMDD-XXXX"""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique_id = uuid.uuid4().hex[:4].upper()
    return f"TKT-{today}-{unique_id}"


def calculate_sla_times(ticket: models.Ticket, db: Session) -> dict:
    """Calculate SLA response and resolution times based on priority."""
    # Get default SLA policy or entity-specific
    policy = db.query(models.SLAPolicy).filter(
        or_(
            and_(models.SLAPolicy.entity_id == ticket.entity_id, models.SLAPolicy.is_active == True),
            and_(models.SLAPolicy.is_default == True, models.SLAPolicy.is_active == True)
        )
    ).first()

    if not policy:
        # Default SLA times in minutes
        sla_config = {
            "critical": {"response": 15, "resolution": 240},
            "high": {"response": 60, "resolution": 480},
            "medium": {"response": 240, "resolution": 1440},
            "low": {"response": 480, "resolution": 2880}
        }
    else:
        sla_config = {
            "critical": {"response": policy.critical_response_time, "resolution": policy.critical_resolution_time},
            "high": {"response": policy.high_response_time, "resolution": policy.high_resolution_time},
            "medium": {"response": policy.medium_response_time, "resolution": policy.medium_resolution_time},
            "low": {"response": policy.low_response_time, "resolution": policy.low_resolution_time}
        }

    priority_sla = sla_config.get(ticket.priority, sla_config["medium"])
    now = datetime.now(timezone.utc)

    return {
        "first_response_due": now + timedelta(minutes=priority_sla["response"]),
        "resolution_due": now + timedelta(minutes=priority_sla["resolution"]),
        "sla_due_date": now + timedelta(minutes=priority_sla["resolution"])
    }


def add_ticket_history(
    db: Session,
    ticket_id: int,
    user_id: int,
    action: str,
    field_name: str = None,
    old_value: str = None,
    new_value: str = None
):
    """Add entry to ticket history."""
    history = models.TicketHistory(
        ticket_id=ticket_id,
        user_id=user_id,
        action=action,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value
    )
    db.add(history)


def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    notification_type: str = "ticket",
    link_type: str = None,
    link_id: int = None
):
    """Create a notification for a user."""
    notification = models.Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        link_type=link_type,
        link_id=link_id
    )
    db.add(notification)


# ==================== TICKET CRUD ====================

@router.get("/", response_model=List[schemas.TicketBrief])
def list_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    ticket_type: Optional[str] = None,
    assigned_to_id: Optional[int] = None,
    requester_id: Optional[int] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    my_tickets: bool = False,
    skip: int = 0,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List tickets with filtering options."""
    query = db.query(models.Ticket).options(
        joinedload(models.Ticket.requester),
        joinedload(models.Ticket.assigned_to)
    )

    # Non-admin users can only see their own tickets (created by them)
    if current_user.role != "admin":
        query = query.filter(models.Ticket.requester_id == current_user.id)
    # Entity filtering for admin users with entity
    elif current_user.entity_id:
        query = query.filter(models.Ticket.entity_id == current_user.entity_id)

    # Filter by my tickets (assigned or requested) - only relevant for admins
    if my_tickets and current_user.role == "admin":
        query = query.filter(
            or_(
                models.Ticket.assigned_to_id == current_user.id,
                models.Ticket.requester_id == current_user.id
            )
        )

    # Apply filters
    if status:
        query = query.filter(models.Ticket.status == status)
    if priority:
        query = query.filter(models.Ticket.priority == priority)
    if ticket_type:
        query = query.filter(models.Ticket.ticket_type == ticket_type)
    if assigned_to_id:
        query = query.filter(models.Ticket.assigned_to_id == assigned_to_id)
    if requester_id:
        query = query.filter(models.Ticket.requester_id == requester_id)
    if category:
        query = query.filter(models.Ticket.category == category)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                models.Ticket.title.ilike(search_term),
                models.Ticket.ticket_number.ilike(search_term),
                models.Ticket.description.ilike(search_term)
            )
        )

    tickets = query.order_by(models.Ticket.created_at.desc()).offset(skip).limit(limit).all()

    # Map to brief response
    result = []
    for t in tickets:
        result.append(schemas.TicketBrief(
            id=t.id,
            ticket_number=t.ticket_number,
            title=t.title,
            status=t.status,
            priority=t.priority,
            ticket_type=t.ticket_type,
            created_at=t.created_at,
            requester_name=t.requester.username if t.requester else None,
            assigned_to_name=t.assigned_to.username if t.assigned_to else None
        ))

    return result


@router.get("/stats", response_model=schemas.TicketStats)
def get_ticket_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get ticket statistics for dashboard."""
    query = db.query(models.Ticket)

    # Non-admin users can only see stats for their own tickets
    if current_user.role != "admin":
        query = query.filter(models.Ticket.requester_id == current_user.id)
    elif current_user.entity_id:
        query = query.filter(models.Ticket.entity_id == current_user.entity_id)

    tickets = query.all()

    stats = schemas.TicketStats(
        total=len(tickets),
        new=sum(1 for t in tickets if t.status == "new"),
        open=sum(1 for t in tickets if t.status == "open"),
        pending=sum(1 for t in tickets if t.status == "pending"),
        resolved=sum(1 for t in tickets if t.status == "resolved"),
        closed=sum(1 for t in tickets if t.status == "closed"),
        sla_breached=sum(1 for t in tickets if t.sla_breached),
        by_priority={
            "critical": sum(1 for t in tickets if t.priority == "critical"),
            "high": sum(1 for t in tickets if t.priority == "high"),
            "medium": sum(1 for t in tickets if t.priority == "medium"),
            "low": sum(1 for t in tickets if t.priority == "low")
        },
        by_type={
            "incident": sum(1 for t in tickets if t.ticket_type == "incident"),
            "request": sum(1 for t in tickets if t.ticket_type == "request"),
            "problem": sum(1 for t in tickets if t.ticket_type == "problem"),
            "change": sum(1 for t in tickets if t.ticket_type == "change")
        }
    )

    return stats


@router.get("/{ticket_id}", response_model=schemas.TicketFull)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get ticket with full details including comments and history."""
    ticket = db.query(models.Ticket).options(
        joinedload(models.Ticket.requester),
        joinedload(models.Ticket.assigned_to),
        joinedload(models.Ticket.equipment),
        joinedload(models.Ticket.comments).joinedload(models.TicketComment.user),
        joinedload(models.Ticket.history).joinedload(models.TicketHistory.user),
        joinedload(models.Ticket.attachments)
    ).filter(models.Ticket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Access control: non-admin users can only view their own tickets
    if current_user.role != "admin":
        if ticket.requester_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
    # Entity check for admin users
    elif current_user.entity_id:
        if ticket.entity_id and ticket.entity_id != current_user.entity_id:
            raise HTTPException(status_code=403, detail="Access denied")

    # Build response
    comments_full = [
        schemas.TicketCommentFull(
            id=c.id,
            ticket_id=c.ticket_id,
            user_id=c.user_id,
            content=c.content,
            is_internal=c.is_internal,
            is_resolution=c.is_resolution,
            created_at=c.created_at,
            username=c.user.username if c.user else None
        ) for c in sorted(ticket.comments, key=lambda x: x.created_at)
    ]

    history_items = [
        schemas.TicketHistoryItem(
            id=h.id,
            ticket_id=h.ticket_id,
            user_id=h.user_id,
            action=h.action,
            field_name=h.field_name,
            old_value=h.old_value,
            new_value=h.new_value,
            created_at=h.created_at,
            username=h.user.username if h.user else None
        ) for h in sorted(ticket.history, key=lambda x: x.created_at, reverse=True)
    ]

    attachments_list = [
        schemas.TicketAttachment(
            id=a.id,
            ticket_id=a.ticket_id,
            filename=a.filename,
            original_filename=a.original_filename,
            file_type=a.file_type,
            file_size=a.file_size,
            uploaded_by_id=a.uploaded_by_id,
            uploaded_at=a.uploaded_at
        ) for a in ticket.attachments
    ]

    return schemas.TicketFull(
        id=ticket.id,
        ticket_number=ticket.ticket_number,
        title=ticket.title,
        description=ticket.description,
        ticket_type=ticket.ticket_type,
        category=ticket.category,
        subcategory=ticket.subcategory,
        status=ticket.status,
        priority=ticket.priority,
        impact=ticket.impact,
        urgency=ticket.urgency,
        requester_id=ticket.requester_id,
        assigned_to_id=ticket.assigned_to_id,
        assigned_group=ticket.assigned_group,
        equipment_id=ticket.equipment_id,
        entity_id=ticket.entity_id,
        sla_due_date=ticket.sla_due_date,
        first_response_at=ticket.first_response_at,
        first_response_due=ticket.first_response_due,
        resolution_due=ticket.resolution_due,
        sla_breached=ticket.sla_breached,
        resolution=ticket.resolution,
        resolution_code=ticket.resolution_code,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        resolved_at=ticket.resolved_at,
        closed_at=ticket.closed_at,
        requester_name=ticket.requester.username if ticket.requester else None,
        assigned_to_name=ticket.assigned_to.username if ticket.assigned_to else None,
        equipment_name=ticket.equipment.name if ticket.equipment else None,
        comments=comments_full,
        history=history_items,
        attachments=attachments_list
    )


@router.post("/", response_model=schemas.Ticket)
def create_ticket(
    ticket_data: schemas.TicketCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new ticket."""
    # Generate ticket number
    ticket_number = generate_ticket_number()

    # Create ticket
    ticket = models.Ticket(
        ticket_number=ticket_number,
        title=ticket_data.title,
        description=ticket_data.description,
        ticket_type=ticket_data.ticket_type,
        category=ticket_data.category,
        subcategory=ticket_data.subcategory,
        priority=ticket_data.priority,
        impact=ticket_data.impact,
        urgency=ticket_data.urgency,
        requester_id=current_user.id,
        assigned_to_id=ticket_data.assigned_to_id,
        assigned_group=ticket_data.assigned_group,
        equipment_id=ticket_data.equipment_id,
        entity_id=ticket_data.entity_id or current_user.entity_id,
        status="new"
    )

    # Calculate SLA times
    sla_times = calculate_sla_times(ticket, db)
    ticket.first_response_due = sla_times["first_response_due"]
    ticket.resolution_due = sla_times["resolution_due"]
    ticket.sla_due_date = sla_times["sla_due_date"]

    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    # Add creation history
    add_ticket_history(db, ticket.id, current_user.id, "created")
    db.commit()

    # Notify assigned user if any
    if ticket.assigned_to_id:
        create_notification(
            db,
            ticket.assigned_to_id,
            f"New ticket assigned: {ticket.ticket_number}",
            f"Ticket '{ticket.title}' has been assigned to you.",
            "ticket",
            "ticket",
            ticket.id
        )
        db.commit()

    logger.info(f"Ticket {ticket.ticket_number} created by {current_user.username}")
    return ticket


@router.put("/{ticket_id}", response_model=schemas.Ticket)
def update_ticket(
    ticket_id: int,
    ticket_data: schemas.TicketUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update a ticket. Non-admin users can only update their own tickets with limited fields."""
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Access control: non-admin users can only update their own tickets
    if current_user.role != "admin":
        if ticket.requester_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        # Non-admin users can only update limited fields
        allowed_fields = {"title", "description", "category", "subcategory"}
        update_data_check = ticket_data.model_dump(exclude_unset=True)
        disallowed = set(update_data_check.keys()) - allowed_fields
        if disallowed:
            raise HTTPException(status_code=403, detail=f"You cannot modify: {', '.join(disallowed)}")

    # Track changes for history
    update_data = ticket_data.model_dump(exclude_unset=True)

    for field, new_value in update_data.items():
        old_value = getattr(ticket, field)
        if old_value != new_value:
            # Special handling for status changes
            if field == "status":
                if new_value == "resolved" and not ticket.resolved_at:
                    ticket.resolved_at = datetime.now(timezone.utc)
                elif new_value == "closed" and not ticket.closed_at:
                    ticket.closed_at = datetime.now(timezone.utc)
                elif new_value == "open" and not ticket.first_response_at:
                    ticket.first_response_at = datetime.now(timezone.utc)

            # Record history
            add_ticket_history(
                db, ticket.id, current_user.id,
                "status_changed" if field == "status" else "updated",
                field,
                str(old_value) if old_value else None,
                str(new_value) if new_value else None
            )

            # Notify on assignment change
            if field == "assigned_to_id" and new_value:
                create_notification(
                    db,
                    new_value,
                    f"Ticket assigned: {ticket.ticket_number}",
                    f"Ticket '{ticket.title}' has been assigned to you.",
                    "ticket",
                    "ticket",
                    ticket.id
                )

            setattr(ticket, field, new_value)

    # Recalculate SLA if priority changed
    if "priority" in update_data:
        sla_times = calculate_sla_times(ticket, db)
        ticket.first_response_due = sla_times["first_response_due"]
        ticket.resolution_due = sla_times["resolution_due"]
        ticket.sla_due_date = sla_times["sla_due_date"]

    db.commit()
    db.refresh(ticket)

    logger.info(f"Ticket {ticket.ticket_number} updated by {current_user.username}")
    return ticket


@router.delete("/{ticket_id}")
def delete_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Delete a ticket (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket_number = ticket.ticket_number
    db.delete(ticket)
    db.commit()

    logger.info(f"Ticket {ticket_number} deleted by {current_user.username}")
    return {"message": f"Ticket {ticket_number} deleted"}


# ==================== TICKET COMMENTS ====================

@router.post("/{ticket_id}/comments", response_model=schemas.TicketComment)
def add_comment(
    ticket_id: int,
    comment_data: schemas.TicketCommentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Add a comment to a ticket."""
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Access control: non-admin users can only comment on their own tickets
    if current_user.role != "admin":
        if ticket.requester_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        # Non-admin users cannot post internal comments or mark as resolution
        if comment_data.is_internal or comment_data.is_resolution:
            raise HTTPException(status_code=403, detail="Only admins can post internal comments or resolutions")

    comment = models.TicketComment(
        ticket_id=ticket_id,
        user_id=current_user.id,
        content=comment_data.content,
        is_internal=comment_data.is_internal,
        is_resolution=comment_data.is_resolution
    )
    db.add(comment)

    # Record first response if this is the first comment from non-requester
    if not ticket.first_response_at and current_user.id != ticket.requester_id:
        ticket.first_response_at = datetime.now(timezone.utc)

    # Add history entry
    add_ticket_history(db, ticket_id, current_user.id, "commented")

    # Mark as resolution if specified
    if comment_data.is_resolution:
        ticket.resolution = comment_data.content
        ticket.status = "resolved"
        ticket.resolved_at = datetime.now(timezone.utc)
        add_ticket_history(db, ticket_id, current_user.id, "resolved")

    db.commit()
    db.refresh(comment)

    # Notify relevant parties
    notify_users = set()
    if ticket.requester_id and ticket.requester_id != current_user.id:
        notify_users.add(ticket.requester_id)
    if ticket.assigned_to_id and ticket.assigned_to_id != current_user.id:
        notify_users.add(ticket.assigned_to_id)

    for user_id in notify_users:
        create_notification(
            db,
            user_id,
            f"New comment on {ticket.ticket_number}",
            f"{current_user.username} added a comment.",
            "ticket",
            "ticket",
            ticket.id
        )
    db.commit()

    return comment


@router.get("/{ticket_id}/comments", response_model=List[schemas.TicketCommentFull])
def get_comments(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get all comments for a ticket."""
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    comments = db.query(models.TicketComment).options(
        joinedload(models.TicketComment.user)
    ).filter(
        models.TicketComment.ticket_id == ticket_id
    ).order_by(models.TicketComment.created_at).all()

    return [
        schemas.TicketCommentFull(
            id=c.id,
            ticket_id=c.ticket_id,
            user_id=c.user_id,
            content=c.content,
            is_internal=c.is_internal,
            is_resolution=c.is_resolution,
            created_at=c.created_at,
            username=c.user.username if c.user else None
        ) for c in comments
    ]


# ==================== TICKET HISTORY ====================

@router.get("/{ticket_id}/history", response_model=List[schemas.TicketHistoryItem])
def get_history(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get ticket history/audit trail."""
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    history = db.query(models.TicketHistory).options(
        joinedload(models.TicketHistory.user)
    ).filter(
        models.TicketHistory.ticket_id == ticket_id
    ).order_by(models.TicketHistory.created_at.desc()).all()

    return [
        schemas.TicketHistoryItem(
            id=h.id,
            ticket_id=h.ticket_id,
            user_id=h.user_id,
            action=h.action,
            field_name=h.field_name,
            old_value=h.old_value,
            new_value=h.new_value,
            created_at=h.created_at,
            username=h.user.username if h.user else None
        ) for h in history
    ]


# ==================== QUICK ACTIONS ====================

@router.post("/{ticket_id}/assign")
def assign_ticket(
    ticket_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Assign ticket to a user."""
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Verify assignee exists
    assignee = db.query(models.User).filter(models.User.id == user_id).first()
    if not assignee:
        raise HTTPException(status_code=404, detail="User not found")

    old_assignee = ticket.assigned_to_id
    ticket.assigned_to_id = user_id

    if ticket.status == "new":
        ticket.status = "open"

    add_ticket_history(
        db, ticket_id, current_user.id, "assigned",
        "assigned_to_id",
        str(old_assignee) if old_assignee else None,
        str(user_id)
    )

    # Notify new assignee
    create_notification(
        db,
        user_id,
        f"Ticket assigned: {ticket.ticket_number}",
        f"Ticket '{ticket.title}' has been assigned to you by {current_user.username}.",
        "ticket",
        "ticket",
        ticket.id
    )

    db.commit()
    return {"message": f"Ticket assigned to {assignee.username}"}


@router.post("/{ticket_id}/resolve")
def resolve_ticket(
    ticket_id: int,
    resolution: str,
    resolution_code: str = "fixed",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Mark ticket as resolved."""
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket.status = "resolved"
    ticket.resolution = resolution
    ticket.resolution_code = resolution_code
    ticket.resolved_at = datetime.now(timezone.utc)

    add_ticket_history(db, ticket_id, current_user.id, "resolved")

    # Notify requester
    if ticket.requester_id:
        create_notification(
            db,
            ticket.requester_id,
            f"Ticket resolved: {ticket.ticket_number}",
            f"Your ticket '{ticket.title}' has been resolved.",
            "success",
            "ticket",
            ticket.id
        )

    db.commit()
    return {"message": "Ticket resolved"}


@router.post("/{ticket_id}/close")
def close_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Close a resolved ticket."""
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if ticket.status not in ["resolved", "closed"]:
        raise HTTPException(status_code=400, detail="Only resolved tickets can be closed")

    ticket.status = "closed"
    ticket.closed_at = datetime.now(timezone.utc)

    add_ticket_history(db, ticket_id, current_user.id, "closed")
    db.commit()

    return {"message": "Ticket closed"}


@router.post("/{ticket_id}/reopen")
def reopen_ticket(
    ticket_id: int,
    reason: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Reopen a closed/resolved ticket."""
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    old_status = ticket.status
    ticket.status = "open"
    ticket.resolved_at = None
    ticket.closed_at = None

    add_ticket_history(
        db, ticket_id, current_user.id, "reopened",
        "status", old_status, "open"
    )

    if reason:
        comment = models.TicketComment(
            ticket_id=ticket_id,
            user_id=current_user.id,
            content=f"Ticket reopened: {reason}",
            is_internal=True
        )
        db.add(comment)

    # Notify assigned user
    if ticket.assigned_to_id:
        create_notification(
            db,
            ticket.assigned_to_id,
            f"Ticket reopened: {ticket.ticket_number}",
            f"Ticket '{ticket.title}' has been reopened.",
            "warning",
            "ticket",
            ticket.id
        )

    db.commit()
    return {"message": "Ticket reopened"}
