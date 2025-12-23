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
    equipment_id: Optional[int] = None
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


# ==================== INVENTORY SCHEMAS ====================

# --- Manufacturer ---
class ManufacturerBase(BaseModel):
    name: str
    website: Optional[str] = None
    notes: Optional[str] = None

class ManufacturerCreate(ManufacturerBase):
    pass

class Manufacturer(ManufacturerBase):
    id: int
    class Config:
        from_attributes = True


# --- Equipment Type ---
class EquipmentTypeBase(BaseModel):
    name: str
    icon: str = "pi-box"

class EquipmentTypeCreate(EquipmentTypeBase):
    pass

class EquipmentType(EquipmentTypeBase):
    id: int
    class Config:
        from_attributes = True


# --- Equipment Model ---
class EquipmentModelBase(BaseModel):
    name: str
    manufacturer_id: int
    equipment_type_id: int
    specs: Optional[Dict[str, Any]] = None

class EquipmentModelCreate(EquipmentModelBase):
    pass

class EquipmentModel(EquipmentModelBase):
    id: int
    class Config:
        from_attributes = True

class EquipmentModelFull(EquipmentModel):
    """Equipment model with expanded relationships"""
    manufacturer: Optional[Manufacturer] = None
    equipment_type: Optional[EquipmentType] = None


# --- Location ---
class LocationBase(BaseModel):
    site: str
    building: Optional[str] = None
    room: Optional[str] = None

class LocationCreate(LocationBase):
    pass

class Location(LocationBase):
    id: int
    class Config:
        from_attributes = True


# --- Supplier ---
class SupplierBase(BaseModel):
    name: str
    contact_email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None

class SupplierCreate(SupplierBase):
    pass

class Supplier(SupplierBase):
    id: int
    class Config:
        from_attributes = True


# --- Equipment ---
class EquipmentBase(BaseModel):
    name: str
    serial_number: Optional[str] = None
    asset_tag: Optional[str] = None
    status: str = "in_service"
    purchase_date: Optional[datetime] = None
    warranty_expiry: Optional[datetime] = None
    notes: Optional[str] = None
    model_id: Optional[int] = None
    location_id: Optional[int] = None
    supplier_id: Optional[int] = None

class EquipmentCreate(EquipmentBase):
    pass

class EquipmentUpdate(BaseModel):
    name: Optional[str] = None
    serial_number: Optional[str] = None
    asset_tag: Optional[str] = None
    status: Optional[str] = None
    purchase_date: Optional[datetime] = None
    warranty_expiry: Optional[datetime] = None
    notes: Optional[str] = None
    model_id: Optional[int] = None
    location_id: Optional[int] = None
    supplier_id: Optional[int] = None

class Equipment(EquipmentBase):
    id: int
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

class EquipmentFull(Equipment):
    """Equipment with expanded relationships"""
    model: Optional[EquipmentModelFull] = None
    location: Optional[Location] = None
    supplier: Optional[Supplier] = None
    ip_addresses: List[IPAddress] = []


# --- IP Link ---
class IPLinkRequest(BaseModel):
    ip_address_id: int