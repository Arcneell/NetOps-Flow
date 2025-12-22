from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- Auth ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserBase(BaseModel):
    username: str
    is_active: bool = True
    role: str = "user"
    permissions: Dict[str, bool] = {}

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema for updating user (all fields optional)."""
    password: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None
    permissions: Optional[Dict[str, bool]] = None

# --- Servers ---
class ServerBase(BaseModel):
    name: str
    ip_address: str
    os_type: str 
    connection_type: str = "ssh"
    username: str
    port: int = 22

class ServerCreate(ServerBase):
    password: str

class Server(ServerBase):
    id: int
    class Config:
        from_attributes = True

# --- IPAM ---
class IPAddressBase(BaseModel):
    address: str
    status: str = "available"
    hostname: Optional[str] = None
    mac_address: Optional[str] = None

class IPAddressCreate(IPAddressBase):
    pass

class IPAddress(IPAddressBase):
    id: int
    subnet_id: int
    last_scanned_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class SubnetBase(BaseModel):
    cidr: str
    name: Optional[str] = None
    description: Optional[str] = None

class SubnetCreate(SubnetBase):
    pass

class Subnet(SubnetBase):
    id: int
    ips: List[IPAddress] = []
    class Config:
        from_attributes = True

# --- Scripts ---
class ScriptBase(BaseModel):
    name: str
    description: Optional[str] = None
    script_type: str 

class ScriptCreate(ScriptBase):
    pass 

class Script(ScriptBase):
    id: int
    filename: str
    created_at: datetime
    class Config:
        from_attributes = True

class ScriptExecutionBase(BaseModel):
    script_id: Optional[int] = None
    server_id: Optional[int] = None 
    password: Optional[str] = None # For confirmation
    script_args: Optional[List[str]] = None

class ScriptExecution(ScriptExecutionBase):
    id: int
    status: str
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    class Config:
        from_attributes = True