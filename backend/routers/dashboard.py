"""
Dashboard Router - Statistics and overview.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.security import get_current_active_user
from backend import models

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get dashboard statistics."""
    return {
        "subnets": db.query(models.Subnet).count(),
        "ips": db.query(models.IPAddress).count(),
        "scripts": db.query(models.Script).count(),
        "executions": db.query(models.ScriptExecution).count(),
        "equipment": db.query(models.Equipment).count()
    }
