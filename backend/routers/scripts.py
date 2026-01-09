"""
Scripts Router - Script upload and execution with security enhancements.
Includes MIME type validation and Docker sandbox enforcement.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import shutil
import os
import re
from datetime import datetime, timezone
import logging

from backend.core.database import get_db
from backend.core.security import get_current_active_user, get_current_admin_user, verify_password
from backend.core.config import get_settings
from backend import models, schemas
from worker.tasks import execute_script_task

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/scripts", tags=["Scripts"])

# Constants
ALLOWED_SCRIPT_TYPES = {"python", "bash", "powershell"}
ALLOWED_SCRIPT_EXTENSIONS = {".py", ".sh", ".ps1"}

# MIME type mapping for script validation
ALLOWED_MIME_TYPES = {
    "text/plain": ["python", "bash", "powershell"],
    "text/x-python": ["python"],
    "text/x-script.python": ["python"],
    "application/x-python-code": ["python"],
    "text/x-sh": ["bash"],
    "text/x-shellscript": ["bash"],
    "application/x-sh": ["bash"],
    "application/x-powershell": ["powershell"],
    "text/x-powershell": ["powershell"],
    # Fallback for scripts that may be detected as generic text
    "application/octet-stream": ["python", "bash", "powershell"],
}


def validate_mime_type(content: bytes, script_type: str) -> bool:
    """
    Validate file content using MIME type detection.

    Args:
        content: File content bytes
        script_type: Expected script type (python, bash, powershell)

    Returns:
        True if MIME type is valid for the script type
    """
    try:
        import magic
        detected_mime = magic.from_buffer(content, mime=True)
        logger.debug(f"Detected MIME type: {detected_mime} for script type: {script_type}")

        # Check if detected MIME type is allowed for this script type
        if detected_mime in ALLOWED_MIME_TYPES:
            allowed_types = ALLOWED_MIME_TYPES[detected_mime]
            return script_type in allowed_types

        # Be lenient with text files - check if it looks like text
        if detected_mime.startswith("text/"):
            return True

        logger.warning(f"Unrecognized MIME type {detected_mime} for script upload")
        return False

    except ImportError:
        # python-magic not installed - fall back to basic validation
        logger.warning("python-magic not installed, skipping MIME validation")
        return True
    except Exception as e:
        logger.error(f"MIME type detection error: {e}")
        # On error, allow upload but log the issue
        return True


def check_scripts_permission(current_user: models.User):
    """Check if user has scripts permission (superadmin only)."""
    if current_user.role != "superadmin":
        raise HTTPException(
            status_code=403,
            detail="Permission denied: Only superadmin users can manage and execute scripts. "
                   "Contact your administrator if you need script access."
        )


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal."""
    filename = os.path.basename(filename)
    filename = re.sub(r'[^\w\-_\. ]', '', filename)
    filename = filename.replace(' ', '_')
    if len(filename) > settings.max_filename_length:
        name, ext = os.path.splitext(filename)
        filename = name[:settings.max_filename_length - len(ext)] + ext
    return filename


def validate_script_type(script_type: str) -> bool:
    """Validate that script type is allowed."""
    return script_type.lower() in ALLOWED_SCRIPT_TYPES


def validate_script_extension(filename: str) -> bool:
    """Validate that file extension is allowed."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_SCRIPT_EXTENSIONS


def sanitize_script_args(args: Optional[List[str]]) -> List[str]:
    """Sanitize script arguments to prevent injection."""
    if not args:
        return []

    sanitized = []
    dangerous_patterns = [';', '&&', '||', '|', '`', '$', '>', '<', '\n', '\r']

    for arg in args:
        if not isinstance(arg, str):
            continue
        for pattern in dangerous_patterns:
            if pattern in arg:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid character in argument: {pattern}"
                )
        if len(arg) > 1000:
            raise HTTPException(
                status_code=400,
                detail="Argument too long (max 1000 characters)"
            )
        sanitized.append(arg)

    return sanitized


class ScriptExecutionRequest(BaseModel):
    equipment_id: Optional[int] = None
    password: str
    script_args: Optional[List[str]] = None


@router.post("/", response_model=schemas.Script)
def upload_script(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    script_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Upload a new script."""
    check_scripts_permission(current_user)

    # Validate script name
    if not name or len(name) > settings.max_script_name_length:
        raise HTTPException(
            status_code=400,
            detail=f"Script name must be 1-{settings.max_script_name_length} characters"
        )
    if not re.match(r'^[\w\-\s]+$', name):
        raise HTTPException(
            status_code=400,
            detail="Script name can only contain letters, numbers, underscores, hyphens, and spaces"
        )

    # Validate script type
    if not validate_script_type(script_type):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid script type. Allowed: {', '.join(ALLOWED_SCRIPT_TYPES)}"
        )

    # Validate file extension
    if not validate_script_extension(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file extension. Allowed: {', '.join(ALLOWED_SCRIPT_EXTENSIONS)}"
        )

    # Read file content for MIME validation
    file_content = file.file.read()
    file.file.seek(0)  # Reset file pointer for later use

    # Validate MIME type
    if not validate_mime_type(file_content, script_type.lower()):
        raise HTTPException(
            status_code=400,
            detail="File content does not match expected script type. "
                   "Please ensure the file is a valid text/script file."
        )

    # Check for duplicate
    existing = db.query(models.Script).filter(models.Script.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Script name already exists")

    # Sanitize and save file
    safe_name = sanitize_filename(name)
    safe_file = sanitize_filename(file.filename)
    filename = f"{safe_name}_{safe_file}"

    os.makedirs(settings.scripts_dir, exist_ok=True)
    file_location = os.path.join(settings.scripts_dir, filename)

    # Security check
    if not os.path.abspath(file_location).startswith(os.path.abspath(settings.scripts_dir)):
        raise HTTPException(status_code=400, detail="Invalid file path")

    with open(file_location, "wb+") as buffer:
        buffer.write(file_content)

    db_script = models.Script(
        name=name,
        description=description,
        script_type=script_type.lower(),
        filename=filename
    )
    db.add(db_script)
    db.commit()
    db.refresh(db_script)

    logger.info(f"Script '{name}' uploaded by '{current_user.username}'")
    return db_script


@router.get("/", response_model=List[schemas.Script])
def list_scripts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """List all scripts."""
    check_scripts_permission(current_user)
    return db.query(models.Script).order_by(models.Script.name).offset(skip).limit(limit).all()


@router.post("/{script_id}/run", response_model=schemas.ScriptExecution)
def run_script(
    script_id: int,
    exec_req: ScriptExecutionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Execute a script."""
    check_scripts_permission(current_user)

    # Verify password
    if not verify_password(exec_req.password, current_user.hashed_password):
        logger.warning(f"Failed password confirmation for script execution by '{current_user.username}'")
        raise HTTPException(status_code=403, detail="Invalid password confirmation")

    script = db.query(models.Script).filter(models.Script.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    # Validate equipment if specified
    if exec_req.equipment_id:
        equipment = db.query(models.Equipment).filter(
            models.Equipment.id == exec_req.equipment_id
        ).first()
        if not equipment:
            raise HTTPException(status_code=404, detail="Target equipment not found")
        if not equipment.remote_ip or not equipment.remote_username:
            raise HTTPException(
                status_code=400,
                detail="Equipment is not configured for remote execution"
            )

    # Sanitize arguments
    safe_args = sanitize_script_args(exec_req.script_args)

    execution = models.ScriptExecution(
        script_id=script_id,
        equipment_id=exec_req.equipment_id,
        status="pending",
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    task = execute_script_task.delay(
        execution.id,
        script.filename,
        script.script_type,
        exec_req.equipment_id,
        safe_args
    )

    execution.task_id = task.id
    db.commit()

    logger.info(f"Script '{script.name}' execution started by '{current_user.username}'")
    return execution


@router.delete("/{script_id}")
def delete_script(
    script_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Delete a script."""
    check_scripts_permission(current_user)

    script = db.query(models.Script).filter(models.Script.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    # Delete file
    file_path = os.path.join(settings.scripts_dir, script.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    db.delete(script)
    db.commit()

    logger.info(f"Script '{script.name}' deleted by '{current_user.username}'")
    return {"ok": True}


# Execution endpoints
executions_router = APIRouter(prefix="/executions", tags=["Executions"])


@executions_router.get("/", response_model=List[schemas.ScriptExecution])
def list_executions(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """List script executions."""
    return db.query(models.ScriptExecution).order_by(
        models.ScriptExecution.started_at.desc()
    ).offset(skip).limit(limit).all()


@executions_router.post("/{execution_id}/stop")
def stop_execution(
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Stop a running execution."""
    check_scripts_permission(current_user)

    execution = db.query(models.ScriptExecution).filter(
        models.ScriptExecution.id == execution_id
    ).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    if execution.status in ["running", "pending"] and execution.task_id:
        execute_script_task.app.control.revoke(execution.task_id, terminate=True)
        execution.status = "cancelled"
        execution.stderr = (execution.stderr or "") + "\n[Stopped by user]"
        execution.completed_at = datetime.now(timezone.utc)
        db.commit()

    return {"message": "Execution stopped"}


@executions_router.delete("/")
def clear_executions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Clear all executions (admin only)."""
    db.query(models.ScriptExecution).delete()
    db.commit()
    logger.info(f"Execution history cleared by '{current_user.username}'")
    return {"message": "History cleared"}
