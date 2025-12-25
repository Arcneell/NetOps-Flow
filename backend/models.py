from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, Date, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import INET, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.core.database import Base


def utc_now():
    """Get current UTC time with timezone awareness."""
    return datetime.now(timezone.utc)


# ==================== MULTI-ENTITY MODEL ====================

class Entity(Base):
    """
    Entity for multi-tenant isolation.
    All major objects belong to an entity for logical separation.
    """
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    users = relationship("User", back_populates="entity")
    subnets = relationship("Subnet", back_populates="entity")
    equipment = relationship("Equipment", back_populates="entity")
    locations = relationship("Location", back_populates="entity")
    racks = relationship("Rack", back_populates="entity")
    contracts = relationship("Contract", back_populates="entity")
    software = relationship("Software", back_populates="entity")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    role = Column(String, default="user")  # admin, user
    permissions = Column(JSON, default={})  # ex: {"ipam": true, "scripts": false}
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=True)

    # MFA/TOTP fields
    mfa_enabled = Column(Boolean, default=False)
    totp_secret = Column(String, nullable=True)  # Encrypted TOTP secret

    entity = relationship("Entity", back_populates="users")


class Subnet(Base):
    __tablename__ = "subnets"

    id = Column(Integer, primary_key=True, index=True)
    cidr = Column(INET, unique=True, nullable=False)
    name = Column(String, nullable=True)
    description = Column(String, nullable=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=True)

    entity = relationship("Entity", back_populates="subnets")
    ips = relationship("IPAddress", back_populates="subnet", cascade="all, delete-orphan")

class IPAddress(Base):
    __tablename__ = "ip_addresses"

    id = Column(Integer, primary_key=True, index=True)
    address = Column(INET, unique=True, nullable=False)
    status = Column(String, default="available")
    hostname = Column(String, nullable=True)
    mac_address = Column(String, nullable=True)
    last_scanned_at = Column(DateTime, nullable=True)
    subnet_id = Column(Integer, ForeignKey("subnets.id"))
    equipment_id = Column(Integer, ForeignKey("equipment.id", ondelete="SET NULL"), nullable=True)

    subnet = relationship("Subnet", back_populates="ips")
    equipment = relationship("Equipment", back_populates="ip_addresses")

class Script(Base):
    __tablename__ = "scripts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    filename = Column(String, nullable=False)
    script_type = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    executions = relationship("ScriptExecution", back_populates="script")

class ScriptExecution(Base):
    __tablename__ = "script_executions"

    id = Column(Integer, primary_key=True, index=True)
    script_id = Column(Integer, ForeignKey("scripts.id", ondelete="SET NULL"), nullable=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id", ondelete="SET NULL"), nullable=True)
    task_id = Column(String, nullable=True)
    status = Column(String, default="pending")
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    started_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime, nullable=True)

    script = relationship("Script", back_populates="executions")
    equipment = relationship("Equipment")


# ==================== INVENTORY MODELS ====================

class Manufacturer(Base):
    """Hardware manufacturers (Dell, HP, Cisco, etc.)"""
    __tablename__ = "manufacturers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    website = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    models = relationship("EquipmentModel", back_populates="manufacturer")


class EquipmentType(Base):
    """Equipment categories (Server, Switch, Router, PC, etc.)"""
    __tablename__ = "equipment_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    icon = Column(String, default="pi-box")  # PrimeIcons class
    supports_remote_execution = Column(Boolean, default=False)  # Enable SSH/WinRM fields

    models = relationship("EquipmentModel", back_populates="equipment_type")


class EquipmentModel(Base):
    """Product models/SKUs (PowerEdge R740, Catalyst 9300, etc.)"""
    __tablename__ = "equipment_models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    manufacturer_id = Column(Integer, ForeignKey("manufacturers.id"), nullable=False)
    equipment_type_id = Column(Integer, ForeignKey("equipment_types.id"), nullable=False)
    specs = Column(JSON, nullable=True)  # {"cpu": "...", "ram": "...", etc.}

    manufacturer = relationship("Manufacturer", back_populates="models")
    equipment_type = relationship("EquipmentType", back_populates="models")
    equipment = relationship("Equipment", back_populates="model")


class Location(Base):
    """Physical locations (Site > Building > Room)"""
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    site = Column(String, nullable=False)
    building = Column(String, nullable=True)
    room = Column(String, nullable=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=True)

    entity = relationship("Entity", back_populates="locations")
    equipment = relationship("Equipment", back_populates="location")
    racks = relationship("Rack", back_populates="location")


class Supplier(Base):
    """Equipment suppliers/vendors"""
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    contact_email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    website = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    equipment = relationship("Equipment", back_populates="supplier")
    contracts = relationship("Contract", back_populates="supplier")


class Equipment(Base):
    """Main equipment/asset inventory with financial and DCIM fields"""
    __tablename__ = "equipment"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    serial_number = Column(String, unique=True, nullable=True, index=True)
    asset_tag = Column(String, unique=True, nullable=True, index=True)
    status = Column(String, default="in_service")  # in_service, in_stock, retired, maintenance
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Financial & Lifecycle fields
    purchase_date = Column(DateTime, nullable=True)
    purchase_price = Column(Numeric(12, 2), nullable=True)
    warranty_months = Column(Integer, nullable=True)  # Duration in months
    warranty_expiry = Column(DateTime, nullable=True)
    end_of_support = Column(DateTime, nullable=True)

    # DCIM - Rack placement fields
    rack_id = Column(Integer, ForeignKey("racks.id"), nullable=True)
    position_u = Column(Integer, nullable=True)  # Starting U position (1-42)
    height_u = Column(Integer, default=1)  # Height in U (1, 2, 4, etc.)

    # Power tracking
    power_consumption_watts = Column(Integer, nullable=True)
    pdu_id = Column(Integer, ForeignKey("pdus.id"), nullable=True)
    pdu_port = Column(String, nullable=True)
    redundant_pdu_id = Column(Integer, ForeignKey("pdus.id"), nullable=True)
    redundant_pdu_port = Column(String, nullable=True)

    # Foreign keys
    model_id = Column(Integer, ForeignKey("equipment_models.id"), nullable=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=True)

    # Remote execution fields (optional, used when equipment type supports it)
    remote_ip = Column(String, nullable=True)
    os_type = Column(String, nullable=True)  # linux, windows
    connection_type = Column(String, nullable=True)  # ssh, winrm
    remote_username = Column(String, nullable=True)
    remote_password = Column(String, nullable=True)
    remote_port = Column(Integer, nullable=True)

    # Relationships
    model = relationship("EquipmentModel", back_populates="equipment")
    location = relationship("Location", back_populates="equipment")
    supplier = relationship("Supplier", back_populates="equipment")
    entity = relationship("Entity", back_populates="equipment")
    ip_addresses = relationship("IPAddress", back_populates="equipment")
    rack = relationship("Rack", back_populates="equipment", foreign_keys=[rack_id])
    pdu = relationship("PDU", back_populates="equipment", foreign_keys=[pdu_id])
    redundant_pdu = relationship("PDU", foreign_keys=[redundant_pdu_id])
    network_ports = relationship("NetworkPort", back_populates="equipment", cascade="all, delete-orphan")
    software_installations = relationship("SoftwareInstallation", back_populates="equipment", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="equipment", cascade="all, delete-orphan")
    contracts = relationship("ContractEquipment", back_populates="equipment")


# ==================== DCIM MODELS ====================

class Rack(Base):
    """
    Server rack for DCIM placement.
    Standard racks have 42U capacity.
    """
    __tablename__ = "racks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=True)
    height_u = Column(Integer, default=42)  # Total U capacity
    width_mm = Column(Integer, default=600)  # Standard 600mm or 800mm
    depth_mm = Column(Integer, default=1000)
    max_power_kw = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    location = relationship("Location", back_populates="racks")
    entity = relationship("Entity", back_populates="racks")
    equipment = relationship("Equipment", back_populates="rack", foreign_keys="Equipment.rack_id")
    pdus = relationship("PDU", back_populates="rack")


class PDU(Base):
    """
    Power Distribution Unit for rack power management.
    """
    __tablename__ = "pdus"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    rack_id = Column(Integer, ForeignKey("racks.id"), nullable=True)
    pdu_type = Column(String, default="basic")  # basic, metered, switched, smart
    total_ports = Column(Integer, default=8)
    max_amps = Column(Float, nullable=True)
    voltage = Column(Integer, default=230)  # 230V or 120V
    phase = Column(String, default="single")  # single, three
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    rack = relationship("Rack", back_populates="pdus")
    equipment = relationship("Equipment", back_populates="pdu", foreign_keys="Equipment.pdu_id")


# ==================== CONTRACT MODELS ====================

class Contract(Base):
    """
    Service contracts (maintenance, insurance, leasing).
    """
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    contract_type = Column(String, nullable=False)  # maintenance, insurance, leasing, support
    contract_number = Column(String, unique=True, nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    annual_cost = Column(Numeric(12, 2), nullable=True)
    renewal_type = Column(String, default="manual")  # auto, manual, none
    renewal_notice_days = Column(Integer, default=30)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    supplier = relationship("Supplier", back_populates="contracts")
    entity = relationship("Entity", back_populates="contracts")
    equipment_links = relationship("ContractEquipment", back_populates="contract", cascade="all, delete-orphan")


class ContractEquipment(Base):
    """
    Many-to-many relationship between contracts and equipment.
    """
    __tablename__ = "contract_equipment"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=False)
    notes = Column(Text, nullable=True)

    contract = relationship("Contract", back_populates="equipment_links")
    equipment = relationship("Equipment", back_populates="contracts")

    __table_args__ = (
        UniqueConstraint('contract_id', 'equipment_id', name='uq_contract_equipment'),
    )


# ==================== SOFTWARE & LICENSE MODELS ====================

class Software(Base):
    """
    Software catalog for license management.
    """
    __tablename__ = "software"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    publisher = Column(String, nullable=True)
    version = Column(String, nullable=True)
    category = Column(String, nullable=True)  # os, database, middleware, application, utility
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    entity = relationship("Entity", back_populates="software")
    licenses = relationship("SoftwareLicense", back_populates="software", cascade="all, delete-orphan")
    installations = relationship("SoftwareInstallation", back_populates="software", cascade="all, delete-orphan")


class SoftwareLicense(Base):
    """
    Software license with quota management.
    """
    __tablename__ = "software_licenses"

    id = Column(Integer, primary_key=True, index=True)
    software_id = Column(Integer, ForeignKey("software.id"), nullable=False)
    license_key = Column(String, nullable=True)  # Encrypted
    license_type = Column(String, default="perpetual")  # perpetual, subscription, oem, volume
    quantity = Column(Integer, default=1)  # Number of allowed installations
    purchase_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    purchase_price = Column(Numeric(12, 2), nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    software = relationship("Software", back_populates="licenses")
    supplier = relationship("Supplier")


class SoftwareInstallation(Base):
    """
    Tracks software installations on equipment.
    """
    __tablename__ = "software_installations"

    id = Column(Integer, primary_key=True, index=True)
    software_id = Column(Integer, ForeignKey("software.id"), nullable=False)
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=False)
    installed_version = Column(String, nullable=True)
    installation_date = Column(DateTime, default=utc_now)
    discovered_at = Column(DateTime, nullable=True)  # For auto-discovered software
    notes = Column(Text, nullable=True)

    software = relationship("Software", back_populates="installations")
    equipment = relationship("Equipment", back_populates="software_installations")

    __table_args__ = (
        UniqueConstraint('software_id', 'equipment_id', name='uq_software_installation'),
    )


# ==================== NETWORK PORT & PATCHING MODELS ====================

class NetworkPort(Base):
    """
    Network ports on equipment for physical connectivity mapping.
    """
    __tablename__ = "network_ports"

    id = Column(Integer, primary_key=True, index=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=False)
    name = Column(String, nullable=False)  # e.g., "eth0", "GigabitEthernet0/1"
    port_type = Column(String, default="ethernet")  # ethernet, fiber, console, management
    speed = Column(String, nullable=True)  # 1G, 10G, 25G, 40G, 100G
    mac_address = Column(String, nullable=True)
    connected_to_id = Column(Integer, ForeignKey("network_ports.id"), nullable=True)
    notes = Column(Text, nullable=True)

    equipment = relationship("Equipment", back_populates="network_ports")
    connected_to = relationship("NetworkPort", remote_side=[id], foreign_keys=[connected_to_id])


# ==================== DOCUMENT ATTACHMENT MODEL ====================

class Attachment(Base):
    """
    File attachments for equipment (invoices, diagrams, etc.).
    """
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=False)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_type = Column(String, nullable=True)  # pdf, png, jpg, doc
    file_size = Column(Integer, nullable=True)  # Size in bytes
    category = Column(String, nullable=True)  # invoice, diagram, manual, photo, other
    description = Column(Text, nullable=True)
    uploaded_by = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=utc_now)

    equipment = relationship("Equipment", back_populates="attachments")


# ==================== AUDIT LOG MODEL ====================

class AuditLog(Base):
    """
    System audit log for tracking critical operations.
    Logs all create, update, and delete operations on sensitive resources.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=utc_now, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    username = Column(String, nullable=False)  # Denormalized for historical accuracy
    action = Column(String, nullable=False)  # CREATE, UPDATE, DELETE, LOGIN, LOGOUT
    resource_type = Column(String, nullable=False, index=True)  # equipment, subnet, user, etc.
    resource_id = Column(String, nullable=True)  # ID of the affected resource
    entity_id = Column(Integer, ForeignKey("entities.id", ondelete="SET NULL"), nullable=True)
    ip_address = Column(String, nullable=True)  # Client IP address
    changes = Column(JSON, nullable=True)  # {"field": {"old": "value", "new": "value"}}
    extra_data = Column(JSON, nullable=True)  # Additional context (renamed from metadata to avoid SQLAlchemy conflict)

    # Note: No relationship to User to preserve logs even after user deletion