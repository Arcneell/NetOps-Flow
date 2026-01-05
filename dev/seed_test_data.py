#!/usr/bin/env python3
"""
Inframate Test Data Seeder
Generates comprehensive test data for all modules.

Usage:
    python dev/seed_test_data.py [--clean] [--minimal]

Options:
    --clean     Remove existing test data before seeding
    --minimal   Generate minimal data set (faster)
"""

import os
import sys
import random
import string
import argparse
from datetime import datetime, timedelta, timezone, date
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment variables before imports
os.environ.setdefault("DATABASE_URL", "postgresql://inframate:inframatepassword@localhost:5432/inframate")

from sqlalchemy.orm import Session
from backend.core.database import SessionLocal, engine
from backend.core.security import get_password_hash
from backend import models


# =============================================================================
# Configuration
# =============================================================================

MINIMAL_COUNT = 3
NORMAL_COUNT = 10

# Test users with different roles
TEST_USERS = [
    {"username": "tech_user", "email": "tech@test.local", "role": "tech", "permissions": ["ipam", "inventory", "dcim", "topology"]},
    {"username": "admin_user", "email": "admin@test.local", "role": "admin", "permissions": []},
    {"username": "helpdesk", "email": "helpdesk@test.local", "role": "user", "permissions": []},
    {"username": "netadmin", "email": "netadmin@test.local", "role": "tech", "permissions": ["ipam", "topology", "network_ports"]},
    {"username": "inventory_tech", "email": "inventory@test.local", "role": "tech", "permissions": ["inventory", "dcim", "contracts", "software"]},
]

# Sample data
MANUFACTURERS = [
    {"name": "Cisco Systems", "website": "https://cisco.com"},
    {"name": "Hewlett Packard Enterprise", "website": "https://hpe.com"},
    {"name": "Dell Technologies", "website": "https://dell.com"},
    {"name": "Juniper Networks", "website": "https://juniper.net"},
    {"name": "Arista Networks", "website": "https://arista.com"},
    {"name": "Fortinet", "website": "https://fortinet.com"},
    {"name": "Palo Alto Networks", "website": "https://paloaltonetworks.com"},
    {"name": "Lenovo", "website": "https://lenovo.com"},
    {"name": "Supermicro", "website": "https://supermicro.com"},
    {"name": "APC by Schneider", "website": "https://apc.com"},
]

EQUIPMENT_TYPES = [
    {"name": "Server", "icon": "pi-server", "supports_remote_execution": True},
    {"name": "Switch", "icon": "pi-sitemap", "supports_remote_execution": True},
    {"name": "Router", "icon": "pi-share-alt", "supports_remote_execution": True},
    {"name": "Firewall", "icon": "pi-shield", "supports_remote_execution": True},
    {"name": "Storage", "icon": "pi-database", "supports_remote_execution": False},
    {"name": "PDU", "icon": "pi-bolt", "supports_remote_execution": False},
    {"name": "UPS", "icon": "pi-bolt", "supports_remote_execution": False},
    {"name": "Access Point", "icon": "pi-wifi", "supports_remote_execution": True},
    {"name": "Load Balancer", "icon": "pi-arrows-h", "supports_remote_execution": True},
    {"name": "Workstation", "icon": "pi-desktop", "supports_remote_execution": True},
]

LOCATIONS = [
    {"site": "Paris DC1", "building": "Building A", "room": "Server Room 1"},
    {"site": "Paris DC1", "building": "Building A", "room": "Server Room 2"},
    {"site": "Lyon Office", "building": "Main Building", "room": "IT Room"},
    {"site": "Marseille DC2", "building": "Data Hall", "room": "Hall A"},
    {"site": "Toulouse Branch", "building": "Office Tower", "room": "Floor 3"},
    {"site": "Bordeaux Remote", "building": None, "room": "Network Closet"},
]

SUPPLIERS = [
    {"name": "TechDistrib", "contact_email": "contact@techdistrib.fr", "phone": "+33 1 23 45 67 89"},
    {"name": "NetPro Solutions", "contact_email": "sales@netpro.fr", "phone": "+33 1 98 76 54 32"},
    {"name": "CloudParts", "contact_email": "order@cloudparts.eu", "phone": "+33 4 56 78 90 12"},
    {"name": "DataCenter Supply", "contact_email": "info@dcsupply.com", "phone": "+33 5 67 89 01 23"},
    {"name": "IT Hardware Pro", "contact_email": "commercial@ithwpro.fr", "phone": "+33 6 78 90 12 34"},
]

SOFTWARE_CATALOG = [
    {"name": "Microsoft Windows Server 2022", "publisher": "Microsoft", "category": "Operating System", "version": "2022"},
    {"name": "VMware vSphere", "publisher": "VMware", "category": "Virtualization", "version": "8.0"},
    {"name": "Microsoft SQL Server", "publisher": "Microsoft", "category": "Database", "version": "2022"},
    {"name": "Red Hat Enterprise Linux", "publisher": "Red Hat", "category": "Operating System", "version": "9"},
    {"name": "Veeam Backup", "publisher": "Veeam", "category": "Backup", "version": "12"},
    {"name": "Zabbix", "publisher": "Zabbix", "category": "Monitoring", "version": "6.4"},
    {"name": "Ansible Tower", "publisher": "Red Hat", "category": "Automation", "version": "4.0"},
    {"name": "Docker Enterprise", "publisher": "Docker", "category": "Containerization", "version": "24.0"},
    {"name": "Kubernetes", "publisher": "CNCF", "category": "Orchestration", "version": "1.28"},
    {"name": "PostgreSQL", "publisher": "PostgreSQL", "category": "Database", "version": "16"},
]

SUBNETS = [
    {"cidr": "10.0.0.0/24", "name": "Management Network", "description": "Management and administration (VLAN 10)"},
    {"cidr": "10.0.1.0/24", "name": "Production Servers", "description": "Production server network (VLAN 20)"},
    {"cidr": "10.0.2.0/24", "name": "Development", "description": "Development environment (VLAN 30)"},
    {"cidr": "10.0.3.0/24", "name": "DMZ", "description": "Demilitarized zone (VLAN 40)"},
    {"cidr": "192.168.1.0/24", "name": "Office WiFi", "description": "Office wireless network (VLAN 100)"},
    {"cidr": "192.168.10.0/24", "name": "Guest Network", "description": "Guest access network (VLAN 200)"},
    {"cidr": "172.16.0.0/24", "name": "Storage Network", "description": "iSCSI and NFS traffic (VLAN 50)"},
    {"cidr": "172.16.1.0/24", "name": "Backup Network", "description": "Backup traffic (VLAN 60)"},
]

TICKET_TEMPLATES = [
    {"name": "New Employee Onboarding", "title_template": "Onboarding: {user}", "description_template": "Setup workstation, accounts, and access for new employee.\n\n- Create AD account\n- Setup email\n- Provision workstation\n- Grant access to required systems", "ticket_type": "request", "priority": "medium", "category": "Onboarding"},
    {"name": "Password Reset", "title_template": "Password Reset Request", "description_template": "User requires password reset for their account.", "ticket_type": "request", "priority": "low", "category": "Access"},
    {"name": "Hardware Failure", "title_template": "Hardware Failure: {equipment}", "description_template": "Equipment has failed and requires replacement or repair.", "ticket_type": "incident", "priority": "high", "category": "Hardware"},
    {"name": "Network Connectivity Issue", "title_template": "Network Issue: {location}", "description_template": "User experiencing network connectivity problems.", "ticket_type": "incident", "priority": "high", "category": "Network"},
    {"name": "Software Installation Request", "title_template": "Software Install: {software}", "description_template": "Request to install software on user workstation.", "ticket_type": "request", "priority": "low", "category": "Software"},
]

KB_ARTICLES = [
    {"title": "How to Reset Your Password", "slug": "reset-password", "category": "Security", "summary": "Step-by-step guide to reset your domain password", "content": "# Password Reset Guide\n\n## Self-Service Portal\n1. Go to https://password.company.local\n2. Enter your username\n3. Answer security questions\n4. Create new password\n\n## Requirements\n- Minimum 12 characters\n- At least one uppercase\n- At least one number\n- At least one special character"},
    {"title": "VPN Connection Setup", "slug": "vpn-setup", "category": "Network", "summary": "Configure VPN client for remote access", "content": "# VPN Setup Guide\n\n## Windows\n1. Download FortiClient from IT portal\n2. Install with default options\n3. Add new VPN connection:\n   - Name: Company VPN\n   - Server: vpn.company.com\n   - Port: 443\n\n## macOS\nSame steps, download macOS version."},
    {"title": "Email Signature Standard", "slug": "email-signature", "category": "Communication", "summary": "Company email signature format and guidelines", "content": "# Email Signature Guidelines\n\n```\nFirst Last\nJob Title\nCompany Name\nPhone: +33 1 XX XX XX XX\nEmail: first.last@company.com\n```"},
    {"title": "Backup Recovery Procedure", "slug": "backup-recovery", "category": "IT Operations", "summary": "How to request and perform data recovery", "content": "# Backup Recovery\n\n## Request Process\n1. Open a ticket with category 'Backup'\n2. Specify:\n   - File/folder path\n   - Approximate date of deletion\n   - Priority level\n\n## SLA\n- Critical: 4 hours\n- Normal: 24 hours"},
    {"title": "New Equipment Request", "slug": "equipment-request", "category": "Procurement", "summary": "Process to request new IT equipment", "content": "# Equipment Request Process\n\n1. Fill out equipment request form\n2. Get manager approval\n3. Submit to IT procurement\n4. Wait for budget approval\n5. Equipment ordered and delivered\n\nTypical timeline: 2-4 weeks"},
]


# =============================================================================
# Helper Functions
# =============================================================================

def random_string(length: int = 8) -> str:
    """Generate random alphanumeric string."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


def random_mac() -> str:
    """Generate random MAC address."""
    return ':'.join([f'{random.randint(0, 255):02x}' for _ in range(6)])


def random_serial() -> str:
    """Generate random serial number."""
    return f"SN-{random_string(4).upper()}-{random_string(6).upper()}"


_asset_counter = 0
def random_asset_tag() -> str:
    """Generate unique asset tag."""
    global _asset_counter
    _asset_counter += 1
    return f"ASSET-{_asset_counter:06d}"


def random_ip(subnet_base: str) -> str:
    """Generate random IP in subnet."""
    base = subnet_base.rsplit('.', 1)[0]
    return f"{base}.{random.randint(10, 250)}"


def random_date_future(days_min: int = 30, days_max: int = 365) -> date:
    """Generate random future date."""
    delta = random.randint(days_min, days_max)
    return date.today() + timedelta(days=delta)


def random_date_past(days_min: int = 30, days_max: int = 730) -> date:
    """Generate random past date."""
    delta = random.randint(days_min, days_max)
    return date.today() - timedelta(days=delta)


def random_datetime_past(days_max: int = 30) -> datetime:
    """Generate random past datetime."""
    delta = random.randint(1, days_max * 24 * 60)
    return datetime.now(timezone.utc) - timedelta(minutes=delta)


# =============================================================================
# Seeder Functions
# =============================================================================

def seed_users(db: Session, count: int) -> list:
    """Create test users."""
    print("  Creating users...")
    users = []

    for user_data in TEST_USERS[:count]:
        existing = db.query(models.User).filter(models.User.username == user_data["username"]).first()
        if existing:
            users.append(existing)
            continue

        user = models.User(
            username=user_data["username"],
            email=user_data["email"],
            hashed_password=get_password_hash("Test123!@#"),
            role=user_data["role"],
            permissions=user_data["permissions"],
            is_active=True
        )
        db.add(user)
        users.append(user)

    db.commit()
    print(f"    Created {len(users)} users")
    return users


def seed_entities(db: Session, count: int) -> list:
    """Create test entities for multi-tenant."""
    print("  Creating entities...")
    entities = []

    entity_names = ["Headquarters", "Branch Paris", "Branch Lyon", "Remote Office", "Partner Site"]

    for name in entity_names[:count]:
        existing = db.query(models.Entity).filter(models.Entity.name == name).first()
        if existing:
            entities.append(existing)
            continue

        entity = models.Entity(
            name=name,
            description=f"Entity for {name}",
            is_active=True
        )
        db.add(entity)
        entities.append(entity)

    db.commit()
    print(f"    Created {len(entities)} entities")
    return entities


def seed_manufacturers(db: Session, count: int) -> list:
    """Create manufacturers."""
    print("  Creating manufacturers...")
    manufacturers = []

    for mfr_data in MANUFACTURERS[:count]:
        existing = db.query(models.Manufacturer).filter(models.Manufacturer.name == mfr_data["name"]).first()
        if existing:
            manufacturers.append(existing)
            continue

        mfr = models.Manufacturer(
            name=mfr_data["name"],
            website=mfr_data["website"]
        )
        db.add(mfr)
        manufacturers.append(mfr)

    db.commit()
    print(f"    Created {len(manufacturers)} manufacturers")
    return manufacturers


def seed_equipment_types(db: Session, count: int) -> list:
    """Create equipment types."""
    print("  Creating equipment types...")
    types = []

    for type_data in EQUIPMENT_TYPES[:count]:
        existing = db.query(models.EquipmentType).filter(models.EquipmentType.name == type_data["name"]).first()
        if existing:
            types.append(existing)
            continue

        eq_type = models.EquipmentType(
            name=type_data["name"],
            icon=type_data.get("icon", "pi-box"),
            supports_remote_execution=type_data.get("supports_remote_execution", False)
        )
        db.add(eq_type)
        types.append(eq_type)

    db.commit()
    print(f"    Created {len(types)} equipment types")
    return types


def seed_locations(db: Session, count: int) -> list:
    """Create locations."""
    print("  Creating locations...")
    locations = []

    for loc_data in LOCATIONS[:count]:
        existing = db.query(models.Location).filter(
            models.Location.site == loc_data["site"],
            models.Location.room == loc_data["room"]
        ).first()
        if existing:
            locations.append(existing)
            continue

        location = models.Location(
            site=loc_data["site"],
            building=loc_data.get("building"),
            room=loc_data.get("room")
        )
        db.add(location)
        locations.append(location)

    db.commit()
    print(f"    Created {len(locations)} locations")
    return locations


def seed_suppliers(db: Session, count: int) -> list:
    """Create suppliers."""
    print("  Creating suppliers...")
    suppliers = []

    for sup_data in SUPPLIERS[:count]:
        existing = db.query(models.Supplier).filter(models.Supplier.name == sup_data["name"]).first()
        if existing:
            suppliers.append(existing)
            continue

        supplier = models.Supplier(
            name=sup_data["name"],
            contact_email=sup_data["contact_email"],
            phone=sup_data["phone"]
        )
        db.add(supplier)
        suppliers.append(supplier)

    db.commit()
    print(f"    Created {len(suppliers)} suppliers")
    return suppliers


def seed_equipment_models(db: Session, manufacturers: list, equipment_types: list, count: int) -> list:
    """Create equipment models."""
    print("  Creating equipment models...")
    models_list = []

    model_names = [
        "ProLiant DL380 Gen10", "PowerEdge R750", "Catalyst 9300", "EX4300",
        "FortiGate 600E", "NetApp AFF A400", "Smart-UPS 3000", "PA-5260",
        "ThinkSystem SR650", "Unity XT 480"
    ]

    for i, name in enumerate(model_names[:count]):
        existing = db.query(models.EquipmentModel).filter(models.EquipmentModel.name == name).first()
        if existing:
            models_list.append(existing)
            continue

        model = models.EquipmentModel(
            name=name,
            manufacturer_id=random.choice(manufacturers).id,
            equipment_type_id=random.choice(equipment_types).id,
            specs={"height_u": random.choice([1, 2, 4]), "power_watts": random.randint(200, 1500)}
        )
        db.add(model)
        models_list.append(model)

    db.commit()
    print(f"    Created {len(models_list)} equipment models")
    return models_list


def seed_racks(db: Session, locations: list, count: int) -> list:
    """Create racks."""
    print("  Creating racks...")
    racks = []

    for i in range(count):
        name = f"RACK-{chr(65 + i // 10)}{i % 10 + 1:02d}"
        existing = db.query(models.Rack).filter(models.Rack.name == name).first()
        if existing:
            racks.append(existing)
            continue

        rack = models.Rack(
            name=name,
            location_id=random.choice(locations).id,
            height_u=random.choice([42, 45, 48]),
            width_mm=600,
            depth_mm=random.choice([1000, 1200]),
            max_power_kw=random.uniform(5.0, 20.0)
        )
        db.add(rack)
        racks.append(rack)

    db.commit()
    print(f"    Created {len(racks)} racks")
    return racks


def seed_equipment(db: Session, equipment_models: list, locations: list,
                   suppliers: list, racks: list, entities: list, count: int) -> list:
    """Create equipment."""
    print("  Creating equipment...")
    equipment_list = []
    statuses = ["in_service", "in_service", "in_service", "in_stock", "maintenance", "retired"]

    for i in range(count):
        model = random.choice(equipment_models)
        rack = random.choice(racks) if random.random() > 0.3 else None

        # Calculate position in rack
        position_u = None
        height_u = model.specs.get("height_u", 2) if model.specs else 2
        if rack:
            position_u = random.randint(1, 42 - height_u)

        equipment = models.Equipment(
            name=f"{model.name}-{random_string(4).upper()}",
            model_id=model.id,
            serial_number=random_serial(),
            asset_tag=random_asset_tag(),
            status=random.choice(statuses),
            location_id=random.choice(locations).id,
            supplier_id=random.choice(suppliers).id if random.random() > 0.3 else None,
            entity_id=random.choice(entities).id if entities else None,
            rack_id=rack.id if rack else None,
            position_u=position_u,
            height_u=height_u,
            purchase_date=random_date_past(30, 1095),
            warranty_expiry=datetime.now(timezone.utc) + timedelta(days=random.randint(-30, 730)),
            notes=f"Test equipment #{i+1}"
        )
        db.add(equipment)
        equipment_list.append(equipment)

    db.commit()
    print(f"    Created {len(equipment_list)} equipment")
    return equipment_list


def seed_subnets(db: Session, count: int) -> list:
    """Create subnets."""
    print("  Creating subnets...")
    subnets = []

    for subnet_data in SUBNETS[:count]:
        existing = db.query(models.Subnet).filter(models.Subnet.cidr == subnet_data["cidr"]).first()
        if existing:
            subnets.append(existing)
            continue

        subnet = models.Subnet(
            cidr=subnet_data["cidr"],
            name=subnet_data["name"],
            description=subnet_data["description"]
        )
        db.add(subnet)
        subnets.append(subnet)

    db.commit()
    print(f"    Created {len(subnets)} subnets")
    return subnets


def seed_ip_addresses(db: Session, subnets: list, equipment_list: list, count_per_subnet: int) -> list:
    """Create IP addresses."""
    print("  Creating IP addresses...")
    ip_addresses = []
    statuses = ["active", "active", "active", "reserved", "available"]

    for subnet in subnets:
        base = subnet.cidr.rsplit('.', 1)[0]
        for i in range(count_per_subnet):
            ip_addr = f"{base}.{10 + i}"

            existing = db.query(models.IPAddress).filter(models.IPAddress.address == ip_addr).first()
            if existing:
                ip_addresses.append(existing)
                continue

            ip = models.IPAddress(
                address=ip_addr,
                subnet_id=subnet.id,
                status=random.choice(statuses),
                hostname=f"host-{random_string(6)}.local" if random.random() > 0.3 else None,
                mac_address=random_mac() if random.random() > 0.5 else None,
                equipment_id=random.choice(equipment_list).id if equipment_list and random.random() > 0.7 else None,
                last_scanned_at=random_datetime_past(7) if random.random() > 0.5 else None
            )
            db.add(ip)
            ip_addresses.append(ip)

    db.commit()
    print(f"    Created {len(ip_addresses)} IP addresses")
    return ip_addresses


def seed_network_ports(db: Session, equipment_list: list, count: int) -> list:
    """Create network ports."""
    print("  Creating network ports...")
    ports = []
    port_types = ["ethernet", "sfp", "sfp+", "qsfp", "console"]
    speeds = ["1G", "10G", "25G", "40G", "100G"]

    for equipment in equipment_list[:count]:
        num_ports = random.randint(2, 8)
        for i in range(num_ports):
            port = models.NetworkPort(
                equipment_id=equipment.id,
                name=f"eth{i}",
                port_type=random.choice(port_types),
                speed=random.choice(speeds),
                mac_address=random_mac()
            )
            db.add(port)
            ports.append(port)

    db.commit()

    # Create some connections between ports
    print("  Creating port connections...")
    available_ports = [p for p in ports if p.connected_to_id is None]
    random.shuffle(available_ports)

    connections = 0
    for i in range(0, len(available_ports) - 1, 2):
        if connections >= count // 2:
            break
        port_a = available_ports[i]
        port_b = available_ports[i + 1]
        if port_a.equipment_id != port_b.equipment_id:
            port_a.connected_to_id = port_b.id
            port_b.connected_to_id = port_a.id
            connections += 1

    db.commit()
    print(f"    Created {len(ports)} network ports with {connections} connections")
    return ports


def seed_contracts(db: Session, suppliers: list, equipment_list: list, count: int) -> list:
    """Create contracts."""
    print("  Creating contracts...")
    contracts = []
    contract_types = ["maintenance", "support", "insurance", "leasing", "service"]

    for i in range(count):
        start_date = random_date_past(365, 730)
        end_date = start_date + timedelta(days=random.randint(365, 1095))

        contract = models.Contract(
            name=f"Contract-{random_string(6).upper()}",
            contract_type=random.choice(contract_types),
            contract_number=f"CTR-{random_string(8).upper()}",
            supplier_id=random.choice(suppliers).id,
            start_date=start_date,
            end_date=end_date,
            annual_cost=random.randint(1000, 50000),
            notes=f"Test contract #{i+1}",
            renewal_type=random.choice(["auto", "manual", "none"])
        )
        db.add(contract)
        contracts.append(contract)

    db.commit()

    # Link equipment to contracts
    for contract in contracts:
        num_equipment = random.randint(1, 5)
        selected_equipment = random.sample(equipment_list, min(num_equipment, len(equipment_list)))
        for eq in selected_equipment:
            link = models.ContractEquipment(
                contract_id=contract.id,
                equipment_id=eq.id
            )
            db.add(link)

    db.commit()
    print(f"    Created {len(contracts)} contracts")
    return contracts


def seed_software(db: Session, count: int) -> list:
    """Create software catalog."""
    print("  Creating software...")
    software_list = []

    for sw_data in SOFTWARE_CATALOG[:count]:
        existing = db.query(models.Software).filter(models.Software.name == sw_data["name"]).first()
        if existing:
            software_list.append(existing)
            continue

        software = models.Software(
            name=sw_data["name"],
            publisher=sw_data["publisher"],
            category=sw_data["category"],
            version=sw_data["version"]
        )
        db.add(software)
        software_list.append(software)

    db.commit()
    print(f"    Created {len(software_list)} software")
    return software_list


def seed_licenses(db: Session, software_list: list, count: int) -> list:
    """Create software licenses."""
    print("  Creating licenses...")
    licenses = []
    license_types = ["perpetual", "subscription", "volume", "oem"]

    for software in software_list[:count]:
        num_licenses = random.randint(1, 3)
        for i in range(num_licenses):
            license = models.SoftwareLicense(
                software_id=software.id,
                license_key=f"XXXX-{random_string(4).upper()}-{random_string(4).upper()}-{random_string(4).upper()}",
                license_type=random.choice(license_types),
                quantity=random.choice([1, 5, 10, 25, 50, 100]),
                purchase_date=random_date_past(365, 730),
                expiry_date=random_date_future(30, 730) if random.random() > 0.3 else None,
                purchase_price=random.randint(100, 10000)
            )
            db.add(license)
            licenses.append(license)

    db.commit()
    print(f"    Created {len(licenses)} licenses")
    return licenses


def seed_software_installations(db: Session, software_list: list, equipment_list: list, count: int) -> list:
    """Create software installations."""
    print("  Creating installations...")
    installations = []

    # Track created pairs to avoid duplicates in memory
    created_pairs = set()

    # Get existing pairs from database
    existing_installations = db.query(
        models.SoftwareInstallation.software_id,
        models.SoftwareInstallation.equipment_id
    ).all()
    for sw_id, eq_id in existing_installations:
        created_pairs.add((sw_id, eq_id))

    attempts = 0
    max_attempts = count * 3

    while len(installations) < count and attempts < max_attempts:
        attempts += 1
        software = random.choice(software_list)
        equipment = random.choice(equipment_list)
        pair = (software.id, equipment.id)

        if pair in created_pairs:
            continue

        created_pairs.add(pair)

        installation = models.SoftwareInstallation(
            software_id=software.id,
            equipment_id=equipment.id,
            installed_version=software.version,
            installation_date=random_datetime_past(180),
            discovered_at=random_datetime_past(30)
        )
        db.add(installation)
        installations.append(installation)

    db.commit()
    print(f"    Created {len(installations)} installations")
    return installations


def seed_tickets(db: Session, users: list, entities: list, equipment_list: list, count: int) -> list:
    """Create tickets."""
    print("  Creating tickets...")
    tickets = []
    statuses = ["new", "open", "open", "pending", "resolved", "closed"]
    priorities = ["low", "medium", "medium", "high", "critical"]
    types = ["incident", "request", "problem", "change"]
    categories = ["Hardware", "Software", "Network", "Security", "Access", "Other"]

    for i in range(count):
        created_by = random.choice(users)
        assigned_to = random.choice(users) if random.random() > 0.3 else None
        status = random.choice(statuses)

        created_at = random_datetime_past(60)

        ticket = models.Ticket(
            title=f"Test Ticket #{i+1} - {random.choice(categories)} Issue",
            description=f"This is a test ticket for testing purposes.\n\nDetails:\n- Created by seed script\n- Random category: {random.choice(categories)}",
            ticket_type=random.choice(types),
            status=status,
            priority=random.choice(priorities),
            category=random.choice(categories),
            requester_id=created_by.id,
            assigned_to_id=assigned_to.id if assigned_to else None,
            entity_id=random.choice(entities).id if entities else None,
            equipment_id=random.choice(equipment_list).id if equipment_list and random.random() > 0.7 else None,
            created_at=created_at,
            updated_at=created_at + timedelta(hours=random.randint(1, 72)),
            sla_due_date=created_at + timedelta(hours=random.choice([4, 8, 24, 72]))
        )

        if status in ["resolved", "closed"]:
            ticket.resolved_at = created_at + timedelta(hours=random.randint(1, 48))
            ticket.resolution = "Issue resolved by test script."

        if status == "closed":
            ticket.closed_at = ticket.resolved_at + timedelta(hours=random.randint(1, 24))

        db.add(ticket)
        # Flush each ticket individually to trigger the before_insert hook
        db.flush()
        tickets.append(ticket)

    db.commit()

    # Add comments to some tickets
    print("  Creating ticket comments...")
    for ticket in tickets[:count // 2]:
        num_comments = random.randint(1, 5)
        for j in range(num_comments):
            comment = models.TicketComment(
                ticket_id=ticket.id,
                user_id=random.choice(users).id,
                content=f"Comment #{j+1} on ticket. This is a test comment.",
                is_internal=random.random() > 0.7,
                created_at=ticket.created_at + timedelta(hours=random.randint(1, 48))
            )
            db.add(comment)

    db.commit()
    print(f"    Created {len(tickets)} tickets with comments")
    return tickets


def seed_ticket_templates(db: Session) -> list:
    """Create ticket templates."""
    print("  Creating ticket templates...")
    templates = []

    for tmpl_data in TICKET_TEMPLATES:
        existing = db.query(models.TicketTemplate).filter(models.TicketTemplate.name == tmpl_data["name"]).first()
        if existing:
            templates.append(existing)
            continue

        template = models.TicketTemplate(
            name=tmpl_data["name"],
            title_template=tmpl_data["title_template"],
            description_template=tmpl_data["description_template"],
            ticket_type=tmpl_data["ticket_type"],
            priority=tmpl_data["priority"],
            category=tmpl_data["category"],
            is_active=True
        )
        db.add(template)
        templates.append(template)

    db.commit()
    print(f"    Created {len(templates)} ticket templates")
    return templates


def seed_knowledge_articles(db: Session, users: list) -> list:
    """Create knowledge base articles."""
    print("  Creating knowledge articles...")
    articles = []

    for article_data in KB_ARTICLES:
        existing = db.query(models.KnowledgeArticle).filter(models.KnowledgeArticle.slug == article_data["slug"]).first()
        if existing:
            articles.append(existing)
            continue

        author = random.choice(users)

        article = models.KnowledgeArticle(
            title=article_data["title"],
            slug=article_data["slug"],
            category=article_data["category"],
            summary=article_data["summary"],
            content=article_data["content"],
            author_id=author.id,
            is_published=True,
            is_internal=random.random() > 0.7,
            view_count=random.randint(0, 500),
            helpful_count=random.randint(0, 50),
            not_helpful_count=random.randint(0, 10),
            version=1,
            created_at=random_datetime_past(180),
            published_at=random_datetime_past(170)
        )
        db.add(article)
        articles.append(article)

    db.commit()
    print(f"    Created {len(articles)} knowledge articles")
    return articles


def seed_notifications(db: Session, users: list, count: int) -> list:
    """Create notifications."""
    print("  Creating notifications...")
    notifications = []
    types = ["info", "success", "warning", "error", "ticket"]

    for user in users:
        num_notifs = random.randint(2, count // len(users) + 1)
        for i in range(num_notifs):
            notif = models.Notification(
                user_id=user.id,
                notification_type=random.choice(types),
                title=f"Notification #{i+1}",
                message=f"This is a test notification for {user.username}.",
                is_read=random.random() > 0.5,
                created_at=random_datetime_past(14)
            )
            db.add(notif)
            notifications.append(notif)

    db.commit()
    print(f"    Created {len(notifications)} notifications")
    return notifications


def seed_pdus(db: Session, racks: list, count: int) -> list:
    """Create PDUs."""
    print("  Creating PDUs...")
    pdus = []
    pdu_types = ["basic", "metered", "switched", "smart"]

    for i, rack in enumerate(racks[:count]):
        pdu = models.PDU(
            name=f"PDU-{rack.name}-A",
            rack_id=rack.id,
            pdu_type=random.choice(pdu_types),
            total_ports=random.choice([8, 16, 24]),
            max_amps=32,
            voltage=230,
            phase="single"
        )
        db.add(pdu)
        pdus.append(pdu)

        if random.random() > 0.5:
            pdu_b = models.PDU(
                name=f"PDU-{rack.name}-B",
                rack_id=rack.id,
                pdu_type=random.choice(pdu_types),
                total_ports=random.choice([8, 16, 24]),
                max_amps=32,
                voltage=230,
                phase="single"
            )
            db.add(pdu_b)
            pdus.append(pdu_b)

    db.commit()
    print(f"    Created {len(pdus)} PDUs")
    return pdus


def seed_sla_policies(db: Session) -> list:
    """Create SLA policies."""
    print("  Creating SLA policies...")
    policies = []

    sla_data = [
        {
            "name": "Standard SLA",
            "description": "Standard SLA for all ticket types",
            "critical_response_time": 15,
            "critical_resolution_time": 240,
            "high_response_time": 60,
            "high_resolution_time": 480,
            "medium_response_time": 240,
            "medium_resolution_time": 1440,
            "low_response_time": 480,
            "low_resolution_time": 2880,
        },
        {
            "name": "Premium SLA",
            "description": "Premium SLA with faster response times",
            "critical_response_time": 5,
            "critical_resolution_time": 120,
            "high_response_time": 30,
            "high_resolution_time": 240,
            "medium_response_time": 120,
            "medium_resolution_time": 720,
            "low_response_time": 240,
            "low_resolution_time": 1440,
        },
    ]

    for policy_data in sla_data:
        existing = db.query(models.SLAPolicy).filter(models.SLAPolicy.name == policy_data["name"]).first()
        if existing:
            policies.append(existing)
            continue

        policy = models.SLAPolicy(
            name=policy_data["name"],
            description=policy_data["description"],
            critical_response_time=policy_data["critical_response_time"],
            critical_resolution_time=policy_data["critical_resolution_time"],
            high_response_time=policy_data["high_response_time"],
            high_resolution_time=policy_data["high_resolution_time"],
            medium_response_time=policy_data["medium_response_time"],
            medium_resolution_time=policy_data["medium_resolution_time"],
            low_response_time=policy_data["low_response_time"],
            low_resolution_time=policy_data["low_resolution_time"],
            business_hours_only=True,
            business_start="09:00",
            business_end="18:00",
            business_days=[1, 2, 3, 4, 5]
        )
        db.add(policy)
        policies.append(policy)

    db.commit()
    print(f"    Created {len(policies)} SLA policies")
    return policies


def clean_test_data(db: Session):
    """Remove test data (keeps admin user)."""
    print("Cleaning existing test data...")

    # Delete in reverse order of dependencies
    tables = [
        models.TicketComment,
        models.TicketHistory,
        models.TicketAttachment,
        models.Ticket,
        models.TicketTemplate,
        models.Notification,
        models.KnowledgeArticle,
        models.SoftwareInstallation,
        models.SoftwareLicense,
        models.Software,
        models.ContractEquipment,
        models.Contract,
        models.NetworkPort,
        models.IPAddress,
        models.Subnet,
        models.PDU,
        models.Equipment,
        models.Rack,
        models.EquipmentModel,
        models.EquipmentType,
        models.Manufacturer,
        models.Supplier,
        models.Location,
        models.Entity,
        models.SLAPolicy,
    ]

    for table in tables:
        try:
            deleted = db.query(table).delete()
            print(f"  Deleted {deleted} records from {table.__tablename__}")
        except Exception as e:
            print(f"  Warning: Could not clean {table.__tablename__}: {e}")
            db.rollback()

    # Delete test users (keep admin)
    deleted_users = db.query(models.User).filter(
        models.User.username.in_([u["username"] for u in TEST_USERS])
    ).delete(synchronize_session=False)
    print(f"  Deleted {deleted_users} test users")

    db.commit()
    print("Cleanup complete!\n")


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Seed test data for Inframate")
    parser.add_argument("--clean", action="store_true", help="Remove existing test data first")
    parser.add_argument("--minimal", action="store_true", help="Generate minimal data set")
    args = parser.parse_args()

    count = MINIMAL_COUNT if args.minimal else NORMAL_COUNT

    print("=" * 60)
    print("Inframate Test Data Seeder")
    print("=" * 60)
    print(f"Mode: {'Minimal' if args.minimal else 'Normal'} ({count} items per category)")
    print()

    db = SessionLocal()

    try:
        if args.clean:
            clean_test_data(db)

        print("Seeding test data...")
        print()

        # Core data
        users = seed_users(db, len(TEST_USERS))
        entities = seed_entities(db, count)

        # Infrastructure
        manufacturers = seed_manufacturers(db, count)
        equipment_types = seed_equipment_types(db, count)
        locations = seed_locations(db, count)
        suppliers = seed_suppliers(db, count)

        # Equipment & DCIM
        equipment_models = seed_equipment_models(db, manufacturers, equipment_types, count)
        racks = seed_racks(db, locations, count)
        equipment = seed_equipment(db, equipment_models, locations, suppliers, racks, entities, count * 3)
        pdus = seed_pdus(db, racks, count)

        # Network
        subnets = seed_subnets(db, count)
        ip_addresses = seed_ip_addresses(db, subnets, equipment, count)
        network_ports = seed_network_ports(db, equipment, count)

        # Contracts & Software
        contracts = seed_contracts(db, suppliers, equipment, count)
        software = seed_software(db, count)
        licenses = seed_licenses(db, software, count)
        installations = seed_software_installations(db, software, equipment, count * 2)

        # Helpdesk
        sla_policies = seed_sla_policies(db)
        ticket_templates = seed_ticket_templates(db)
        tickets = seed_tickets(db, users, entities, equipment, count * 2)

        # Knowledge & Notifications
        articles = seed_knowledge_articles(db, users)
        notifications = seed_notifications(db, users, count * 2)

        print()
        print("=" * 60)
        print("Test data seeding complete!")
        print("=" * 60)
        print()
        print("Test users created (password: Test123!@#):")
        for user_data in TEST_USERS:
            print(f"  - {user_data['username']} ({user_data['role']})")
        print()

    except Exception as e:
        print(f"\nError: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
