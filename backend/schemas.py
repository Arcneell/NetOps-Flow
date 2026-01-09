from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal

# --- Auth ---
class Token(BaseModel):
    access_token: str
    token_type: str
    user: Optional[Dict[str, Any]] = None

class TokenWithRefresh(BaseModel):
    """Token response including refresh token."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Access token expiration in seconds
    user: Optional[Dict[str, Any]] = None

class RefreshTokenRequest(BaseModel):
    """Request to refresh access token."""
    refresh_token: str

class TokenData(BaseModel):
    username: Optional[str] = None

class MFAResponse(BaseModel):
    """Response when MFA is required after password validation."""
    mfa_required: bool = True
    user_id: int
    message: str = "MFA verification required"

class MFAVerifyRequest(BaseModel):
    """Request to verify MFA code."""
    user_id: int
    code: str

class MFASetupResponse(BaseModel):
    """Response for MFA setup with QR code URI."""
    secret: str
    qr_uri: str
    message: str = "Scan QR code with authenticator app"

class MFAEnableRequest(BaseModel):
    """Request to enable MFA with verification code."""
    code: str

class MFADisableRequest(BaseModel):
    """Request to disable MFA with password verification."""
    password: str

class UserBase(BaseModel):
    username: str
    email: Optional[str] = None
    is_active: bool = True
    role: str = "user"  # user, tech, admin, superadmin
    permissions: List[str] = Field(default_factory=list)  # Granular permissions for tech/admin
    entity_id: Optional[int] = None

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    avatar: Optional[str] = None
    mfa_enabled: bool = False
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema for updating user (all fields optional)."""
    email: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None  # user, tech, admin, superadmin
    permissions: Optional[List[str]] = None  # Granular permissions for tech/admin
    entity_id: Optional[int] = None


class UserProfileUpdate(BaseModel):
    """Schema for users to update their own profile."""
    email: Optional[str] = None


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
    """Subnet with IP count (IPs loaded separately with pagination)"""
    id: int
    cidr: str
    name: Optional[str] = None
    description: Optional[str] = None
    ip_count: int = 0
    class Config:
        from_attributes = True


class PaginatedIPResponse(BaseModel):
    """Paginated response for IP addresses."""
    items: List[IPAddressWithEquipment]
    total: int
    skip: int
    limit: int

class SubnetBase(BaseModel):
    cidr: str
    name: Optional[str] = None
    description: Optional[str] = None

class SubnetCreate(SubnetBase):
    pass

class SubnetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class Subnet(SubnetBase):
    id: int
    ips: List[IPAddress] = Field(default_factory=list)
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
    hierarchy_level: Optional[int] = 3  # 0=top (router), 1=firewall, 2=switch, 3=server, 4=storage

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
    model_config = {"protected_namespaces": ()}

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
    model_config = {"protected_namespaces": ()}

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
    ip_addresses: List[IPAddress] = Field(default_factory=list)


class PaginatedEquipmentResponse(BaseModel):
    """Paginated response for equipment list"""
    items: List[EquipmentFull]
    total: int
    skip: int
    limit: int


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
    model_config = {"protected_namespaces": (), "from_attributes": True}

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


class RackSlot(BaseModel):
    """Single U slot in rack"""
    u: int
    equipment: Optional[RackEquipmentDetail] = None


class RackLayoutResponse(BaseModel):
    """Complete rack layout with equipment details"""
    rack: dict
    layout: List[RackSlot]
    pdus: List[dict]
    unassigned_equipment: List[dict] = Field(default_factory=list)


# ==================== BULK OPERATION SCHEMAS ====================

class BulkEquipmentDelete(BaseModel):
    """Request to delete multiple equipment."""
    equipment_ids: List[int] = Field(..., min_length=1, max_length=100)

class BulkEquipmentStatusUpdate(BaseModel):
    """Request to update status of multiple equipment."""
    equipment_ids: List[int] = Field(..., min_length=1, max_length=100)
    status: str = Field(..., pattern="^(in_service|in_stock|retired|maintenance)$")

class BulkEquipmentLocationUpdate(BaseModel):
    """Request to update location of multiple equipment."""
    equipment_ids: List[int] = Field(..., min_length=1, max_length=100)
    location_id: Optional[int] = None  # None to clear location

class BulkTicketClose(BaseModel):
    """Request to close multiple tickets."""
    ticket_ids: List[int] = Field(..., min_length=1, max_length=100)
    resolution: Optional[str] = None

class BulkTicketAssign(BaseModel):
    """Request to assign multiple tickets."""
    ticket_ids: List[int] = Field(..., min_length=1, max_length=100)
    assigned_to_id: Optional[int] = None  # None to unassign

class BulkTicketPriority(BaseModel):
    """Request to update priority of multiple tickets."""
    ticket_ids: List[int] = Field(..., min_length=1, max_length=100)
    priority: str = Field(..., pattern="^(low|medium|high|critical)$")

class BulkTicketStatus(BaseModel):
    """Request to update status of multiple tickets."""
    ticket_ids: List[int] = Field(..., min_length=1, max_length=100)
    status: str = Field(..., pattern="^(new|open|pending|resolved|closed)$")

class BulkTicketType(BaseModel):
    """Request to update type of multiple tickets."""
    ticket_ids: List[int] = Field(..., min_length=1, max_length=100)
    ticket_type: str = Field(..., pattern="^(incident|request|problem|change)$")

class BulkIPStatusUpdate(BaseModel):
    """Request to update status of multiple IP addresses."""
    ip_ids: List[int] = Field(..., min_length=1, max_length=100)
    status: str = Field(..., pattern="^(available|reserved|assigned|dhcp)$")

class BulkIPRelease(BaseModel):
    """Request to release multiple IP addresses (set to available, clear equipment link)."""
    ip_ids: List[int] = Field(..., min_length=1, max_length=100)

class BulkOperationResult(BaseModel):
    """Result of a bulk operation."""
    success: bool
    processed: int
    failed: int
    errors: List[str] = Field(default_factory=list)


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


class PaginatedSoftwareResponse(BaseModel):
    """Paginated response for software list"""
    items: List[SoftwareWithCompliance]
    total: int
    skip: int
    limit: int


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
    """Network port with connection info and connected equipment details"""
    connected_to: Optional["NetworkPort"] = None
    # Additional fields for connected equipment (populated by router)
    connected_equipment_id: Optional[int] = None
    connected_equipment_name: Optional[str] = None
    connected_port_name: Optional[str] = None


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


# ==================== TICKET SCHEMAS ====================

class TicketBase(BaseModel):
    title: str
    description: str
    ticket_type: str = "incident"  # incident, request, problem, change
    category: Optional[str] = None
    subcategory: Optional[str] = None
    priority: str = "medium"  # critical, high, medium, low
    impact: str = "medium"
    urgency: str = "medium"
    equipment_id: Optional[int] = None
    entity_id: Optional[int] = None


class TicketCreate(TicketBase):
    assigned_to_id: Optional[int] = None
    assigned_group: Optional[str] = None


class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    ticket_type: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    impact: Optional[str] = None
    urgency: Optional[str] = None
    assigned_to_id: Optional[int] = None
    assigned_group: Optional[str] = None
    equipment_id: Optional[int] = None
    resolution: Optional[str] = None
    resolution_code: Optional[str] = None


class TicketCommentBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=50000)  # Max 50KB to prevent abuse
    is_internal: bool = False
    is_resolution: bool = False


class TicketCommentCreate(TicketCommentBase):
    pass


class TicketComment(TicketCommentBase):
    id: int
    ticket_id: int
    user_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TicketCommentFull(TicketComment):
    """Comment with user info"""
    username: Optional[str] = None
    user_avatar: Optional[str] = None


class TicketHistoryItem(BaseModel):
    id: int
    ticket_id: int
    user_id: Optional[int] = None
    action: str
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    created_at: datetime
    username: Optional[str] = None

    class Config:
        from_attributes = True


class TicketAttachmentBase(BaseModel):
    pass


class TicketAttachment(BaseModel):
    id: int
    ticket_id: int
    filename: str
    original_filename: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    uploaded_by_id: Optional[int] = None
    uploaded_at: datetime

    class Config:
        from_attributes = True


class Ticket(TicketBase):
    id: int
    ticket_number: str
    status: str
    requester_id: Optional[int] = None
    assigned_to_id: Optional[int] = None
    assigned_group: Optional[str] = None
    sla_due_date: Optional[datetime] = None
    first_response_at: Optional[datetime] = None
    first_response_due: Optional[datetime] = None
    resolution_due: Optional[datetime] = None
    sla_breached: bool = False
    resolution: Optional[str] = None
    resolution_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TicketBrief(BaseModel):
    """Brief ticket info for lists"""
    id: int
    ticket_number: str
    title: str
    status: str
    priority: str
    ticket_type: str
    created_at: datetime
    requester_name: Optional[str] = None
    assigned_to_name: Optional[str] = None

    class Config:
        from_attributes = True


class PaginatedTicketResponse(BaseModel):
    """Paginated response for ticket list"""
    items: List[TicketBrief]
    total: int
    skip: int
    limit: int


class TicketFull(Ticket):
    """Ticket with all relationships"""
    requester_name: Optional[str] = None
    assigned_to_name: Optional[str] = None
    equipment_name: Optional[str] = None
    comments: List[TicketCommentFull] = Field(default_factory=list)
    history: List[TicketHistoryItem] = Field(default_factory=list)
    attachments: List[TicketAttachment] = Field(default_factory=list)


class TicketStats(BaseModel):
    """Dashboard statistics for tickets"""
    total: int = 0
    new: int = 0
    open: int = 0
    pending: int = 0
    resolved: int = 0
    closed: int = 0
    sla_breached: int = 0
    by_priority: Dict[str, int] = {}
    by_type: Dict[str, int] = {}


# ==================== NOTIFICATION SCHEMAS ====================

class NotificationBase(BaseModel):
    title: str
    message: str
    notification_type: str = "info"  # info, warning, error, success, ticket
    link_type: Optional[str] = None
    link_id: Optional[int] = None


class NotificationCreate(NotificationBase):
    user_id: int
    expires_at: Optional[datetime] = None


class Notification(NotificationBase):
    id: int
    user_id: int
    is_read: bool = False
    read_at: Optional[datetime] = None
    created_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationCount(BaseModel):
    total: int = 0
    unread: int = 0


# ==================== KNOWLEDGE BASE SCHEMAS ====================

# --- Knowledge Category ---
class KnowledgeCategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    icon: str = Field("pi-folder", max_length=50)
    color: str = Field("#0ea5e9", max_length=20)
    is_active: bool = True
    display_order: int = 0


class KnowledgeCategoryCreate(KnowledgeCategoryBase):
    pass


class KnowledgeCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


class KnowledgeCategory(KnowledgeCategoryBase):
    id: int
    article_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KnowledgeArticleBase(BaseModel):
    title: str
    content: str
    summary: Optional[str] = None
    category: Optional[str] = None  # Legacy string category (deprecated)
    category_id: Optional[int] = None  # New foreign key to KnowledgeCategory
    tags: List[str] = Field(default_factory=list)
    is_published: bool = False
    is_internal: bool = False


class KnowledgeArticleCreate(KnowledgeArticleBase):
    entity_id: Optional[int] = None


class KnowledgeArticleUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    category: Optional[str] = None  # Legacy
    category_id: Optional[int] = None
    tags: Optional[List[str]] = None
    is_published: Optional[bool] = None
    is_internal: Optional[bool] = None


class KnowledgeArticle(KnowledgeArticleBase):
    id: int
    slug: str
    author_id: Optional[int] = None
    last_editor_id: Optional[int] = None
    view_count: int = 0
    helpful_count: int = 0
    not_helpful_count: int = 0
    version: int = 1
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None
    entity_id: Optional[int] = None

    class Config:
        from_attributes = True


class KnowledgeArticleBrief(BaseModel):
    """Brief article info for lists"""
    id: int
    title: str
    slug: str
    summary: Optional[str] = None
    category: Optional[str] = None  # Legacy
    category_id: Optional[int] = None
    category_name: Optional[str] = None  # From KnowledgeCategory relationship
    is_published: bool
    is_internal: bool = False
    view_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class PaginatedKnowledgeResponse(BaseModel):
    """Paginated response for knowledge articles"""
    items: List[KnowledgeArticleBrief]
    total: int
    skip: int
    limit: int


class KnowledgeArticleFull(KnowledgeArticle):
    """Article with author info"""
    author_name: Optional[str] = None
    last_editor_name: Optional[str] = None
    category_name: Optional[str] = None  # From KnowledgeCategory relationship


class KnowledgeArticleFeedback(BaseModel):
    helpful: bool


# ==================== SLA POLICY SCHEMAS ====================

class SLAPolicyBase(BaseModel):
    name: str
    description: Optional[str] = None
    critical_response_time: int = 15
    critical_resolution_time: int = 240
    high_response_time: int = 60
    high_resolution_time: int = 480
    medium_response_time: int = 240
    medium_resolution_time: int = 1440
    low_response_time: int = 480
    low_resolution_time: int = 2880
    business_hours_only: bool = True
    business_start: str = "09:00"
    business_end: str = "18:00"
    business_days: List[int] = [1, 2, 3, 4, 5]


class SLAPolicyCreate(SLAPolicyBase):
    is_default: bool = False
    entity_id: Optional[int] = None


class SLAPolicy(SLAPolicyBase):
    id: int
    is_default: bool
    is_active: bool
    entity_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== TICKET TEMPLATE SCHEMAS ====================

class TicketTemplateBase(BaseModel):
    """Base schema for ticket templates."""
    name: str = Field(..., min_length=1, max_length=100, description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    title_template: str = Field(..., min_length=1, max_length=200, description="Title template with optional placeholders")
    description_template: Optional[str] = Field(None, description="Description template")
    ticket_type: str = Field("request", description="Ticket type: incident, request, problem, change")
    category: Optional[str] = Field(None, description="Ticket category")
    subcategory: Optional[str] = Field(None, description="Ticket subcategory")
    priority: str = Field("medium", description="Default priority: critical, high, medium, low")
    assigned_group: Optional[str] = Field(None, description="Default assignment group")
    is_active: bool = Field(True, description="Whether template is active")
    is_public: bool = Field(True, description="Visible to all users or just tech/admin")
    icon: str = Field("pi-ticket", description="PrimeIcons class for display")
    color: str = Field("#0ea5e9", description="Accent color for UI")


class TicketTemplateCreate(TicketTemplateBase):
    """Schema for creating a ticket template."""
    entity_id: Optional[int] = None


class TicketTemplateUpdate(BaseModel):
    """Schema for updating a ticket template."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    title_template: Optional[str] = Field(None, min_length=1, max_length=200)
    description_template: Optional[str] = None
    ticket_type: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    priority: Optional[str] = None
    assigned_group: Optional[str] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class TicketTemplate(TicketTemplateBase):
    """Schema for ticket template response."""
    id: int
    usage_count: int = 0
    entity_id: Optional[int] = None
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TicketFromTemplate(BaseModel):
    """Schema for creating a ticket from a template."""
    template_id: int = Field(..., description="Template ID to use")
    title: Optional[str] = Field(None, description="Override title (optional)")
    description: Optional[str] = Field(None, description="Additional description")
    equipment_id: Optional[int] = Field(None, description="Related equipment")
