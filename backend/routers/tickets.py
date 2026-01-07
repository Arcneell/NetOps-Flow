"""
Ticket Management Router for Helpdesk functionality.
Provides full CRUD operations with SLA tracking and workflow management.

Access Control:
- user: Can only see/modify their own tickets
- tech: Can see all tickets, can modify tickets (for resolution)
- admin: Full access to all tickets
- superadmin: Full access to all tickets
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


def can_access_all_tickets(user: models.User) -> bool:
    """Check if user can access all tickets (tech, admin, superadmin)."""
    return user.role in ("tech", "admin", "superadmin")


def can_manage_tickets(user: models.User) -> bool:
    """Check if user can manage tickets (assign, resolve, etc.) - tech, admin, superadmin."""
    return user.role in ("tech", "admin", "superadmin")


def generate_ticket_number() -> str:
    """Generate unique ticket number: TKT-YYYYMMDD-XXXX"""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique_id = uuid.uuid4().hex[:4].upper()
    return f"TKT-{today}-{unique_id}"


def calculate_sla_times(ticket: models.Ticket, db: Session) -> dict:
    """
    Calculate SLA response and resolution times based on priority.
    Supports business hours calculation when configured in SLA policy.
    """
    from backend.core.sla import calculate_sla_due_date

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
        use_business_hours = False
    else:
        sla_config = {
            "critical": {"response": policy.critical_response_time, "resolution": policy.critical_resolution_time},
            "high": {"response": policy.high_response_time, "resolution": policy.high_resolution_time},
            "medium": {"response": policy.medium_response_time, "resolution": policy.medium_resolution_time},
            "low": {"response": policy.low_response_time, "resolution": policy.low_resolution_time}
        }
        use_business_hours = policy.business_hours_only

    priority_sla = sla_config.get(ticket.priority, sla_config["medium"])
    now = datetime.now(timezone.utc)

    # Calculate due dates using business hours if configured
    first_response_due = calculate_sla_due_date(
        now,
        priority_sla["response"],
        policy,
        use_business_hours
    )
    resolution_due = calculate_sla_due_date(
        now,
        priority_sla["resolution"],
        policy,
        use_business_hours
    )

    return {
        "first_response_due": first_response_due,
        "resolution_due": resolution_due,
        "sla_due_date": resolution_due
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

@router.get("/", response_model=schemas.PaginatedTicketResponse)
def list_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    ticket_type: Optional[str] = None,
    assigned_to_id: Optional[int] = None,
    requester_id: Optional[int] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    my_tickets: bool = False,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List tickets with filtering options. Returns paginated response with total count."""
    # Base count query (without joins)
    count_query = db.query(func.count(models.Ticket.id))

    # Data query with joins
    query = db.query(models.Ticket).options(
        joinedload(models.Ticket.requester),
        joinedload(models.Ticket.assigned_to)
    )

    # Users can only see their own tickets, tech/admin/superadmin can see all
    if not can_access_all_tickets(current_user):
        query = query.filter(models.Ticket.requester_id == current_user.id)
        count_query = count_query.filter(models.Ticket.requester_id == current_user.id)
    # Entity filtering for privileged users with entity
    elif current_user.entity_id:
        query = query.filter(models.Ticket.entity_id == current_user.entity_id)
        count_query = count_query.filter(models.Ticket.entity_id == current_user.entity_id)

    # Filter by my tickets (assigned or requested) - only relevant for tech/admin/superadmin
    if my_tickets and can_access_all_tickets(current_user):
        my_filter = or_(
            models.Ticket.assigned_to_id == current_user.id,
            models.Ticket.requester_id == current_user.id
        )
        query = query.filter(my_filter)
        count_query = count_query.filter(my_filter)

    # Apply filters
    if status:
        query = query.filter(models.Ticket.status == status)
        count_query = count_query.filter(models.Ticket.status == status)
    if priority:
        query = query.filter(models.Ticket.priority == priority)
        count_query = count_query.filter(models.Ticket.priority == priority)
    if ticket_type:
        query = query.filter(models.Ticket.ticket_type == ticket_type)
        count_query = count_query.filter(models.Ticket.ticket_type == ticket_type)
    if assigned_to_id:
        query = query.filter(models.Ticket.assigned_to_id == assigned_to_id)
        count_query = count_query.filter(models.Ticket.assigned_to_id == assigned_to_id)
    if requester_id:
        query = query.filter(models.Ticket.requester_id == requester_id)
        count_query = count_query.filter(models.Ticket.requester_id == requester_id)
    if category:
        query = query.filter(models.Ticket.category == category)
        count_query = count_query.filter(models.Ticket.category == category)
    if search:
        search_term = f"%{search}%"
        search_filter = or_(
            models.Ticket.title.ilike(search_term),
            models.Ticket.ticket_number.ilike(search_term),
            models.Ticket.description.ilike(search_term)
        )
        query = query.filter(search_filter)
        count_query = count_query.filter(search_filter)

    # Get total count
    total = count_query.scalar() or 0

    # Get paginated results
    tickets = query.order_by(models.Ticket.created_at.desc()).offset(skip).limit(limit).all()

    # Map to brief response
    items = []
    for t in tickets:
        items.append(schemas.TicketBrief(
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

    return schemas.PaginatedTicketResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/stats", response_model=schemas.TicketStats)
def get_ticket_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get ticket statistics for dashboard using optimized SQL aggregations with caching."""
    from sqlalchemy import case, literal_column
    from backend.core.cache import cache_get, cache_set, build_cache_key

    # Build cache key based on user context
    cache_key = build_cache_key(
        "tickets",
        "stats",
        user_id=current_user.id,
        role=current_user.role,
        entity_id=current_user.entity_id
    )

    # Try to get from cache first (TTL: 2 minutes for stats)
    cached_stats = cache_get(cache_key)
    if cached_stats:
        return schemas.TicketStats(**cached_stats)

    # Build base query with filters
    base_filter = []
    if not can_access_all_tickets(current_user):
        base_filter.append(models.Ticket.requester_id == current_user.id)
    elif current_user.entity_id:
        base_filter.append(models.Ticket.entity_id == current_user.entity_id)

    # Count total tickets
    total_query = db.query(func.count(models.Ticket.id))
    if base_filter:
        total_query = total_query.filter(*base_filter)
    total = total_query.scalar() or 0

    # Aggregate by status using CASE expressions
    status_counts = db.query(
        func.sum(case((models.Ticket.status == "new", 1), else_=0)).label("new"),
        func.sum(case((models.Ticket.status == "open", 1), else_=0)).label("open"),
        func.sum(case((models.Ticket.status == "pending", 1), else_=0)).label("pending"),
        func.sum(case((models.Ticket.status == "resolved", 1), else_=0)).label("resolved"),
        func.sum(case((models.Ticket.status == "closed", 1), else_=0)).label("closed"),
        func.sum(case((models.Ticket.sla_breached == True, 1), else_=0)).label("sla_breached")
    )
    if base_filter:
        status_counts = status_counts.filter(*base_filter)
    status_result = status_counts.first()

    # Aggregate by priority
    priority_counts = db.query(
        func.sum(case((models.Ticket.priority == "critical", 1), else_=0)).label("critical"),
        func.sum(case((models.Ticket.priority == "high", 1), else_=0)).label("high"),
        func.sum(case((models.Ticket.priority == "medium", 1), else_=0)).label("medium"),
        func.sum(case((models.Ticket.priority == "low", 1), else_=0)).label("low")
    )
    if base_filter:
        priority_counts = priority_counts.filter(*base_filter)
    priority_result = priority_counts.first()

    # Aggregate by type
    type_counts = db.query(
        func.sum(case((models.Ticket.ticket_type == "incident", 1), else_=0)).label("incident"),
        func.sum(case((models.Ticket.ticket_type == "request", 1), else_=0)).label("request"),
        func.sum(case((models.Ticket.ticket_type == "problem", 1), else_=0)).label("problem"),
        func.sum(case((models.Ticket.ticket_type == "change", 1), else_=0)).label("change")
    )
    if base_filter:
        type_counts = type_counts.filter(*base_filter)
    type_result = type_counts.first()

    stats_data = {
        "total": total,
        "new": int(status_result.new or 0),
        "open": int(status_result.open or 0),
        "pending": int(status_result.pending or 0),
        "resolved": int(status_result.resolved or 0),
        "closed": int(status_result.closed or 0),
        "sla_breached": int(status_result.sla_breached or 0),
        "by_priority": {
            "critical": int(priority_result.critical or 0),
            "high": int(priority_result.high or 0),
            "medium": int(priority_result.medium or 0),
            "low": int(priority_result.low or 0)
        },
        "by_type": {
            "incident": int(type_result.incident or 0),
            "request": int(type_result.request or 0),
            "problem": int(type_result.problem or 0),
            "change": int(type_result.change or 0)
        }
    }

    # Cache the stats for 2 minutes
    cache_set(cache_key, stats_data, expire_seconds=120)

    return schemas.TicketStats(**stats_data)


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

    # Access control: users can only view their own tickets, tech/admin/superadmin can view all
    if not can_access_all_tickets(current_user):
        if ticket.requester_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
    # Entity check for privileged users
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
            username=c.user.username if c.user else None,
            user_avatar=c.user.avatar if c.user else None
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
    # Note: ticket_number is auto-generated by SQLAlchemy before_insert hook in models.py

    # Create ticket
    ticket = models.Ticket(
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

    # Access control: users can only update their own tickets with limited fields
    # tech/admin/superadmin can update all tickets with all fields
    if not can_manage_tickets(current_user):
        if ticket.requester_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        # Regular users can only update limited fields
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
    """Delete a ticket (admin/superadmin only)."""
    if current_user.role not in ("admin", "superadmin"):
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

    # Access control: users can only comment on their own tickets
    # tech/admin/superadmin can comment on all tickets
    if not can_access_all_tickets(current_user):
        if ticket.requester_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        # Regular users cannot post internal comments or mark as resolution
        if comment_data.is_internal or comment_data.is_resolution:
            raise HTTPException(status_code=403, detail="Only tech/admin can post internal comments or resolutions")

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
            username=c.user.username if c.user else None,
            user_avatar=c.user.avatar if c.user else None
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
    """Assign ticket to a user. Requires tech, admin or superadmin role."""
    # Permission check: only tech, admin, superadmin can assign tickets
    if not can_manage_tickets(current_user):
        raise HTTPException(status_code=403, detail="Permission denied: only tech, admin or superadmin can assign tickets")

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
    """Mark ticket as resolved. Requires tech, admin or superadmin role."""
    # Permission check: only tech, admin, superadmin can resolve tickets
    if not can_manage_tickets(current_user):
        raise HTTPException(status_code=403, detail="Permission denied: only tech, admin or superadmin can resolve tickets")

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
    """Close a resolved ticket. Requires tech, admin or superadmin role."""
    # Permission check: only tech, admin, superadmin can close tickets
    if not can_manage_tickets(current_user):
        raise HTTPException(status_code=403, detail="Permission denied: only tech, admin or superadmin can close tickets")

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
    """Reopen a closed/resolved ticket. Requires tech, admin or superadmin role."""
    # Permission check: only tech, admin, superadmin can reopen tickets
    if not can_manage_tickets(current_user):
        raise HTTPException(status_code=403, detail="Permission denied: only tech, admin or superadmin can reopen tickets")

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


# ==================== TICKET TEMPLATES ====================

@router.get("/templates/", response_model=List[schemas.TicketTemplate])
def list_ticket_templates(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    List available ticket templates.

    Regular users see only public active templates.
    Tech/admin/superadmin see all templates.
    """
    query = db.query(models.TicketTemplate)

    # Apply visibility filter
    if not can_manage_tickets(current_user):
        query = query.filter(
            models.TicketTemplate.is_public == True,
            models.TicketTemplate.is_active == True
        )
    elif active_only:
        query = query.filter(models.TicketTemplate.is_active == True)

    # Apply entity filter
    if current_user.entity_id:
        query = query.filter(
            (models.TicketTemplate.entity_id == None) |
            (models.TicketTemplate.entity_id == current_user.entity_id)
        )

    return query.order_by(models.TicketTemplate.name).all()


@router.get("/templates/{template_id}", response_model=schemas.TicketTemplate)
def get_ticket_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get a specific ticket template."""
    template = db.query(models.TicketTemplate).filter(
        models.TicketTemplate.id == template_id
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Check visibility
    if not can_manage_tickets(current_user):
        if not template.is_public or not template.is_active:
            raise HTTPException(status_code=403, detail="Access denied")

    # Check entity access
    if current_user.entity_id and template.entity_id:
        if template.entity_id != current_user.entity_id:
            raise HTTPException(status_code=403, detail="Access denied")

    return template


@router.post("/templates/", response_model=schemas.TicketTemplate)
def create_ticket_template(
    template_data: schemas.TicketTemplateCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new ticket template (tech/admin/superadmin only)."""
    if not can_manage_tickets(current_user):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Check for duplicate name
    existing = db.query(models.TicketTemplate).filter(
        models.TicketTemplate.name == template_data.name
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Template with this name already exists")

    template = models.TicketTemplate(
        **template_data.model_dump(),
        created_by_id=current_user.id
    )

    db.add(template)
    db.commit()
    db.refresh(template)

    logger.info(f"Ticket template '{template.name}' created by {current_user.username}")
    return template


@router.put("/templates/{template_id}", response_model=schemas.TicketTemplate)
def update_ticket_template(
    template_id: int,
    template_data: schemas.TicketTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update a ticket template (tech/admin/superadmin only)."""
    if not can_manage_tickets(current_user):
        raise HTTPException(status_code=403, detail="Permission denied")

    template = db.query(models.TicketTemplate).filter(
        models.TicketTemplate.id == template_id
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Check for duplicate name if name is being changed
    if template_data.name and template_data.name != template.name:
        existing = db.query(models.TicketTemplate).filter(
            models.TicketTemplate.name == template_data.name
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Template with this name already exists")

    # Update fields
    for key, value in template_data.model_dump(exclude_unset=True).items():
        setattr(template, key, value)

    db.commit()
    db.refresh(template)

    logger.info(f"Ticket template '{template.name}' updated by {current_user.username}")
    return template


@router.delete("/templates/{template_id}")
def delete_ticket_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Delete a ticket template (admin/superadmin only)."""
    if current_user.role not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Admin access required")

    template = db.query(models.TicketTemplate).filter(
        models.TicketTemplate.id == template_id
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    template_name = template.name
    db.delete(template)
    db.commit()

    logger.info(f"Ticket template '{template_name}' deleted by {current_user.username}")
    return {"message": "Template deleted"}


@router.post("/from-template", response_model=schemas.Ticket)
def create_ticket_from_template(
    request_data: schemas.TicketFromTemplate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Create a ticket from a template.

    Template placeholders in title:
    - {user} - Current user's username
    - {date} - Current date (YYYY-MM-DD)
    """
    from datetime import datetime, timezone

    template = db.query(models.TicketTemplate).filter(
        models.TicketTemplate.id == request_data.template_id,
        models.TicketTemplate.is_active == True
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found or inactive")

    # Check visibility for regular users
    if not can_manage_tickets(current_user) and not template.is_public:
        raise HTTPException(status_code=403, detail="Access denied")

    # Process title template with placeholders
    title = request_data.title or template.title_template
    title = title.replace("{user}", current_user.username)
    title = title.replace("{date}", datetime.now(timezone.utc).strftime("%Y-%m-%d"))

    # Build description
    description = template.description_template or ""
    if request_data.description:
        description = f"{description}\n\n{request_data.description}" if description else request_data.description

    # Create ticket (ticket_number is auto-generated by hook)
    ticket = models.Ticket(
        title=title,
        description=description,
        ticket_type=template.ticket_type,
        category=template.category,
        subcategory=template.subcategory,
        priority=template.priority,
        assigned_group=template.assigned_group,
        requester_id=current_user.id,
        equipment_id=request_data.equipment_id,
        entity_id=current_user.entity_id,
        status="new"
    )

    # Calculate SLA times
    sla_times = calculate_sla_times(ticket, db)
    ticket.first_response_due = sla_times["first_response_due"]
    ticket.resolution_due = sla_times["resolution_due"]
    ticket.sla_due_date = sla_times["sla_due_date"]

    db.add(ticket)

    # Increment template usage count
    template.usage_count += 1

    db.commit()
    db.refresh(ticket)

    # Add creation history
    add_ticket_history(db, ticket.id, current_user.id, "created", extra=f"from template: {template.name}")
    db.commit()

    logger.info(f"Ticket {ticket.ticket_number} created from template '{template.name}' by {current_user.username}")
    return ticket
