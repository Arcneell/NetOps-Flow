from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal

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
    entity_id: Optional[int] = None

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
    entity_id: Optional[int] = None


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

class EquipmentBrief(BaseModel):
    """Brief equipment info for IPAM display"""
    id: int
    name: str
    class Config:
        from_attributes = True

class IPAddressWithEquipment(IPAddress):
    """IP Address with equipment relationship for IPAM"""
    equipment: Optional[EquipmentBrief] = None

class SubnetWithEquipment(BaseModel):
    """Subnet with IPs that include equipment info"""
    id: int
    cidr: str
    name: Optional[str] = None
    description: Optional[str] = None
    ips: List[IPAddressWithEquipment] = []
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
    equipment_id: Optional[int] = None
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
    supports_remote_execution: bool = False

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
    notes: Optional[str] = None
    model_id: Optional[int] = None
    location_id: Optional[int] = None
    supplier_id: Optional[int] = None
    entity_id: Optional[int] = None
    # Financial & Lifecycle fields
    purchase_date: Optional[datetime] = None
    purchase_price: Optional[Decimal] = None
    warranty_months: Optional[int] = None
    warranty_expiry: Optional[datetime] = None
    end_of_support: Optional[datetime] = None
    # DCIM fields
    rack_id: Optional[int] = None
    position_u: Optional[int] = Field(None, ge=1, le=42)
    height_u: Optional[int] = Field(1, ge=1, le=42)
    power_consumption_watts: Optional[int] = None
    pdu_id: Optional[int] = None
    pdu_port: Optional[str] = None
    redundant_pdu_id: Optional[int] = None
    redundant_pdu_port: Optional[str] = None
    # Remote execution fields
    remote_ip: Optional[str] = None
    os_type: Optional[str] = None
    connection_type: Optional[str] = None
    remote_username: Optional[str] = None
    remote_port: Optional[int] = None

class EquipmentCreate(EquipmentBase):
    remote_password: Optional[str] = None

class EquipmentUpdate(BaseModel):
    name: Optional[str] = None
    serial_number: Optional[str] = None
    asset_tag: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    model_id: Optional[int] = None
    location_id: Optional[int] = None
    supplier_id: Optional[int] = None
    entity_id: Optional[int] = None
    # Financial & Lifecycle fields
    purchase_date: Optional[datetime] = None
    purchase_price: Optional[Decimal] = None
    warranty_months: Optional[int] = None
    warranty_expiry: Optional[datetime] = None
    end_of_support: Optional[datetime] = None
    # DCIM fields
    rack_id: Optional[int] = None
    position_u: Optional[int] = None
    height_u: Optional[int] = None
    power_consumption_watts: Optional[int] = None
    pdu_id: Optional[int] = None
    pdu_port: Optional[str] = None
    redundant_pdu_id: Optional[int] = None
    redundant_pdu_port: Optional[str] = None
    # Remote execution fields
    remote_ip: Optional[str] = None
    os_type: Optional[str] = None
    connection_type: Optional[str] = None
    remote_username: Optional[str] = None
    remote_password: Optional[str] = None
    remote_port: Optional[int] = None

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


# ==================== ENTITY SCHEMAS ====================

class EntityBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True

class EntityCreate(EntityBase):
    pass

class Entity(EntityBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


# ==================== DCIM SCHEMAS ====================

# --- Rack ---
class RackBase(BaseModel):
    name: str
    location_id: int
    entity_id: Optional[int] = None
    height_u: int = 42
    width_mm: int = 600
    depth_mm: int = 1000
    max_power_kw: Optional[float] = None
    notes: Optional[str] = None

class RackCreate(RackBase):
    pass

class Rack(RackBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class RackFull(Rack):
    """Rack with location info"""
    location: Optional[Location] = None


# --- PDU ---
class PDUBase(BaseModel):
    name: str
    rack_id: Optional[int] = None
    pdu_type: str = "basic"
    total_ports: int = 8
    max_amps: Optional[float] = None
    voltage: int = 230
    phase: str = "single"
    notes: Optional[str] = None

class PDUCreate(PDUBase):
    pass

class PDU(PDUBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


# --- Rack Layout Schemas ---
class RackEquipmentDetail(BaseModel):
    """Detailed equipment info for rack layout visualization"""
    id: int
    name: str
    height_u: int
    is_start: bool
    status: str
    serial_number: Optional[str] = None
    asset_tag: Optional[str] = None
    model_name: Optional[str] = None
    manufacturer_name: Optional[str] = None
    management_ip: Optional[str] = None
    class Config:
        from_attributes = True


class RackSlot(BaseModel):
    """Single U slot in rack"""
    u: int
    equipment: Optional[RackEquipmentDetail] = None


class RackLayoutResponse(BaseModel):
    """Complete rack layout with equipment details"""
    rack: dict
    layout: List[RackSlot]
    pdus: List[dict]
    unassigned_equipment: List[dict] = []


# ==================== CONTRACT SCHEMAS ====================

class ContractBase(BaseModel):
    name: str
    contract_type: str
    contract_number: Optional[str] = None
    supplier_id: Optional[int] = None
    entity_id: Optional[int] = None
    start_date: date
    end_date: date
    annual_cost: Optional[Decimal] = None
    renewal_type: str = "manual"
    renewal_notice_days: int = 30
    notes: Optional[str] = None

class ContractCreate(ContractBase):
    pass

class Contract(ContractBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class ContractFull(Contract):
    """Contract with supplier info"""
    supplier: Optional[Supplier] = None


class ContractEquipmentBase(BaseModel):
    contract_id: int
    equipment_id: int
    notes: Optional[str] = None

class ContractEquipmentCreate(ContractEquipmentBase):
    pass

class ContractEquipment(ContractEquipmentBase):
    id: int
    class Config:
        from_attributes = True


# ==================== SOFTWARE & LICENSE SCHEMAS ====================

class SoftwareBase(BaseModel):
    name: str
    publisher: Optional[str] = None
    version: Optional[str] = None
    category: Optional[str] = None
    entity_id: Optional[int] = None
    notes: Optional[str] = None

class SoftwareCreate(SoftwareBase):
    pass

class Software(SoftwareBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


class SoftwareLicenseBase(BaseModel):
    software_id: int
    license_key: Optional[str] = None
    license_type: str = "perpetual"
    quantity: int = 1
    purchase_date: Optional[date] = None
    expiry_date: Optional[date] = None
    purchase_price: Optional[Decimal] = None
    supplier_id: Optional[int] = None
    notes: Optional[str] = None

class SoftwareLicenseCreate(SoftwareLicenseBase):
    pass

class SoftwareLicense(SoftwareLicenseBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


class SoftwareInstallationBase(BaseModel):
    software_id: int
    equipment_id: int
    installed_version: Optional[str] = None
    notes: Optional[str] = None

class SoftwareInstallationCreate(SoftwareInstallationBase):
    pass

class SoftwareInstallation(SoftwareInstallationBase):
    id: int
    installation_date: datetime
    discovered_at: Optional[datetime] = None
    class Config:
        from_attributes = True


class SoftwareWithCompliance(Software):
    """Software with license compliance info"""
    total_licenses: int = 0
    total_installations: int = 0
    compliance_status: str = "compliant"  # compliant, warning, violation


# ==================== NETWORK PORT SCHEMAS ====================

class NetworkPortBase(BaseModel):
    equipment_id: int
    name: str
    port_type: str = "ethernet"
    speed: Optional[str] = None
    mac_address: Optional[str] = None
    connected_to_id: Optional[int] = None
    notes: Optional[str] = None

class NetworkPortCreate(NetworkPortBase):
    pass

class NetworkPort(NetworkPortBase):
    id: int
    class Config:
        from_attributes = True

class NetworkPortFull(NetworkPort):
    """Network port with connection info"""
    connected_to: Optional["NetworkPort"] = None


# ==================== ATTACHMENT SCHEMAS ====================

class AttachmentBase(BaseModel):
    equipment_id: int
    category: Optional[str] = None
    description: Optional[str] = None

class AttachmentCreate(AttachmentBase):
    pass

class Attachment(BaseModel):
    id: int
    equipment_id: int
    filename: str
    original_filename: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    category: Optional[str] = None
    description: Optional[str] = None
    uploaded_by: Optional[str] = None
    uploaded_at: datetime
    class Config:
        from_attributes = True


# ==================== EXPIRATION NOTIFICATION SCHEMAS ====================

class ExpirationAlert(BaseModel):
    """Alert for expiring warranties/contracts"""
    type: str  # warranty, contract, license
    item_id: int
    item_name: str
    expiry_date: date
    days_remaining: int
    severity: str  # info, warning, critical