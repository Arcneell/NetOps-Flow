"""
Attachments Router - File storage for equipment documents.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import logging
from pathlib import Path

from backend.core.database import get_db
from backend.core.security import get_current_active_user, get_current_admin_user
from backend import models, schemas

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/attachments", tags=["Attachments"])

# Configuration
ATTACHMENTS_DIR = os.environ.get("ATTACHMENTS_DIR", "/attachments_storage")
MAX_FILE_SIZE = int(os.environ.get("MAX_ATTACHMENT_SIZE", str(10 * 1024 * 1024)))  # 10MB
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "gif", "doc", "docx", "xls", "xlsx", "txt"}


def check_attachment_permission(current_user: models.User):
    """Check if user has attachment/inventory permission (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")


def get_file_extension(filename: str) -> str:
    """Extract file extension."""
    if "." in filename:
        return filename.rsplit(".", 1)[1].lower()
    return ""


def validate_file(file: UploadFile):
    """Validate uploaded file."""
    ext = get_file_extension(file.filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )


def ensure_storage_dir():
    """Ensure attachment storage directory exists."""
    Path(ATTACHMENTS_DIR).mkdir(parents=True, exist_ok=True)


# ==================== ATTACHMENTS ====================

@router.get("/equipment/{equipment_id}", response_model=List[schemas.Attachment])
def list_equipment_attachments(
    equipment_id: int,
    category: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """List all attachments for an equipment."""
    check_attachment_permission(current_user)

    equipment = db.query(models.Equipment).filter(
        models.Equipment.id == equipment_id
    ).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    query = db.query(models.Attachment).filter(
        models.Attachment.equipment_id == equipment_id
    )

    if category:
        query = query.filter(models.Attachment.category == category)

    return query.order_by(models.Attachment.uploaded_at.desc()).all()


@router.get("/{attachment_id}", response_model=schemas.Attachment)
def get_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get attachment metadata."""
    check_attachment_permission(current_user)

    attachment = db.query(models.Attachment).filter(
        models.Attachment.id == attachment_id
    ).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    return attachment


@router.get("/{attachment_id}/download")
def download_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Download an attachment file."""
    check_attachment_permission(current_user)

    attachment = db.query(models.Attachment).filter(
        models.Attachment.id == attachment_id
    ).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    file_path = os.path.join(ATTACHMENTS_DIR, attachment.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=file_path,
        filename=attachment.original_filename,
        media_type="application/octet-stream"
    )


@router.post("/equipment/{equipment_id}", response_model=schemas.Attachment)
async def upload_attachment(
    equipment_id: int,
    file: UploadFile = File(...),
    category: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Upload an attachment for equipment."""
    check_attachment_permission(current_user)

    # Verify equipment exists
    equipment = db.query(models.Equipment).filter(
        models.Equipment.id == equipment_id
    ).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    # Validate file
    validate_file(file)

    # Read and check file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )

    # Ensure storage directory exists
    ensure_storage_dir()

    # Generate unique filename
    ext = get_file_extension(file.filename)
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(ATTACHMENTS_DIR, unique_filename)

    # Save file
    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        logger.error(f"Failed to save attachment: {e}")
        raise HTTPException(status_code=500, detail="Failed to save file")

    # Create database record
    attachment = models.Attachment(
        equipment_id=equipment_id,
        filename=unique_filename,
        original_filename=file.filename,
        file_type=ext,
        file_size=len(content),
        category=category,
        description=description,
        uploaded_by=current_user.username
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    logger.info(
        f"Attachment '{file.filename}' uploaded for '{equipment.name}' "
        f"by '{current_user.username}'"
    )

    return attachment


@router.put("/{attachment_id}", response_model=schemas.Attachment)
def update_attachment(
    attachment_id: int,
    category: Optional[str] = None,
    description: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Update attachment metadata."""
    check_attachment_permission(current_user)

    attachment = db.query(models.Attachment).filter(
        models.Attachment.id == attachment_id
    ).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    if category is not None:
        attachment.category = category
    if description is not None:
        attachment.description = description

    db.commit()
    db.refresh(attachment)

    return attachment


@router.delete("/{attachment_id}")
def delete_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Delete an attachment."""
    check_attachment_permission(current_user)

    attachment = db.query(models.Attachment).filter(
        models.Attachment.id == attachment_id
    ).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    # Delete file from disk
    file_path = os.path.join(ATTACHMENTS_DIR, attachment.filename)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        logger.warning(f"Failed to delete file {file_path}: {e}")

    db.delete(attachment)
    db.commit()

    logger.info(
        f"Attachment '{attachment.original_filename}' deleted "
        f"by '{current_user.username}'"
    )

    return {"ok": True}
