"""
Webhooks Router - External integration via event-driven webhooks.
Supports CRUD operations for webhooks and webhook delivery management.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, HttpUrl
import hashlib
import hmac
import httpx
import json
import logging
import time

from backend.core.database import get_db
from backend.core.security import get_current_admin_user
from backend import models

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# ==================== PYDANTIC MODELS ====================

class WebhookCreate(BaseModel):
    """Schema for creating a webhook."""
    name: str
    url: str
    secret: Optional[str] = None
    events: List[str]  # e.g., ["ticket.created", "ticket.updated", "equipment.created"]
    is_active: bool = True
    retry_count: int = 3
    timeout_seconds: int = 30


class WebhookUpdate(BaseModel):
    """Schema for updating a webhook."""
    name: Optional[str] = None
    url: Optional[str] = None
    secret: Optional[str] = None
    events: Optional[List[str]] = None
    is_active: Optional[bool] = None
    retry_count: Optional[int] = None
    timeout_seconds: Optional[int] = None


class WebhookResponse(BaseModel):
    """Response schema for webhook."""
    id: int
    name: str
    url: str
    events: List[str]
    is_active: bool
    retry_count: int
    timeout_seconds: int
    last_triggered: Optional[datetime] = None
    last_status_code: Optional[int] = None
    failure_count: int
    success_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class WebhookDeliveryResponse(BaseModel):
    """Response schema for webhook delivery log."""
    id: int
    event_type: str
    status_code: Optional[int] = None
    response_time_ms: Optional[int] = None
    success: bool
    error_message: Optional[str] = None
    attempt_count: int
    created_at: datetime

    class Config:
        from_attributes = True


# Available webhook events
AVAILABLE_EVENTS = [
    "ticket.created",
    "ticket.updated",
    "ticket.resolved",
    "ticket.closed",
    "ticket.assigned",
    "equipment.created",
    "equipment.updated",
    "equipment.deleted",
    "contract.created",
    "contract.expiring",
    "user.created",
    "user.deleted",
    "sla.breached",
]


# ==================== WEBHOOK DELIVERY FUNCTION ====================

async def deliver_webhook(
    webhook: models.Webhook,
    event_type: str,
    payload: dict,
    db: Session
):
    """
    Deliver a webhook payload to the configured URL.
    Handles retries and logs delivery attempts.
    """
    import httpx

    headers = {
        "Content-Type": webhook.content_type,
        "X-Webhook-Event": event_type,
        "X-Webhook-Timestamp": str(int(time.time())),
    }

    # Add HMAC signature if secret is configured
    if webhook.secret:
        payload_bytes = json.dumps(payload).encode()
        signature = hmac.new(
            webhook.secret.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        headers["X-Webhook-Signature"] = f"sha256={signature}"

    delivery = models.WebhookDelivery(
        webhook_id=webhook.id,
        event_type=event_type,
        payload=payload
    )

    start_time = time.time()
    attempt = 0
    max_attempts = webhook.retry_count + 1

    async with httpx.AsyncClient() as client:
        while attempt < max_attempts:
            attempt += 1
            delivery.attempt_count = attempt

            try:
                response = await client.post(
                    webhook.url,
                    json=payload,
                    headers=headers,
                    timeout=webhook.timeout_seconds
                )

                delivery.status_code = response.status_code
                delivery.response_body = response.text[:1000] if response.text else None
                delivery.response_time_ms = int((time.time() - start_time) * 1000)

                if 200 <= response.status_code < 300:
                    delivery.success = True
                    webhook.success_count += 1
                    webhook.failure_count = 0  # Reset consecutive failures
                    break
                else:
                    delivery.success = False
                    delivery.error_message = f"HTTP {response.status_code}"

            except httpx.TimeoutException:
                delivery.success = False
                delivery.error_message = "Request timeout"
            except httpx.RequestError as e:
                delivery.success = False
                delivery.error_message = str(e)[:500]
            except Exception as e:
                delivery.success = False
                delivery.error_message = str(e)[:500]

            # Wait before retry (exponential backoff)
            if attempt < max_attempts:
                await asyncio.sleep(2 ** attempt)

    # Update webhook stats
    webhook.last_triggered = datetime.now(timezone.utc)
    webhook.last_status_code = delivery.status_code

    if not delivery.success:
        webhook.failure_count += 1

    # Save delivery log
    db.add(delivery)
    db.commit()

    logger.info(
        f"Webhook delivery to {webhook.url}: "
        f"event={event_type}, success={delivery.success}, "
        f"status={delivery.status_code}, attempts={attempt}"
    )


async def trigger_webhooks(
    event_type: str,
    payload: dict,
    db: Session,
    entity_id: Optional[int] = None
):
    """
    Trigger all active webhooks subscribed to an event.
    """
    import asyncio

    # Find active webhooks subscribed to this event
    query = db.query(models.Webhook).filter(
        models.Webhook.is_active == True
    )

    if entity_id:
        query = query.filter(
            (models.Webhook.entity_id == entity_id) |
            (models.Webhook.entity_id == None)
        )

    webhooks = query.all()

    # Filter webhooks that are subscribed to this event
    matching_webhooks = [
        w for w in webhooks
        if event_type in (w.events or [])
    ]

    if not matching_webhooks:
        return

    # Deliver to all matching webhooks concurrently
    tasks = [
        deliver_webhook(webhook, event_type, payload, db)
        for webhook in matching_webhooks
    ]

    await asyncio.gather(*tasks, return_exceptions=True)


# ==================== CRUD ENDPOINTS ====================

@router.get("/events", response_model=List[str])
def list_available_events(
    current_user: models.User = Depends(get_current_admin_user)
):
    """List all available webhook events."""
    return AVAILABLE_EVENTS


@router.get("/", response_model=List[WebhookResponse])
def list_webhooks(
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """List all webhooks."""
    query = db.query(models.Webhook)

    if current_user.entity_id:
        query = query.filter(models.Webhook.entity_id == current_user.entity_id)

    if is_active is not None:
        query = query.filter(models.Webhook.is_active == is_active)

    webhooks = query.order_by(models.Webhook.created_at.desc()).offset(skip).limit(limit).all()

    return webhooks


@router.get("/{webhook_id}", response_model=WebhookResponse)
def get_webhook(
    webhook_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Get a specific webhook."""
    webhook = db.query(models.Webhook).filter(models.Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    return webhook


@router.post("/", response_model=WebhookResponse)
def create_webhook(
    webhook_data: WebhookCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Create a new webhook."""
    # Validate events
    invalid_events = set(webhook_data.events) - set(AVAILABLE_EVENTS)
    if invalid_events:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid events: {', '.join(invalid_events)}. Available: {', '.join(AVAILABLE_EVENTS)}"
        )

    webhook = models.Webhook(
        name=webhook_data.name,
        url=webhook_data.url,
        secret=webhook_data.secret,
        events=webhook_data.events,
        is_active=webhook_data.is_active,
        retry_count=webhook_data.retry_count,
        timeout_seconds=webhook_data.timeout_seconds,
        entity_id=current_user.entity_id,
        created_by_id=current_user.id
    )

    db.add(webhook)
    db.commit()
    db.refresh(webhook)

    logger.info(f"Webhook '{webhook.name}' created by {current_user.username}")
    return webhook


@router.put("/{webhook_id}", response_model=WebhookResponse)
def update_webhook(
    webhook_id: int,
    webhook_data: WebhookUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Update a webhook."""
    webhook = db.query(models.Webhook).filter(models.Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    update_data = webhook_data.model_dump(exclude_unset=True)

    # Validate events if provided
    if "events" in update_data:
        invalid_events = set(update_data["events"]) - set(AVAILABLE_EVENTS)
        if invalid_events:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid events: {', '.join(invalid_events)}"
            )

    for field, value in update_data.items():
        setattr(webhook, field, value)

    db.commit()
    db.refresh(webhook)

    logger.info(f"Webhook '{webhook.name}' updated by {current_user.username}")
    return webhook


@router.delete("/{webhook_id}")
def delete_webhook(
    webhook_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Delete a webhook."""
    webhook = db.query(models.Webhook).filter(models.Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    webhook_name = webhook.name
    db.delete(webhook)
    db.commit()

    logger.info(f"Webhook '{webhook_name}' deleted by {current_user.username}")
    return {"message": f"Webhook '{webhook_name}' deleted"}


# ==================== DELIVERY LOG ENDPOINTS ====================

@router.get("/{webhook_id}/deliveries", response_model=List[WebhookDeliveryResponse])
def list_webhook_deliveries(
    webhook_id: int,
    success: Optional[bool] = None,
    skip: int = 0,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """List delivery attempts for a webhook."""
    webhook = db.query(models.Webhook).filter(models.Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    query = db.query(models.WebhookDelivery).filter(
        models.WebhookDelivery.webhook_id == webhook_id
    )

    if success is not None:
        query = query.filter(models.WebhookDelivery.success == success)

    deliveries = query.order_by(
        models.WebhookDelivery.created_at.desc()
    ).offset(skip).limit(limit).all()

    return deliveries


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Send a test payload to a webhook."""
    webhook = db.query(models.Webhook).filter(models.Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    test_payload = {
        "event": "webhook.test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "message": "This is a test webhook delivery",
            "webhook_id": webhook.id,
            "webhook_name": webhook.name,
            "triggered_by": current_user.username
        }
    }

    # Deliver in background
    import asyncio
    loop = asyncio.get_event_loop()
    loop.create_task(deliver_webhook(webhook, "webhook.test", test_payload, db))

    logger.info(f"Test webhook sent to '{webhook.name}' by {current_user.username}")
    return {"message": "Test webhook sent", "webhook_id": webhook.id}


@router.delete("/{webhook_id}/deliveries")
def clear_delivery_logs(
    webhook_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Clear delivery logs for a webhook."""
    webhook = db.query(models.Webhook).filter(models.Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    deleted = db.query(models.WebhookDelivery).filter(
        models.WebhookDelivery.webhook_id == webhook_id
    ).delete()

    db.commit()

    logger.info(f"Cleared {deleted} delivery logs for webhook '{webhook.name}'")
    return {"message": f"Cleared {deleted} delivery logs"}
