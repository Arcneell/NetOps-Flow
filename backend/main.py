from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
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
            perms = {"ipam": True, "topology": True, "scripts": True, "settings": True}
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


# --- Server Management ---

@app.post("/servers/", response_model=schemas.Server)
def create_server(server: schemas.ServerCreate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_admin_user)):
    # Validate IP address format
    try:
        ipaddress.ip_address(server.ip_address)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid IP address format")

    # Validate connection type
    if server.connection_type not in ["ssh", "winrm"]:
        raise HTTPException(status_code=400, detail="Connection type must be 'ssh' or 'winrm'")

    # Validate OS type
    if server.os_type not in ["linux", "windows"]:
        raise HTTPException(status_code=400, detail="OS type must be 'linux' or 'windows'")

    # Validate port range
    if not (1 <= server.port <= 65535):
        raise HTTPException(status_code=400, detail="Port must be between 1 and 65535")

    # Check for duplicate server name
    existing = db.query(models.Server).filter(models.Server.name == server.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Server name already exists")

    db_server = models.Server(**server.model_dump())
    db.add(db_server)
    db.commit()
    db.refresh(db_server)
    logger.info(f"Server '{server.name}' created by '{current_user.username}'")
    return db_server

@app.get("/servers/", response_model=List[schemas.Server])
def read_servers(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    return db.query(models.Server).all()

@app.delete("/servers/{server_id}")
def delete_server(server_id: int, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_admin_user)):
    server = db.query(models.Server).filter(models.Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    db.delete(server)
    db.commit()
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

@app.get("/subnets/", response_model=List[schemas.Subnet])
def read_subnets(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    # Read access might be open or restricted. For now, let's keep it open to active users or check IPAM?
    # User asked to check rights. Let's enforce IPAM or Topology for reading subnets as they are basic network data?
    # Let's be safe: if you can't see IPAM or Topology, you probably shouldn't list subnets detailedly.
    # But for now, let's stick to modifying the write operations as critical path, and specific feature pages.
    if current_user.role != "admin" and not current_user.permissions.get("ipam") and not current_user.permissions.get("topology"):
         raise HTTPException(status_code=403, detail="Permission denied")
    return db.query(models.Subnet).offset(skip).limit(limit).all()

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
    server_id: Optional[int] = None
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

    # Validate server exists if specified
    if exec_req.server_id:
        server = db.query(models.Server).filter(models.Server.id == exec_req.server_id).first()
        if not server:
            raise HTTPException(status_code=404, detail="Target server not found")

    # Sanitize script arguments
    safe_args = sanitize_script_args(exec_req.script_args)

    execution = models.ScriptExecution(
        script_id=script_id,
        server_id=exec_req.server_id,
        status="pending",
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    task = execute_script_task.delay(execution.id, script.filename, script.script_type, exec_req.server_id, safe_args)

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
        "executions": db.query(models.ScriptExecution).count()
    }