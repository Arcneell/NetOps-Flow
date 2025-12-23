from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from pydantic import BaseModel, field_validator
import shutil
import os
import re
import ipaddress
import logging
import datetime
import secrets

from backend import models, schemas, database, auth
from worker.tasks import execute_script_task, scan_subnet_task

# Security constants
ALLOWED_SCRIPT_TYPES = {"python", "bash", "powershell"}
ALLOWED_SCRIPT_EXTENSIONS = {".py", ".sh", ".ps1"}
MAX_SCRIPT_NAME_LENGTH = 100
MAX_FILENAME_LENGTH = 255

# Rate limiting configuration
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 5  # max login attempts per window
login_attempts: dict = {}  # In-memory rate limiting (use Redis in production for distributed)


def check_rate_limit(client_ip: str) -> bool:
    """Check if client has exceeded rate limit. Returns True if allowed, False if blocked."""
    current_time = datetime.datetime.utcnow().timestamp()

    # Clean old entries
    expired_keys = [ip for ip, data in login_attempts.items()
                    if current_time - data["window_start"] > RATE_LIMIT_WINDOW]
    for key in expired_keys:
        del login_attempts[key]

    if client_ip not in login_attempts:
        login_attempts[client_ip] = {"count": 1, "window_start": current_time}
        return True

    data = login_attempts[client_ip]
    if current_time - data["window_start"] > RATE_LIMIT_WINDOW:
        # Window expired, reset
        login_attempts[client_ip] = {"count": 1, "window_start": current_time}
        return True

    if data["count"] >= RATE_LIMIT_MAX_REQUESTS:
        return False

    data["count"] += 1
    return True


# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Tables
models.Base.metadata.create_all(bind=database.engine)

# Create Default Admin User
def create_default_admin():
    db = database.SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.username == "admin").first()
        if not user:
            logger.info("Creating default admin user...")
            hashed_pwd = auth.get_password_hash("admin")
            # Admin has all permissions
            perms = {"ipam": True, "topology": True, "scripts": True, "settings": True, "inventory": True}
            admin = models.User(username="admin", hashed_password=hashed_pwd, role="admin", permissions=perms)
            db.add(admin)
            db.commit()
            logger.info("Default user 'admin' created successfully.")
    except Exception as e:
        logger.error(f"Error creating default admin: {e}")
    finally:
        db.close()

create_default_admin()

app = FastAPI(title="NetOps-Flow API")

# CORS Configuration - Restrict origins in production
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and invalid characters."""
    # Remove path components
    filename = os.path.basename(filename)
    # Remove or replace dangerous characters
    filename = re.sub(r'[^\w\-_\. ]', '', filename)
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    # Limit length
    if len(filename) > MAX_FILENAME_LENGTH:
        name, ext = os.path.splitext(filename)
        filename = name[:MAX_FILENAME_LENGTH - len(ext)] + ext
    return filename


def validate_script_type(script_type: str) -> bool:
    """Validate that script type is allowed."""
    return script_type.lower() in ALLOWED_SCRIPT_TYPES


def validate_script_extension(filename: str) -> bool:
    """Validate that file extension is allowed."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_SCRIPT_EXTENSIONS

# --- Auth Endpoints ---

@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db)
):
    # Get client IP for rate limiting
    client_ip = request.client.host if request.client else "unknown"

    # Check rate limit before processing login
    if not check_rate_limit(client_ip):
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    user = db.query(models.User).filter(models.User.username == form_data.username.lower()).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Failed login attempt for username: {form_data.username} from IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    access_token = auth.create_access_token(data={"sub": user.username})
    logger.info(f"Successful login for user: {user.username} from IP: {client_ip}")
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(auth.get_current_active_user)):
    return current_user

class PasswordChange(BaseModel):
    password: str


@app.put("/users/me/password")
async def update_password(
    password_data: PasswordChange,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    # Validate password strength
    if not auth.validate_password_strength(password_data.password):
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {auth.MIN_PASSWORD_LENGTH} characters"
        )
    hashed_password = auth.get_password_hash(password_data.password)
    current_user.hashed_password = hashed_password
    db.commit()
    logger.info(f"Password updated for user: {current_user.username}")
    return {"message": "Password updated successfully"}

# --- User Management (Admin Only) ---

@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_admin_user)):
    # Validate username
    if not user.username or len(user.username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if not re.match(r'^[a-zA-Z0-9_]+$', user.username):
        raise HTTPException(status_code=400, detail="Username can only contain letters, numbers, and underscores")

    # Validate password strength
    if not auth.validate_password_strength(user.password):
        raise HTTPException(status_code=400, detail=f"Password must be at least {auth.MIN_PASSWORD_LENGTH} characters")

    db_user = db.query(models.User).filter(models.User.username == user.username.lower()).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Validate role
    if user.role not in ["admin", "user"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'admin' or 'user'")

    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        username=user.username.lower(),
        hashed_password=hashed_password,
        role=user.role,
        is_active=user.is_active,
        permissions=user.permissions
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    logger.info(f"User '{user.username}' created by admin '{current_user.username}'")
    return db_user

@app.get("/users/", response_model=List[schemas.User])
def read_users(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_admin_user)):
    return db.query(models.User).all()


@app.put("/users/{user_id}", response_model=schemas.User)
def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    """Update a user (admin only). Cannot change username."""
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent deactivating the last admin
    if user_update.is_active is False and db_user.role == "admin":
        active_admins = db.query(models.User).filter(
            models.User.role == "admin",
            models.User.is_active == True,
            models.User.id != user_id
        ).count()
        if active_admins == 0:
            raise HTTPException(status_code=400, detail="Cannot deactivate the last active admin")

    # Update fields
    if user_update.role is not None:
        if user_update.role not in ["admin", "user"]:
            raise HTTPException(status_code=400, detail="Invalid role")
        db_user.role = user_update.role
    if user_update.is_active is not None:
        db_user.is_active = user_update.is_active
    if user_update.permissions is not None:
        db_user.permissions = user_update.permissions
    if user_update.password:
        if not auth.validate_password_strength(user_update.password):
            raise HTTPException(status_code=400, detail=f"Password must be at least {auth.MIN_PASSWORD_LENGTH} characters")
        db_user.hashed_password = auth.get_password_hash(user_update.password)

    db.commit()
    db.refresh(db_user)
    logger.info(f"User '{db_user.username}' updated by admin '{current_user.username}'")
    return db_user


@app.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    """Delete a user (admin only). Cannot delete yourself."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent deleting the last admin
    if db_user.role == "admin":
        admin_count = db.query(models.User).filter(models.User.role == "admin").count()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete the last admin")

    db.delete(db_user)
    db.commit()
    logger.info(f"User '{db_user.username}' deleted by admin '{current_user.username}'")
    return {"ok": True}



# --- IPAM Endpoints ---

@app.post("/subnets/", response_model=schemas.Subnet)
def create_subnet(subnet: schemas.SubnetCreate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    if current_user.role != "admin" and not current_user.permissions.get("ipam"):
        raise HTTPException(status_code=403, detail="Permission denied")
    try:
        ipaddress.ip_network(subnet.cidr)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid CIDR format")
    db_subnet = models.Subnet(cidr=subnet.cidr, name=subnet.name, description=subnet.description)
    db.add(db_subnet)
    db.commit()
    db.refresh(db_subnet)
    return db_subnet

@app.get("/subnets/", response_model=List[schemas.SubnetWithEquipment])
def read_subnets(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    # Read access might be open or restricted. For now, let's keep it open to active users or check IPAM?
    # User asked to check rights. Let's enforce IPAM or Topology for reading subnets as they are basic network data?
    # Let's be safe: if you can't see IPAM or Topology, you probably shouldn't list subnets detailedly.
    # But for now, let's stick to modifying the write operations as critical path, and specific feature pages.
    if current_user.role != "admin" and not current_user.permissions.get("ipam") and not current_user.permissions.get("topology"):
         raise HTTPException(status_code=403, detail="Permission denied")
    # Load IPs with their equipment relationship
    subnets = db.query(models.Subnet).options(
        joinedload(models.Subnet.ips).joinedload(models.IPAddress.equipment)
    ).offset(skip).limit(limit).all()
    return subnets

@app.post("/subnets/{subnet_id}/ips/", response_model=schemas.IPAddress)
def create_ip_for_subnet(subnet_id: int, ip: schemas.IPAddressCreate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    if current_user.role != "admin" and not current_user.permissions.get("ipam"):
        raise HTTPException(status_code=403, detail="Permission denied")
    subnet = db.query(models.Subnet).filter(models.Subnet.id == subnet_id).first()
    if not subnet:
        raise HTTPException(status_code=404, detail="Subnet not found")
    net = ipaddress.ip_network(subnet.cidr)
    try:
        addr = ipaddress.ip_address(ip.address)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid IP address format")
    if addr not in net:
        raise HTTPException(status_code=400, detail=f"IP {ip.address} does not belong to subnet {subnet.cidr}")
    db_ip = models.IPAddress(**ip.model_dump(), subnet_id=subnet_id)
    db.add(db_ip)
    db.commit()
    db.refresh(db_ip)
    return db_ip

@app.post("/subnets/{subnet_id}/scan")
def scan_subnet(subnet_id: int, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    if current_user.role != "admin" and not current_user.permissions.get("ipam"):
        raise HTTPException(status_code=403, detail="Permission denied")
    subnet = db.query(models.Subnet).filter(models.Subnet.id == subnet_id).first()
    if not subnet:
        raise HTTPException(status_code=404, detail="Subnet not found")
    task = scan_subnet_task.delay(subnet_id)
    logger.info(f"Subnet scan started for '{subnet.cidr}' by '{current_user.username}'")
    return {"message": "Scan started", "task_id": task.id}


@app.delete("/subnets/{subnet_id}")
def delete_subnet(subnet_id: int, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_admin_user)):
    """Delete a subnet and all its IP addresses (admin only)."""
    subnet = db.query(models.Subnet).filter(models.Subnet.id == subnet_id).first()
    if not subnet:
        raise HTTPException(status_code=404, detail="Subnet not found")
    db.delete(subnet)  # Cascade will delete associated IPs
    db.commit()
    logger.info(f"Subnet '{subnet.cidr}' deleted by '{current_user.username}'")
    return {"ok": True, "message": f"Subnet {subnet.cidr} deleted"}


@app.delete("/subnets/{subnet_id}/ips/{ip_id}")
def delete_ip(subnet_id: int, ip_id: int, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    """Delete an IP address from a subnet."""
    if current_user.role != "admin" and not current_user.permissions.get("ipam"):
        raise HTTPException(status_code=403, detail="Permission denied")
    ip = db.query(models.IPAddress).filter(
        models.IPAddress.id == ip_id,
        models.IPAddress.subnet_id == subnet_id
    ).first()
    if not ip:
        raise HTTPException(status_code=404, detail="IP address not found")
    db.delete(ip)
    db.commit()
    return {"ok": True}


@app.get("/topology")
def get_topology(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    if current_user.role != "admin" and not current_user.permissions.get("topology"):
        raise HTTPException(status_code=403, detail="Permission denied")
    subnets = db.query(models.Subnet).all()
    nodes = []
    edges = []
    nodes.append({"id": "internet", "label": "Internet", "group": "internet", "shape": "cloud"})
    for subnet in subnets:
        subnet_node_id = f"subnet_{subnet.id}"
        nodes.append({
            "id": subnet_node_id,
            "label": f"{subnet.name}\n{subnet.cidr}",
            "group": "subnet",
            "shape": "box"
        })
        edges.append({"from": "internet", "to": subnet_node_id})
        for ip in subnet.ips:
            ip_node_id = f"ip_{ip.id}"
            label = ip.address
            if ip.hostname:
                label += f"\n({ip.hostname})"
            color = "#10b981" if ip.status == "active" else "#64748b"
            nodes.append({
                "id": ip_node_id,
                "label": label,
                "group": "ip",
                "shape": "dot",
                "color": color
            })
            edges.append({"from": subnet_node_id, "to": ip_node_id})
    return {"nodes": nodes, "edges": edges}

# --- Script Runner Endpoints ---

SCRIPTS_DIR = "/scripts_storage"

@app.post("/scripts/", response_model=schemas.Script)
def upload_script(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    script_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if current_user.role != "admin" and not current_user.permissions.get("scripts"):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Validate script name
    if not name or len(name) > MAX_SCRIPT_NAME_LENGTH:
        raise HTTPException(status_code=400, detail=f"Script name must be 1-{MAX_SCRIPT_NAME_LENGTH} characters")
    if not re.match(r'^[\w\-\s]+$', name):
        raise HTTPException(status_code=400, detail="Script name can only contain letters, numbers, underscores, hyphens, and spaces")

    # Validate script type
    if not validate_script_type(script_type):
        raise HTTPException(status_code=400, detail=f"Invalid script type. Allowed: {', '.join(ALLOWED_SCRIPT_TYPES)}")

    # Validate file extension
    if not validate_script_extension(file.filename):
        raise HTTPException(status_code=400, detail=f"Invalid file extension. Allowed: {', '.join(ALLOWED_SCRIPT_EXTENSIONS)}")

    # Check for duplicate script name
    existing = db.query(models.Script).filter(models.Script.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Script name already exists")

    # Sanitize filenames to prevent path traversal
    safe_name = sanitize_filename(name)
    safe_file = sanitize_filename(file.filename)
    filename = f"{safe_name}_{safe_file}"

    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    file_location = os.path.join(SCRIPTS_DIR, filename)

    # Ensure we're not writing outside the scripts directory
    if not os.path.abspath(file_location).startswith(os.path.abspath(SCRIPTS_DIR)):
        raise HTTPException(status_code=400, detail="Invalid file path")

    with open(file_location, "wb+") as buffer:
        shutil.copyfileobj(file.file, buffer)

    db_script = models.Script(
        name=name, description=description, script_type=script_type.lower(), filename=filename
    )
    db.add(db_script)
    db.commit()
    db.refresh(db_script)
    logger.info(f"Script '{name}' uploaded by '{current_user.username}'")
    return db_script

@app.get("/scripts/", response_model=List[schemas.Script])
def list_scripts(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    if current_user.role != "admin" and not current_user.permissions.get("scripts"):
        raise HTTPException(status_code=403, detail="Permission denied")
    return db.query(models.Script).all()

def sanitize_script_args(args: Optional[List[str]]) -> List[str]:
    """Sanitize script arguments to prevent injection attacks."""
    if not args:
        return []
    sanitized = []
    # Dangerous patterns that could be used for command injection
    dangerous_patterns = [';', '&&', '||', '|', '`', '$', '>', '<', '\n', '\r']
    for arg in args:
        if not isinstance(arg, str):
            continue
        # Check for dangerous patterns
        for pattern in dangerous_patterns:
            if pattern in arg:
                raise HTTPException(status_code=400, detail=f"Invalid character in argument: {pattern}")
        # Limit argument length
        if len(arg) > 1000:
            raise HTTPException(status_code=400, detail="Argument too long (max 1000 characters)")
        sanitized.append(arg)
    return sanitized


class ScriptExecutionRequest(BaseModel):
    equipment_id: Optional[int] = None
    password: str
    script_args: Optional[List[str]] = None


@app.post("/scripts/{script_id}/run", response_model=schemas.ScriptExecution)
def run_script(
    script_id: int,
    exec_req: ScriptExecutionRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if current_user.role != "admin" and not current_user.permissions.get("scripts"):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Security Check: Verify Password
    if not auth.verify_password(exec_req.password, current_user.hashed_password):
        logger.warning(f"Failed password confirmation for script execution by '{current_user.username}'")
        raise HTTPException(status_code=403, detail="Invalid password confirmation")

    script = db.query(models.Script).filter(models.Script.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    # Validate equipment exists if specified and has remote execution configured
    if exec_req.equipment_id:
        equipment = db.query(models.Equipment).filter(models.Equipment.id == exec_req.equipment_id).first()
        if not equipment:
            raise HTTPException(status_code=404, detail="Target equipment not found")
        if not equipment.remote_ip or not equipment.remote_username:
            raise HTTPException(status_code=400, detail="Equipment is not configured for remote execution")

    # Sanitize script arguments
    safe_args = sanitize_script_args(exec_req.script_args)

    execution = models.ScriptExecution(
        script_id=script_id,
        equipment_id=exec_req.equipment_id,
        status="pending",
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    task = execute_script_task.delay(execution.id, script.filename, script.script_type, exec_req.equipment_id, safe_args)

    # Save task_id
    execution.task_id = task.id
    db.commit()
    logger.info(f"Script '{script.name}' execution started by '{current_user.username}'")

    return execution

@app.post("/executions/{execution_id}/stop")
def stop_execution(execution_id: int, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    if current_user.role != "admin" and not current_user.permissions.get("scripts"):
        raise HTTPException(status_code=403, detail="Permission denied")
        
    execution = db.query(models.ScriptExecution).filter(models.ScriptExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
        
    if execution.status in ["running", "pending"] and execution.task_id:
        # Revoke task
        execute_script_task.app.control.revoke(execution.task_id, terminate=True)
        execution.status = "cancelled"
        execution.stderr = (execution.stderr or "") + "\n[Stopped by user]"
        execution.completed_at = datetime.datetime.utcnow()
        db.commit()
        
    return {"message": "Execution stopped"}

@app.delete("/executions/")
def clear_executions(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_admin_user)):
    # Only admin can clear full history
    db.query(models.ScriptExecution).delete()
    db.commit()
    return {"message": "History cleared"}

@app.delete("/scripts/{script_id}")
def delete_script(script_id: int, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    if current_user.role != "admin" and not current_user.permissions.get("scripts"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    script = db.query(models.Script).filter(models.Script.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    # Delete file
    file_path = os.path.join(SCRIPTS_DIR, script.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    db.delete(script)
    db.commit()
    return {"ok": True}

@app.get("/executions/", response_model=List[schemas.ScriptExecution])
def list_executions(skip: int = 0, limit: int = 20, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    return db.query(models.ScriptExecution).order_by(models.ScriptExecution.started_at.desc()).offset(skip).limit(limit).all()

@app.get("/dashboard/stats")
def get_stats(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    return {
        "subnets": db.query(models.Subnet).count(),
        "ips": db.query(models.IPAddress).count(),
        "scripts": db.query(models.Script).count(),
        "executions": db.query(models.ScriptExecution).count(),
        "equipment": db.query(models.Equipment).count()
    }


# ==================== INVENTORY ENDPOINTS ====================

def check_inventory_permission(current_user: models.User):
    """Check if user has inventory permission."""
    if current_user.role != "admin" and not current_user.permissions.get("inventory"):
        raise HTTPException(status_code=403, detail="Permission denied")


# --- Manufacturers ---

@app.get("/inventory/manufacturers/", response_model=List[schemas.Manufacturer])
def list_manufacturers(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    check_inventory_permission(current_user)
    return db.query(models.Manufacturer).order_by(models.Manufacturer.name).all()


@app.post("/inventory/manufacturers/", response_model=schemas.Manufacturer)
def create_manufacturer(
    manufacturer: schemas.ManufacturerCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    check_inventory_permission(current_user)
    existing = db.query(models.Manufacturer).filter(models.Manufacturer.name == manufacturer.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Manufacturer already exists")
    db_manufacturer = models.Manufacturer(**manufacturer.model_dump())
    db.add(db_manufacturer)
    db.commit()
    db.refresh(db_manufacturer)
    return db_manufacturer


@app.put("/inventory/manufacturers/{manufacturer_id}", response_model=schemas.Manufacturer)
def update_manufacturer(
    manufacturer_id: int,
    manufacturer: schemas.ManufacturerCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    check_inventory_permission(current_user)
    db_manufacturer = db.query(models.Manufacturer).filter(models.Manufacturer.id == manufacturer_id).first()
    if not db_manufacturer:
        raise HTTPException(status_code=404, detail="Manufacturer not found")
    for key, value in manufacturer.model_dump().items():
        setattr(db_manufacturer, key, value)
    db.commit()
    db.refresh(db_manufacturer)
    return db_manufacturer


@app.delete("/inventory/manufacturers/{manufacturer_id}")
def delete_manufacturer(
    manufacturer_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    db_manufacturer = db.query(models.Manufacturer).filter(models.Manufacturer.id == manufacturer_id).first()
    if not db_manufacturer:
        raise HTTPException(status_code=404, detail="Manufacturer not found")
    # Check if manufacturer has models
    if db.query(models.EquipmentModel).filter(models.EquipmentModel.manufacturer_id == manufacturer_id).count() > 0:
        raise HTTPException(status_code=400, detail="Cannot delete manufacturer with associated models")
    db.delete(db_manufacturer)
    db.commit()
    return {"ok": True}


# --- Equipment Types ---

@app.get("/inventory/types/", response_model=List[schemas.EquipmentType])
def list_equipment_types(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    check_inventory_permission(current_user)
    return db.query(models.EquipmentType).order_by(models.EquipmentType.name).all()


@app.post("/inventory/types/", response_model=schemas.EquipmentType)
def create_equipment_type(
    equipment_type: schemas.EquipmentTypeCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    check_inventory_permission(current_user)
    existing = db.query(models.EquipmentType).filter(models.EquipmentType.name == equipment_type.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Equipment type already exists")
    db_type = models.EquipmentType(**equipment_type.model_dump())
    db.add(db_type)
    db.commit()
    db.refresh(db_type)
    return db_type


@app.put("/inventory/types/{type_id}", response_model=schemas.EquipmentType)
def update_equipment_type(
    type_id: int,
    equipment_type: schemas.EquipmentTypeCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    check_inventory_permission(current_user)
    db_type = db.query(models.EquipmentType).filter(models.EquipmentType.id == type_id).first()
    if not db_type:
        raise HTTPException(status_code=404, detail="Equipment type not found")
    for key, value in equipment_type.model_dump().items():
        setattr(db_type, key, value)
    db.commit()
    db.refresh(db_type)
    return db_type


@app.delete("/inventory/types/{type_id}")
def delete_equipment_type(
    type_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    db_type = db.query(models.EquipmentType).filter(models.EquipmentType.id == type_id).first()
    if not db_type:
        raise HTTPException(status_code=404, detail="Equipment type not found")
    if db.query(models.EquipmentModel).filter(models.EquipmentModel.equipment_type_id == type_id).count() > 0:
        raise HTTPException(status_code=400, detail="Cannot delete type with associated models")
    db.delete(db_type)
    db.commit()
    return {"ok": True}


# --- Equipment Models ---

@app.get("/inventory/models/", response_model=List[schemas.EquipmentModelFull])
def list_equipment_models(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    check_inventory_permission(current_user)
    return db.query(models.EquipmentModel).order_by(models.EquipmentModel.name).all()


@app.post("/inventory/models/", response_model=schemas.EquipmentModel)
def create_equipment_model(
    model: schemas.EquipmentModelCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    check_inventory_permission(current_user)
    # Validate foreign keys
    if not db.query(models.Manufacturer).filter(models.Manufacturer.id == model.manufacturer_id).first():
        raise HTTPException(status_code=400, detail="Manufacturer not found")
    if not db.query(models.EquipmentType).filter(models.EquipmentType.id == model.equipment_type_id).first():
        raise HTTPException(status_code=400, detail="Equipment type not found")
    db_model = models.EquipmentModel(**model.model_dump())
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return db_model


@app.put("/inventory/models/{model_id}", response_model=schemas.EquipmentModel)
def update_equipment_model(
    model_id: int,
    model: schemas.EquipmentModelCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    check_inventory_permission(current_user)
    db_model = db.query(models.EquipmentModel).filter(models.EquipmentModel.id == model_id).first()
    if not db_model:
        raise HTTPException(status_code=404, detail="Equipment model not found")
    for key, value in model.model_dump().items():
        setattr(db_model, key, value)
    db.commit()
    db.refresh(db_model)
    return db_model


@app.delete("/inventory/models/{model_id}")
def delete_equipment_model(
    model_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    db_model = db.query(models.EquipmentModel).filter(models.EquipmentModel.id == model_id).first()
    if not db_model:
        raise HTTPException(status_code=404, detail="Equipment model not found")
    if db.query(models.Equipment).filter(models.Equipment.model_id == model_id).count() > 0:
        raise HTTPException(status_code=400, detail="Cannot delete model with associated equipment")
    db.delete(db_model)
    db.commit()
    return {"ok": True}


# --- Locations ---

@app.get("/inventory/locations/", response_model=List[schemas.Location])
def list_locations(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    check_inventory_permission(current_user)
    return db.query(models.Location).order_by(models.Location.site, models.Location.building, models.Location.room).all()


@app.post("/inventory/locations/", response_model=schemas.Location)
def create_location(
    location: schemas.LocationCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    check_inventory_permission(current_user)
    db_location = models.Location(**location.model_dump())
    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    return db_location


@app.put("/inventory/locations/{location_id}", response_model=schemas.Location)
def update_location(
    location_id: int,
    location: schemas.LocationCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    check_inventory_permission(current_user)
    db_location = db.query(models.Location).filter(models.Location.id == location_id).first()
    if not db_location:
        raise HTTPException(status_code=404, detail="Location not found")
    for key, value in location.model_dump().items():
        setattr(db_location, key, value)
    db.commit()
    db.refresh(db_location)
    return db_location


@app.delete("/inventory/locations/{location_id}")
def delete_location(
    location_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    db_location = db.query(models.Location).filter(models.Location.id == location_id).first()
    if not db_location:
        raise HTTPException(status_code=404, detail="Location not found")
    if db.query(models.Equipment).filter(models.Equipment.location_id == location_id).count() > 0:
        raise HTTPException(status_code=400, detail="Cannot delete location with associated equipment")
    db.delete(db_location)
    db.commit()
    return {"ok": True}


# --- Suppliers ---

@app.get("/inventory/suppliers/", response_model=List[schemas.Supplier])
def list_suppliers(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    check_inventory_permission(current_user)
    return db.query(models.Supplier).order_by(models.Supplier.name).all()


@app.post("/inventory/suppliers/", response_model=schemas.Supplier)
def create_supplier(
    supplier: schemas.SupplierCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    check_inventory_permission(current_user)
    existing = db.query(models.Supplier).filter(models.Supplier.name == supplier.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Supplier already exists")
    db_supplier = models.Supplier(**supplier.model_dump())
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    return db_supplier


@app.put("/inventory/suppliers/{supplier_id}", response_model=schemas.Supplier)
def update_supplier(
    supplier_id: int,
    supplier: schemas.SupplierCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    check_inventory_permission(current_user)
    db_supplier = db.query(models.Supplier).filter(models.Supplier.id == supplier_id).first()
    if not db_supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    for key, value in supplier.model_dump().items():
        setattr(db_supplier, key, value)
    db.commit()
    db.refresh(db_supplier)
    return db_supplier


@app.delete("/inventory/suppliers/{supplier_id}")
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    db_supplier = db.query(models.Supplier).filter(models.Supplier.id == supplier_id).first()
    if not db_supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    if db.query(models.Equipment).filter(models.Equipment.supplier_id == supplier_id).count() > 0:
        raise HTTPException(status_code=400, detail="Cannot delete supplier with associated equipment")
    db.delete(db_supplier)
    db.commit()
    return {"ok": True}


# --- Equipment ---

@app.get("/inventory/equipment/", response_model=List[schemas.EquipmentFull])
def list_equipment(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    type_id: Optional[int] = None,
    location_id: Optional[int] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    check_inventory_permission(current_user)
    query = db.query(models.Equipment)
    if status:
        query = query.filter(models.Equipment.status == status)
    if type_id:
        query = query.join(models.EquipmentModel).filter(models.EquipmentModel.equipment_type_id == type_id)
    if location_id:
        query = query.filter(models.Equipment.location_id == location_id)
    return query.order_by(models.Equipment.name).offset(skip).limit(limit).all()


@app.get("/inventory/equipment/executable/", response_model=List[schemas.EquipmentFull])
def list_executable_equipment(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Get equipment configured for remote script execution."""
    if current_user.role != "admin" and not current_user.permissions.get("scripts"):
        raise HTTPException(status_code=403, detail="Permission denied")
    return db.query(models.Equipment).join(
        models.EquipmentModel
    ).join(
        models.EquipmentType
    ).filter(
        models.EquipmentType.supports_remote_execution == True,
        models.Equipment.remote_ip != None,
        models.Equipment.remote_username != None
    ).order_by(models.Equipment.name).all()


@app.get("/inventory/equipment/{equipment_id}", response_model=schemas.EquipmentFull)
def get_equipment(
    equipment_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    check_inventory_permission(current_user)
    equipment = db.query(models.Equipment).filter(models.Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return equipment


@app.post("/inventory/equipment/", response_model=schemas.Equipment)
def create_equipment(
    equipment: schemas.EquipmentCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    check_inventory_permission(current_user)

    # Validate status
    valid_statuses = ["in_service", "in_stock", "retired", "maintenance"]
    if equipment.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

    # Check unique constraints
    if equipment.serial_number:
        existing = db.query(models.Equipment).filter(models.Equipment.serial_number == equipment.serial_number).first()
        if existing:
            raise HTTPException(status_code=400, detail="Serial number already exists")
    if equipment.asset_tag:
        existing = db.query(models.Equipment).filter(models.Equipment.asset_tag == equipment.asset_tag).first()
        if existing:
            raise HTTPException(status_code=400, detail="Asset tag already exists")

    db_equipment = models.Equipment(**equipment.model_dump())
    db.add(db_equipment)
    db.commit()
    db.refresh(db_equipment)
    logger.info(f"Equipment '{equipment.name}' created by '{current_user.username}'")
    return db_equipment


@app.put("/inventory/equipment/{equipment_id}", response_model=schemas.Equipment)
def update_equipment(
    equipment_id: int,
    equipment: schemas.EquipmentUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    check_inventory_permission(current_user)
    db_equipment = db.query(models.Equipment).filter(models.Equipment.id == equipment_id).first()
    if not db_equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    update_data = equipment.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_equipment, key, value)

    db.commit()
    db.refresh(db_equipment)
    return db_equipment


@app.delete("/inventory/equipment/{equipment_id}")
def delete_equipment(
    equipment_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    db_equipment = db.query(models.Equipment).filter(models.Equipment.id == equipment_id).first()
    if not db_equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    # Unlink any associated IPs
    db.query(models.IPAddress).filter(models.IPAddress.equipment_id == equipment_id).update({"equipment_id": None})

    db.delete(db_equipment)
    db.commit()
    logger.info(f"Equipment '{db_equipment.name}' deleted by '{current_user.username}'")
    return {"ok": True}


# --- Equipment-IP Linking ---

@app.post("/inventory/equipment/{equipment_id}/link-ip")
def link_ip_to_equipment(
    equipment_id: int,
    link_request: schemas.IPLinkRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    check_inventory_permission(current_user)

    equipment = db.query(models.Equipment).filter(models.Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    ip = db.query(models.IPAddress).filter(models.IPAddress.id == link_request.ip_address_id).first()
    if not ip:
        raise HTTPException(status_code=404, detail="IP address not found")

    # Check if IP is already linked to another equipment
    if ip.equipment_id and ip.equipment_id != equipment_id:
        raise HTTPException(status_code=400, detail="IP address is already linked to another equipment")

    ip.equipment_id = equipment_id
    db.commit()
    logger.info(f"IP '{ip.address}' linked to equipment '{equipment.name}' by '{current_user.username}'")
    return {"ok": True, "message": f"IP {ip.address} linked to {equipment.name}"}


@app.delete("/inventory/equipment/{equipment_id}/unlink-ip/{ip_id}")
def unlink_ip_from_equipment(
    equipment_id: int,
    ip_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    check_inventory_permission(current_user)

    ip = db.query(models.IPAddress).filter(
        models.IPAddress.id == ip_id,
        models.IPAddress.equipment_id == equipment_id
    ).first()
    if not ip:
        raise HTTPException(status_code=404, detail="IP address not found or not linked to this equipment")

    ip.equipment_id = None
    db.commit()
    return {"ok": True}


# --- Available IPs for linking ---

@app.get("/inventory/available-ips/", response_model=List[schemas.IPAddress])
def get_available_ips(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    """Get all IPs that are not linked to any equipment."""
    check_inventory_permission(current_user)
    return db.query(models.IPAddress).filter(models.IPAddress.equipment_id == None).all()