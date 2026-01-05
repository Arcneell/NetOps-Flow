"""
System Settings Router - Administration system configuration.
Superadmin only access for sensitive system settings.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
import json
import logging

from backend.core.database import get_db
from backend.core.security import get_current_superadmin_user, encrypt_value, decrypt_value
from backend.core.rate_limiter import get_rate_limiter
from backend import models

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])


# ==================== PYDANTIC MODELS ====================

class SettingCreate(BaseModel):
    """Schema for creating a setting."""
    key: str
    value: Optional[str] = None
    category: str
    description: Optional[str] = None
    value_type: str = "string"  # string, integer, boolean, json, password
    is_sensitive: bool = False


class SettingUpdate(BaseModel):
    """Schema for updating a setting."""
    value: Optional[str] = None
    description: Optional[str] = None


class SettingResponse(BaseModel):
    """Response schema for a setting."""
    id: int
    key: str
    value: Optional[str] = None
    category: str
    description: Optional[str] = None
    value_type: str
    is_sensitive: bool
    updated_at: Optional[datetime] = None
    updated_by_id: Optional[int] = None

    class Config:
        from_attributes = True


class SettingCategoryResponse(BaseModel):
    """Response schema for a category of settings."""
    category: str
    settings: List[SettingResponse]


# ==================== DEFAULT SETTINGS ====================

DEFAULT_SETTINGS = [
    # SMTP Settings
    {
        "key": "smtp_host",
        "value": "",
        "category": "smtp",
        "description": "SMTP server hostname",
        "value_type": "string",
        "is_sensitive": False
    },
    {
        "key": "smtp_port",
        "value": "587",
        "category": "smtp",
        "description": "SMTP server port",
        "value_type": "integer",
        "is_sensitive": False
    },
    {
        "key": "smtp_username",
        "value": "",
        "category": "smtp",
        "description": "SMTP authentication username",
        "value_type": "string",
        "is_sensitive": False
    },
    {
        "key": "smtp_password",
        "value": "",
        "category": "smtp",
        "description": "SMTP authentication password",
        "value_type": "password",
        "is_sensitive": True
    },
    {
        "key": "smtp_use_tls",
        "value": "true",
        "category": "smtp",
        "description": "Use TLS encryption for SMTP",
        "value_type": "boolean",
        "is_sensitive": False
    },
    {
        "key": "smtp_from_email",
        "value": "",
        "category": "smtp",
        "description": "Default sender email address",
        "value_type": "string",
        "is_sensitive": False
    },
    {
        "key": "smtp_from_name",
        "value": "Inframate",
        "category": "smtp",
        "description": "Default sender name",
        "value_type": "string",
        "is_sensitive": False
    },
    # General Settings
    {
        "key": "site_name",
        "value": "Inframate",
        "category": "general",
        "description": "Site name displayed in the application",
        "value_type": "string",
        "is_sensitive": False
    },
    {
        "key": "site_url",
        "value": "http://localhost:3000",
        "category": "general",
        "description": "Base URL of the application",
        "value_type": "string",
        "is_sensitive": False
    },
    {
        "key": "default_language",
        "value": "en",
        "category": "general",
        "description": "Default application language (en, fr)",
        "value_type": "string",
        "is_sensitive": False
    },
    {
        "key": "session_timeout_minutes",
        "value": "30",
        "category": "general",
        "description": "Session timeout in minutes",
        "value_type": "integer",
        "is_sensitive": False
    },
    {
        "key": "items_per_page",
        "value": "25",
        "category": "general",
        "description": "Default number of items per page in lists",
        "value_type": "integer",
        "is_sensitive": False
    },
    # Security Settings
    {
        "key": "min_password_length",
        "value": "8",
        "category": "security",
        "description": "Minimum password length",
        "value_type": "integer",
        "is_sensitive": False
    },
    {
        "key": "require_mfa_for_admins",
        "value": "false",
        "category": "security",
        "description": "Require MFA for admin and superadmin users",
        "value_type": "boolean",
        "is_sensitive": False
    },
    {
        "key": "login_rate_limit",
        "value": "5",
        "category": "security",
        "description": "Maximum login attempts per minute",
        "value_type": "integer",
        "is_sensitive": False
    },
    {
        "key": "session_concurrent_limit",
        "value": "5",
        "category": "security",
        "description": "Maximum concurrent sessions per user",
        "value_type": "integer",
        "is_sensitive": False
    },
    # Notification Settings
    {
        "key": "email_notifications_enabled",
        "value": "false",
        "category": "notifications",
        "description": "Enable email notifications",
        "value_type": "boolean",
        "is_sensitive": False
    },
    {
        "key": "ticket_notification_email",
        "value": "true",
        "category": "notifications",
        "description": "Send email on ticket creation",
        "value_type": "boolean",
        "is_sensitive": False
    },
    {
        "key": "contract_expiry_notification_days",
        "value": "30",
        "category": "notifications",
        "description": "Days before contract expiry to send notification",
        "value_type": "integer",
        "is_sensitive": False
    },
    {
        "key": "license_expiry_notification_days",
        "value": "30",
        "category": "notifications",
        "description": "Days before license expiry to send notification",
        "value_type": "integer",
        "is_sensitive": False
    },
    # Maintenance Settings
    {
        "key": "maintenance_mode",
        "value": "false",
        "category": "maintenance",
        "description": "Enable maintenance mode (only superadmins can access)",
        "value_type": "boolean",
        "is_sensitive": False
    },
    {
        "key": "maintenance_message",
        "value": "The system is currently under maintenance. Please try again later.",
        "category": "maintenance",
        "description": "Message displayed during maintenance",
        "value_type": "string",
        "is_sensitive": False
    },
    {
        "key": "audit_log_retention_days",
        "value": "90",
        "category": "maintenance",
        "description": "Days to retain audit logs",
        "value_type": "integer",
        "is_sensitive": False
    },
    {
        "key": "backup_enabled",
        "value": "false",
        "category": "maintenance",
        "description": "Enable automatic database backups",
        "value_type": "boolean",
        "is_sensitive": False
    },
]


# ==================== HELPER FUNCTIONS ====================

def init_default_settings(db: Session) -> int:
    """Initialize default settings if they don't exist."""
    created = 0
    for setting_data in DEFAULT_SETTINGS:
        existing = db.query(models.SystemSettings).filter(
            models.SystemSettings.key == setting_data["key"]
        ).first()

        if not existing:
            setting = models.SystemSettings(**setting_data)
            db.add(setting)
            created += 1

    if created > 0:
        db.commit()
        logger.info(f"Initialized {created} default system settings")

    return created


def get_setting_value(db: Session, key: str, default: str = None) -> Optional[str]:
    """Get a setting value by key."""
    setting = db.query(models.SystemSettings).filter(
        models.SystemSettings.key == key
    ).first()

    if not setting:
        return default

    # Decrypt sensitive values
    if setting.is_sensitive and setting.value:
        try:
            return decrypt_value(setting.value)
        except Exception:
            return default

    return setting.value


def mask_sensitive_value(value: str) -> str:
    """Mask a sensitive value for display."""
    if not value:
        return ""
    if len(value) <= 4:
        return "****"
    return value[:2] + "****" + value[-2:]


# ==================== ENDPOINTS ====================

@router.get("/", response_model=List[SettingResponse])
def list_settings(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_superadmin_user)
):
    """List all system settings."""
    # Initialize default settings if needed
    init_default_settings(db)

    query = db.query(models.SystemSettings)

    if category:
        query = query.filter(models.SystemSettings.category == category)

    settings = query.order_by(
        models.SystemSettings.category,
        models.SystemSettings.key
    ).all()

    # Mask sensitive values
    result = []
    for setting in settings:
        setting_dict = {
            "id": setting.id,
            "key": setting.key,
            "value": mask_sensitive_value(setting.value) if setting.is_sensitive else setting.value,
            "category": setting.category,
            "description": setting.description,
            "value_type": setting.value_type,
            "is_sensitive": setting.is_sensitive,
            "updated_at": setting.updated_at,
            "updated_by_id": setting.updated_by_id
        }
        result.append(SettingResponse(**setting_dict))

    return result


@router.get("/categories", response_model=List[str])
def list_categories(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_superadmin_user)
):
    """List all setting categories."""
    categories = db.query(models.SystemSettings.category).distinct().all()
    return [c[0] for c in categories]


@router.get("/by-category", response_model=List[SettingCategoryResponse])
def list_settings_by_category(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_superadmin_user)
):
    """List all settings grouped by category."""
    # Initialize default settings if needed
    init_default_settings(db)

    settings = db.query(models.SystemSettings).order_by(
        models.SystemSettings.category,
        models.SystemSettings.key
    ).all()

    # Group by category
    categories = {}
    for setting in settings:
        if setting.category not in categories:
            categories[setting.category] = []

        setting_dict = {
            "id": setting.id,
            "key": setting.key,
            "value": mask_sensitive_value(setting.value) if setting.is_sensitive else setting.value,
            "category": setting.category,
            "description": setting.description,
            "value_type": setting.value_type,
            "is_sensitive": setting.is_sensitive,
            "updated_at": setting.updated_at,
            "updated_by_id": setting.updated_by_id
        }
        categories[setting.category].append(SettingResponse(**setting_dict))

    return [
        SettingCategoryResponse(category=cat, settings=settings_list)
        for cat, settings_list in categories.items()
    ]


@router.get("/{key}", response_model=SettingResponse)
def get_setting(
    key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_superadmin_user)
):
    """Get a specific setting by key."""
    setting = db.query(models.SystemSettings).filter(
        models.SystemSettings.key == key
    ).first()

    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")

    # Mask sensitive values
    value = mask_sensitive_value(setting.value) if setting.is_sensitive else setting.value

    return SettingResponse(
        id=setting.id,
        key=setting.key,
        value=value,
        category=setting.category,
        description=setting.description,
        value_type=setting.value_type,
        is_sensitive=setting.is_sensitive,
        updated_at=setting.updated_at,
        updated_by_id=setting.updated_by_id
    )


@router.put("/{key}", response_model=SettingResponse)
async def update_setting(
    key: str,
    setting_data: SettingUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_superadmin_user)
):
    """Update a system setting."""
    # Rate limiting using action-based identifier
    rate_limiter = get_rate_limiter()

    if not rate_limiter.is_allowed(str(current_user.id), action="settings_update"):
        logger.warning(f"Rate limit exceeded for settings update by user {current_user.username}")
        raise HTTPException(
            status_code=429,
            detail="Too many settings modifications. Please try again later."
        )

    setting = db.query(models.SystemSettings).filter(
        models.SystemSettings.key == key
    ).first()

    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")

    # Update value
    if setting_data.value is not None:
        # Encrypt sensitive values
        if setting.is_sensitive and setting_data.value:
            setting.value = encrypt_value(setting_data.value)
        else:
            setting.value = setting_data.value

    # Update description if provided
    if setting_data.description is not None:
        setting.description = setting_data.description

    setting.updated_at = datetime.now(timezone.utc)
    setting.updated_by_id = current_user.id

    db.commit()
    db.refresh(setting)

    logger.info(f"Setting '{key}' updated by {current_user.username}")

    # Return with masked value if sensitive
    value = mask_sensitive_value(setting.value) if setting.is_sensitive else setting.value

    return SettingResponse(
        id=setting.id,
        key=setting.key,
        value=value,
        category=setting.category,
        description=setting.description,
        value_type=setting.value_type,
        is_sensitive=setting.is_sensitive,
        updated_at=setting.updated_at,
        updated_by_id=setting.updated_by_id
    )


@router.post("/", response_model=SettingResponse)
async def create_setting(
    setting_data: SettingCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_superadmin_user)
):
    """Create a new system setting."""
    # Rate limiting using action-based identifier
    rate_limiter = get_rate_limiter()

    if not rate_limiter.is_allowed(str(current_user.id), action="settings_update"):
        logger.warning(f"Rate limit exceeded for settings creation by user {current_user.username}")
        raise HTTPException(
            status_code=429,
            detail="Too many settings modifications. Please try again later."
        )

    # Check if key already exists
    existing = db.query(models.SystemSettings).filter(
        models.SystemSettings.key == setting_data.key
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Setting with this key already exists")

    # Encrypt sensitive values
    value = setting_data.value
    if setting_data.is_sensitive and value:
        value = encrypt_value(value)

    setting = models.SystemSettings(
        key=setting_data.key,
        value=value,
        category=setting_data.category,
        description=setting_data.description,
        value_type=setting_data.value_type,
        is_sensitive=setting_data.is_sensitive,
        updated_by_id=current_user.id
    )

    db.add(setting)
    db.commit()
    db.refresh(setting)

    logger.info(f"Setting '{setting_data.key}' created by {current_user.username}")

    return setting


@router.delete("/{key}")
def delete_setting(
    key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_superadmin_user)
):
    """Delete a system setting (custom settings only, not defaults)."""
    setting = db.query(models.SystemSettings).filter(
        models.SystemSettings.key == key
    ).first()

    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")

    # Check if it's a default setting
    default_keys = [s["key"] for s in DEFAULT_SETTINGS]
    if key in default_keys:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete default system settings. You can only update their values."
        )

    db.delete(setting)
    db.commit()

    logger.info(f"Setting '{key}' deleted by {current_user.username}")
    return {"message": f"Setting '{key}' deleted"}


@router.post("/init")
def initialize_settings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_superadmin_user)
):
    """Initialize all default settings."""
    created = init_default_settings(db)
    return {"message": f"Initialized {created} new settings"}


@router.post("/test-smtp")
async def test_smtp_connection(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_superadmin_user)
):
    """Test SMTP connection with current settings."""
    import smtplib
    from email.mime.text import MIMEText

    # Get SMTP settings
    host = get_setting_value(db, "smtp_host")
    port = int(get_setting_value(db, "smtp_port", "587"))
    username = get_setting_value(db, "smtp_username")
    password = get_setting_value(db, "smtp_password")
    use_tls = get_setting_value(db, "smtp_use_tls", "true").lower() == "true"
    from_email = get_setting_value(db, "smtp_from_email")

    if not host:
        raise HTTPException(status_code=400, detail="SMTP host not configured")

    if not from_email:
        raise HTTPException(status_code=400, detail="SMTP from email not configured")

    try:
        # Create test message
        msg = MIMEText("This is a test email from Inframate.")
        msg["Subject"] = "Inframate SMTP Test"
        msg["From"] = from_email
        msg["To"] = from_email

        # Connect and send
        if use_tls:
            server = smtplib.SMTP(host, port)
            server.starttls()
        else:
            server = smtplib.SMTP(host, port)

        if username and password:
            server.login(username, password)

        server.sendmail(from_email, [from_email], msg.as_string())
        server.quit()

        logger.info(f"SMTP test successful by {current_user.username}")
        return {"message": "SMTP test successful. Check your inbox."}

    except smtplib.SMTPAuthenticationError:
        raise HTTPException(status_code=400, detail="SMTP authentication failed. Check username and password.")
    except smtplib.SMTPConnectError:
        raise HTTPException(status_code=400, detail="Failed to connect to SMTP server. Check host and port.")
    except Exception as e:
        logger.error(f"SMTP test failed: {e}")
        raise HTTPException(status_code=400, detail=f"SMTP test failed: {str(e)}")
