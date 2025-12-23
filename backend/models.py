from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import INET, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    role = Column(String, default="user") # admin, user
    permissions = Column(JSON, default={}) # ex: {"ipam": true, "scripts": false}

class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    ip_address = Column(String, nullable=False)
    os_type = Column(String, nullable=False) # linux, windows
    connection_type = Column(String, default="ssh") # ssh, winrm
    username = Column(String, nullable=False)
    password = Column(String, nullable=True) 
    port = Column(Integer, default=22)

class Subnet(Base):
    __tablename__ = "subnets"

    id = Column(Integer, primary_key=True, index=True)
    cidr = Column(INET, unique=True, nullable=False)
    name = Column(String, nullable=True)
    description = Column(String, nullable=True)
    
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
    created_at = Column(DateTime, default=datetime.utcnow)

    executions = relationship("ScriptExecution", back_populates="script")

class ScriptExecution(Base):
    __tablename__ = "script_executions"

    id = Column(Integer, primary_key=True, index=True)
    script_id = Column(Integer, ForeignKey("scripts.id", ondelete="SET NULL"), nullable=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=True)
    task_id = Column(String, nullable=True)
    status = Column(String, default="pending")
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    script = relationship("Script", back_populates="executions")
    server = relationship("Server")


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

    equipment = relationship("Equipment", back_populates="location")


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


class Equipment(Base):
    """Main equipment/asset inventory"""
    __tablename__ = "equipment"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    serial_number = Column(String, unique=True, nullable=True, index=True)
    asset_tag = Column(String, unique=True, nullable=True, index=True)
    status = Column(String, default="in_service")  # in_service, in_stock, retired, maintenance
    purchase_date = Column(DateTime, nullable=True)
    warranty_expiry = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Foreign keys
    model_id = Column(Integer, ForeignKey("equipment_models.id"), nullable=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)

    # Relationships
    model = relationship("EquipmentModel", back_populates="equipment")
    location = relationship("Location", back_populates="equipment")
    supplier = relationship("Supplier", back_populates="equipment")
    ip_addresses = relationship("IPAddress", back_populates="equipment")