#!/usr/bin/env python3
"""
Inframate Realistic Infrastructure Seeder
Generates a coherent datacenter infrastructure with proper network topology.

This simulates a real company "TechCorp" with:
- 2 Datacenters (Paris DC1 - Primary, Lyon DC2 - DR)
- Full network topology with core/distribution/access layers
- Proper IPAM with VLANs
- Equipment properly connected via network ports
- Realistic contracts, software, and helpdesk data

Usage:
    python test/seed_realistic_data.py [--clean] [--minimal]

Options:
    --clean     Remove existing test data before seeding
    --minimal   Generate minimal data set (single DC)
"""

import os
import sys
import random
import string
import argparse
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment variables before imports
os.environ.setdefault("DATABASE_URL", "postgresql://inframate:inframatepassword@localhost:5432/inframate")

from sqlalchemy.orm import Session
from backend.core.database import SessionLocal, engine
from backend.core.security import get_password_hash
from backend import models


# =============================================================================
# Company: TechCorp - A realistic IT infrastructure
# =============================================================================

COMPANY_NAME = "TechCorp"

# =============================================================================
# Users - IT Department Structure
# =============================================================================

IT_TEAM = [
    {"username": "j.martin", "email": "j.martin@techcorp.local", "role": "superadmin", "permissions": [], "full_name": "Jean Martin (CTO)"},
    {"username": "m.dupont", "email": "m.dupont@techcorp.local", "role": "admin", "permissions": [], "full_name": "Marie Dupont (IT Manager)"},
    {"username": "p.bernard", "email": "p.bernard@techcorp.local", "role": "tech", "permissions": ["ipam", "inventory", "dcim", "topology", "network_ports", "contracts", "software"], "full_name": "Pierre Bernard (Infra Lead)"},
    {"username": "s.leroy", "email": "s.leroy@techcorp.local", "role": "tech", "permissions": ["ipam", "topology", "network_ports"], "full_name": "Sophie Leroy (Network Engineer)"},
    {"username": "a.moreau", "email": "a.moreau@techcorp.local", "role": "tech", "permissions": ["inventory", "dcim", "contracts"], "full_name": "Antoine Moreau (System Admin)"},
    {"username": "l.garcia", "email": "l.garcia@techcorp.local", "role": "tech", "permissions": ["software", "inventory"], "full_name": "Lucia Garcia (Software Admin)"},
    {"username": "t.robert", "email": "t.robert@techcorp.local", "role": "user", "permissions": [], "full_name": "Thomas Robert (Helpdesk L1)"},
    {"username": "e.petit", "email": "e.petit@techcorp.local", "role": "user", "permissions": [], "full_name": "Emma Petit (Helpdesk L1)"},
]

# =============================================================================
# Entities (Business Units)
# =============================================================================

ENTITIES = [
    {"name": "TechCorp HQ", "description": "Headquarters - Paris"},
    {"name": "TechCorp R&D", "description": "Research & Development"},
    {"name": "TechCorp Sales", "description": "Sales & Marketing"},
    {"name": "TechCorp Ops", "description": "Operations"},
]

# =============================================================================
# Locations - Datacenter & Offices
# =============================================================================

LOCATIONS = {
    "paris_dc1": [
        {"site": "Paris DC1", "building": "Data Hall A", "room": "Server Room A1", "description": "Primary datacenter - Core infrastructure"},
        {"site": "Paris DC1", "building": "Data Hall A", "room": "Server Room A2", "description": "Primary datacenter - Production servers"},
        {"site": "Paris DC1", "building": "Data Hall B", "room": "Network Room B1", "description": "Primary datacenter - Network core"},
    ],
    "lyon_dc2": [
        {"site": "Lyon DC2", "building": "Main Hall", "room": "DR Room 1", "description": "DR site - Disaster recovery"},
        {"site": "Lyon DC2", "building": "Main Hall", "room": "DR Room 2", "description": "DR site - Backup systems"},
    ],
    "offices": [
        {"site": "Paris HQ", "building": "Tour Montparnasse", "room": "Floor 15 - IT", "description": "Headquarters IT room"},
        {"site": "Lyon Office", "building": "Part-Dieu Tower", "room": "Floor 8 - Comms", "description": "Lyon branch network closet"},
        {"site": "Marseille Office", "building": "Euromediterranee", "room": "IT Closet", "description": "Marseille branch"},
    ],
}

# =============================================================================
# Manufacturers & Suppliers
# =============================================================================

MANUFACTURERS = {
    "cisco": {"name": "Cisco Systems", "website": "https://cisco.com"},
    "hpe": {"name": "Hewlett Packard Enterprise", "website": "https://hpe.com"},
    "dell": {"name": "Dell Technologies", "website": "https://dell.com"},
    "juniper": {"name": "Juniper Networks", "website": "https://juniper.net"},
    "fortinet": {"name": "Fortinet", "website": "https://fortinet.com"},
    "netapp": {"name": "NetApp", "website": "https://netapp.com"},
    "apc": {"name": "APC by Schneider Electric", "website": "https://apc.com"},
    "vmware": {"name": "VMware", "website": "https://vmware.com"},
    "aruba": {"name": "Aruba Networks", "website": "https://arubanetworks.com"},
    "paloalto": {"name": "Palo Alto Networks", "website": "https://paloaltonetworks.com"},
}

SUPPLIERS = [
    {"name": "Westcon-Comstor", "contact_email": "enterprise@westcon.fr", "phone": "+33 1 55 00 11 22", "description": "Primary network vendor"},
    {"name": "Ingram Micro", "contact_email": "sales@ingrammicro.fr", "phone": "+33 1 49 83 20 00", "description": "Server & storage vendor"},
    {"name": "TD Synnex", "contact_email": "contact@tdsynnex.fr", "phone": "+33 1 64 86 50 50", "description": "Multi-vendor distributor"},
    {"name": "Exclusive Networks", "contact_email": "info@exclusive-networks.fr", "phone": "+33 1 55 17 18 00", "description": "Security solutions"},
    {"name": "Arrow ECS", "contact_email": "france@arrow.com", "phone": "+33 1 49 97 60 00", "description": "Cloud & infrastructure"},
]

# =============================================================================
# Equipment Types & Models - Realistic Hierarchy
# =============================================================================

EQUIPMENT_TYPES = [
    {"name": "Core Router", "icon": "pi-share-alt", "supports_remote_execution": True, "hierarchy_level": 1},
    {"name": "Core Switch", "icon": "pi-sitemap", "supports_remote_execution": True, "hierarchy_level": 2},
    {"name": "Distribution Switch", "icon": "pi-sitemap", "supports_remote_execution": True, "hierarchy_level": 3},
    {"name": "Access Switch", "icon": "pi-sitemap", "supports_remote_execution": True, "hierarchy_level": 4},
    {"name": "Firewall", "icon": "pi-shield", "supports_remote_execution": True, "hierarchy_level": 2},
    {"name": "Load Balancer", "icon": "pi-arrows-h", "supports_remote_execution": True, "hierarchy_level": 3},
    {"name": "Server", "icon": "pi-server", "supports_remote_execution": True, "hierarchy_level": 5},
    {"name": "Storage Array", "icon": "pi-database", "supports_remote_execution": False, "hierarchy_level": 5},
    {"name": "Backup Appliance", "icon": "pi-save", "supports_remote_execution": False, "hierarchy_level": 5},
    {"name": "UPS", "icon": "pi-bolt", "supports_remote_execution": False, "hierarchy_level": 6},
    {"name": "PDU", "icon": "pi-bolt", "supports_remote_execution": False, "hierarchy_level": 6},
    {"name": "Wireless Controller", "icon": "pi-wifi", "supports_remote_execution": True, "hierarchy_level": 4},
    {"name": "Access Point", "icon": "pi-wifi", "supports_remote_execution": True, "hierarchy_level": 5},
]

# Equipment models with realistic specs
EQUIPMENT_MODELS = {
    # Core Routers
    "cisco_asr1001x": {"name": "Cisco ASR 1001-X", "manufacturer": "cisco", "type": "Core Router", "height_u": 1, "power_watts": 400, "ports": 6},
    "juniper_mx204": {"name": "Juniper MX204", "manufacturer": "juniper", "type": "Core Router", "height_u": 1, "power_watts": 450, "ports": 4},

    # Core Switches
    "cisco_nexus9336": {"name": "Cisco Nexus 9336C-FX2", "manufacturer": "cisco", "type": "Core Switch", "height_u": 1, "power_watts": 650, "ports": 36},
    "cisco_nexus93180": {"name": "Cisco Nexus 93180YC-FX", "manufacturer": "cisco", "type": "Core Switch", "height_u": 1, "power_watts": 550, "ports": 48},

    # Distribution Switches
    "cisco_catalyst9500": {"name": "Cisco Catalyst 9500-48Y4C", "manufacturer": "cisco", "type": "Distribution Switch", "height_u": 1, "power_watts": 750, "ports": 52},
    "aruba_8325": {"name": "Aruba 8325-48Y8C", "manufacturer": "aruba", "type": "Distribution Switch", "height_u": 1, "power_watts": 650, "ports": 56},

    # Access Switches
    "cisco_catalyst9300": {"name": "Cisco Catalyst 9300-48P", "manufacturer": "cisco", "type": "Access Switch", "height_u": 1, "power_watts": 850, "ports": 48},
    "aruba_6300": {"name": "Aruba 6300M 48G PoE+", "manufacturer": "aruba", "type": "Access Switch", "height_u": 1, "power_watts": 800, "ports": 48},

    # Firewalls
    "fortinet_fg600e": {"name": "FortiGate 600E", "manufacturer": "fortinet", "type": "Firewall", "height_u": 2, "power_watts": 350, "ports": 18},
    "paloalto_pa5250": {"name": "Palo Alto PA-5250", "manufacturer": "paloalto", "type": "Firewall", "height_u": 2, "power_watts": 500, "ports": 24},

    # Load Balancers
    "f5_i5800": {"name": "F5 BIG-IP i5800", "manufacturer": "hpe", "type": "Load Balancer", "height_u": 1, "power_watts": 400, "ports": 8},

    # Servers
    "hpe_dl380g10": {"name": "HPE ProLiant DL380 Gen10", "manufacturer": "hpe", "type": "Server", "height_u": 2, "power_watts": 800, "ports": 4},
    "dell_r750": {"name": "Dell PowerEdge R750", "manufacturer": "dell", "type": "Server", "height_u": 2, "power_watts": 750, "ports": 4},
    "hpe_dl360g10": {"name": "HPE ProLiant DL360 Gen10", "manufacturer": "hpe", "type": "Server", "height_u": 1, "power_watts": 500, "ports": 4},
    "dell_r650": {"name": "Dell PowerEdge R650", "manufacturer": "dell", "type": "Server", "height_u": 1, "power_watts": 500, "ports": 4},

    # Storage
    "netapp_aff400": {"name": "NetApp AFF A400", "manufacturer": "netapp", "type": "Storage Array", "height_u": 4, "power_watts": 1200, "ports": 8},
    "dell_unity500": {"name": "Dell EMC Unity XT 480", "manufacturer": "dell", "type": "Storage Array", "height_u": 3, "power_watts": 900, "ports": 8},

    # Backup
    "dell_dp4400": {"name": "Dell PowerProtect DP4400", "manufacturer": "dell", "type": "Backup Appliance", "height_u": 4, "power_watts": 1100, "ports": 4},

    # UPS
    "apc_srt10k": {"name": "APC Smart-UPS SRT 10kVA", "manufacturer": "apc", "type": "UPS", "height_u": 6, "power_watts": 0, "ports": 0},
    "apc_srt5k": {"name": "APC Smart-UPS SRT 5kVA", "manufacturer": "apc", "type": "UPS", "height_u": 3, "power_watts": 0, "ports": 0},

    # Wireless
    "cisco_wlc9800": {"name": "Cisco Catalyst 9800-40", "manufacturer": "cisco", "type": "Wireless Controller", "height_u": 1, "power_watts": 350, "ports": 8},
    "aruba_ap535": {"name": "Aruba AP-535", "manufacturer": "aruba", "type": "Access Point", "height_u": 0, "power_watts": 25, "ports": 2},
}

# =============================================================================
# Network Architecture - VLANs & Subnets
# =============================================================================

NETWORK_VLANS = {
    # Management
    10: {"name": "MGMT", "cidr": "10.0.10.0/24", "description": "Management network - OOB access", "gateway": "10.0.10.1"},

    # Production
    20: {"name": "PROD-WEB", "cidr": "10.0.20.0/24", "description": "Production - Web servers", "gateway": "10.0.20.1"},
    21: {"name": "PROD-APP", "cidr": "10.0.21.0/24", "description": "Production - Application servers", "gateway": "10.0.21.1"},
    22: {"name": "PROD-DB", "cidr": "10.0.22.0/24", "description": "Production - Database servers", "gateway": "10.0.22.1"},

    # Development
    30: {"name": "DEV", "cidr": "10.0.30.0/24", "description": "Development environment", "gateway": "10.0.30.1"},
    31: {"name": "TEST", "cidr": "10.0.31.0/24", "description": "Test/QA environment", "gateway": "10.0.31.1"},

    # DMZ
    40: {"name": "DMZ-EXT", "cidr": "172.16.40.0/24", "description": "DMZ - External facing", "gateway": "172.16.40.1"},
    41: {"name": "DMZ-INT", "cidr": "172.16.41.0/24", "description": "DMZ - Internal services", "gateway": "172.16.41.1"},

    # Storage
    50: {"name": "STORAGE-ISCSI", "cidr": "10.0.50.0/24", "description": "Storage - iSCSI traffic", "gateway": "10.0.50.1"},
    51: {"name": "STORAGE-NFS", "cidr": "10.0.51.0/24", "description": "Storage - NFS traffic", "gateway": "10.0.51.1"},
    52: {"name": "BACKUP", "cidr": "10.0.52.0/24", "description": "Backup network", "gateway": "10.0.52.1"},

    # User networks
    100: {"name": "USERS-HQ", "cidr": "192.168.100.0/24", "description": "Paris HQ - User workstations", "gateway": "192.168.100.1"},
    101: {"name": "USERS-LYON", "cidr": "192.168.101.0/24", "description": "Lyon - User workstations", "gateway": "192.168.101.1"},
    102: {"name": "USERS-MRS", "cidr": "192.168.102.0/24", "description": "Marseille - User workstations", "gateway": "192.168.102.1"},

    # Voice/IoT
    150: {"name": "VOICE", "cidr": "192.168.150.0/24", "description": "VoIP network", "gateway": "192.168.150.1"},
    160: {"name": "IOT", "cidr": "192.168.160.0/24", "description": "IoT/Building automation", "gateway": "192.168.160.1"},

    # Guest
    200: {"name": "GUEST", "cidr": "192.168.200.0/24", "description": "Guest WiFi - Isolated", "gateway": "192.168.200.1"},
}

# =============================================================================
# Software & Licenses
# =============================================================================

SOFTWARE_CATALOG = [
    # Operating Systems
    {"name": "VMware vSphere Enterprise Plus", "publisher": "VMware", "category": "Virtualization", "version": "8.0 U2"},
    {"name": "VMware vCenter Server", "publisher": "VMware", "category": "Virtualization", "version": "8.0 U2"},
    {"name": "Microsoft Windows Server 2022 Datacenter", "publisher": "Microsoft", "category": "Operating System", "version": "21H2"},
    {"name": "Red Hat Enterprise Linux", "publisher": "Red Hat", "category": "Operating System", "version": "9.3"},
    {"name": "Ubuntu Server LTS", "publisher": "Canonical", "category": "Operating System", "version": "22.04"},

    # Databases
    {"name": "Microsoft SQL Server Enterprise", "publisher": "Microsoft", "category": "Database", "version": "2022"},
    {"name": "Oracle Database Enterprise", "publisher": "Oracle", "category": "Database", "version": "19c"},
    {"name": "PostgreSQL", "publisher": "PostgreSQL", "category": "Database", "version": "16"},

    # Backup & DR
    {"name": "Veeam Backup & Replication", "publisher": "Veeam", "category": "Backup", "version": "12.1"},
    {"name": "Commvault Complete Backup", "publisher": "Commvault", "category": "Backup", "version": "2024"},

    # Monitoring
    {"name": "Zabbix Enterprise", "publisher": "Zabbix", "category": "Monitoring", "version": "7.0 LTS"},
    {"name": "Grafana Enterprise", "publisher": "Grafana Labs", "category": "Monitoring", "version": "10.3"},
    {"name": "Splunk Enterprise", "publisher": "Splunk", "category": "SIEM", "version": "9.2"},

    # Security
    {"name": "CrowdStrike Falcon", "publisher": "CrowdStrike", "category": "Endpoint Security", "version": "2024"},
    {"name": "Tenable.io", "publisher": "Tenable", "category": "Vulnerability Management", "version": "2024"},

    # DevOps
    {"name": "GitLab Enterprise", "publisher": "GitLab", "category": "DevOps", "version": "16.8"},
    {"name": "Ansible Automation Platform", "publisher": "Red Hat", "category": "Automation", "version": "2.4"},
    {"name": "HashiCorp Terraform Enterprise", "publisher": "HashiCorp", "category": "IaC", "version": "1.7"},

    # Collaboration
    {"name": "Microsoft 365 E5", "publisher": "Microsoft", "category": "Collaboration", "version": "2024"},
]

# =============================================================================
# Contracts
# =============================================================================

CONTRACT_TEMPLATES = [
    {"name": "Cisco SmartNet Total Care", "type": "maintenance", "vendor": "Westcon-Comstor", "annual_cost": 45000},
    {"name": "HPE Proactive Care 24x7", "type": "maintenance", "vendor": "Ingram Micro", "annual_cost": 35000},
    {"name": "Dell ProSupport Plus", "type": "maintenance", "vendor": "TD Synnex", "annual_cost": 28000},
    {"name": "Fortinet FortiCare Premium", "type": "support", "vendor": "Exclusive Networks", "annual_cost": 18000},
    {"name": "VMware Production Support", "type": "support", "vendor": "Arrow ECS", "annual_cost": 52000},
    {"name": "NetApp SupportEdge Premium", "type": "maintenance", "vendor": "Ingram Micro", "annual_cost": 42000},
    {"name": "DC Colocation Paris DC1", "type": "service", "vendor": "Equinix", "annual_cost": 180000},
    {"name": "DC Colocation Lyon DC2", "type": "service", "vendor": "Data4", "annual_cost": 95000},
    {"name": "Internet Transit 10Gbps", "type": "service", "vendor": "Cogent", "annual_cost": 36000},
    {"name": "MPLS WAN - 5 sites", "type": "service", "vendor": "Orange Business", "annual_cost": 72000},
]

# =============================================================================
# Knowledge Base Articles
# =============================================================================

KB_ARTICLES = [
    {
        "title": "Network Emergency Response Procedure",
        "slug": "network-emergency-procedure",
        "category": "Procedures",
        "summary": "Step-by-step guide for handling network outages",
        "content": """# Network Emergency Response Procedure

## Severity Classification

| Severity | Definition | Response Time | Escalation |
|----------|-----------|---------------|------------|
| P1 - Critical | Complete network outage | 15 min | Immediate |
| P2 - High | Partial outage, >50% users | 30 min | 1 hour |
| P3 - Medium | Single site/service affected | 2 hours | 4 hours |
| P4 - Low | Performance degradation | 4 hours | Next business day |

## Initial Response Checklist

1. **Identify scope** - Which sites/services are affected?
2. **Check monitoring** - Zabbix dashboards, network topology
3. **Verify core infrastructure** - Core routers, firewalls, ISP links
4. **Contact NOC** - If P1/P2, immediate escalation

## Key Contacts

- Network Lead: Sophie Leroy (s.leroy@techcorp.local)
- On-call: +33 1 XX XX XX XX
- Cisco TAC: 1-800-553-2447

## Recovery Steps

### For Core Network Issues
1. Check `CORE-RTR-01` and `CORE-RTR-02` status
2. Verify BGP sessions: `show ip bgp summary`
3. Check interface status: `show interface status`
4. Review logs: `show logging`
""",
        "is_internal": True
    },
    {
        "title": "Server Provisioning Standard",
        "slug": "server-provisioning",
        "category": "Standards",
        "summary": "Standard procedure for new server deployment",
        "content": """# Server Provisioning Standard

## Prerequisites

- Approved change request (CR)
- Rack space allocated in DCIM
- Network ports assigned
- IP addresses allocated in IPAM

## VM Provisioning Steps

### 1. vSphere Configuration
```
Cluster: PROD-CLUSTER-01 or DEV-CLUSTER-01
Datastore: VSAN-PROD or VSAN-DEV
Resource Pool: Based on environment
```

### 2. Network Configuration
- VLAN assignment per environment:
  - Production Web: VLAN 20
  - Production App: VLAN 21
  - Production DB: VLAN 22
  - Development: VLAN 30

### 3. OS Installation
- Windows: Use approved gold image
- Linux: Kickstart/Preseed from PXE

### 4. Post-Install
- Join domain
- Install monitoring agent (Zabbix)
- Install security agent (CrowdStrike)
- Register in CMDB (Inframate)
""",
        "is_internal": True
    },
    {
        "title": "VPN Connection Guide",
        "slug": "vpn-connection-guide",
        "category": "How-To",
        "summary": "How to connect to the corporate VPN",
        "content": """# VPN Connection Guide

## FortiClient VPN Setup

### Download
1. Go to https://vpn.techcorp.com
2. Download FortiClient for your OS

### Configuration
- **VPN Name**: TechCorp VPN
- **Remote Gateway**: vpn.techcorp.com
- **Port**: 443
- **Authentication**: SAML (Azure AD)

### Connecting
1. Open FortiClient
2. Select "TechCorp VPN"
3. Click Connect
4. Authenticate via Microsoft 365

## Troubleshooting

### "Connection Failed"
- Check internet connectivity
- Try alternate gateway: vpn2.techcorp.com
- Contact helpdesk if persists

### "Certificate Error"
- Update FortiClient to latest version
- Clear browser cache
""",
        "is_internal": False
    },
    {
        "title": "Password Policy",
        "slug": "password-policy",
        "category": "Security",
        "summary": "Corporate password requirements and best practices",
        "content": """# Password Policy

## Requirements

- Minimum **14 characters**
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 number
- At least 1 special character
- Cannot contain username
- Cannot reuse last 12 passwords

## Password Expiration

- Standard accounts: 90 days
- Admin accounts: 60 days
- Service accounts: 365 days (with exception)

## MFA Requirement

All accounts must have MFA enabled:
- Recommended: Microsoft Authenticator
- Alternative: Hardware token (YubiKey)

## Self-Service Password Reset

1. Go to https://passwordreset.techcorp.com
2. Verify identity via MFA
3. Set new password
""",
        "is_internal": False
    },
]

# =============================================================================
# Ticket Templates
# =============================================================================

TICKET_TEMPLATES = [
    {"name": "New Employee Onboarding", "title": "Onboarding: {employee_name}", "description": "## New Employee Setup\n\n**Employee**: {employee_name}\n**Department**: {department}\n**Start Date**: {start_date}\n\n### Checklist\n- [ ] Create AD account\n- [ ] Setup email & M365\n- [ ] Provision workstation\n- [ ] Configure VPN access\n- [ ] Security awareness training\n- [ ] Badge access request", "type": "request", "priority": "medium", "category": "Onboarding"},
    {"name": "Server Provisioning", "title": "New Server: {server_name}", "description": "## Server Request\n\n**Server Name**: {server_name}\n**Environment**: Production / Dev / Test\n**OS**: Windows / Linux\n**Resources**: CPU, RAM, Storage\n**Justification**: {justification}\n\n### Approvals Required\n- [ ] Technical approval\n- [ ] Security review\n- [ ] Cost center approval", "type": "request", "priority": "medium", "category": "Infrastructure"},
    {"name": "Network Change Request", "title": "Network Change: {description}", "description": "## Network Change\n\n**Change Description**: {description}\n**Affected Systems**: {systems}\n**Maintenance Window**: {window}\n\n### Risk Assessment\n- Impact: Low / Medium / High\n- Rollback Plan: Yes / No", "type": "change", "priority": "high", "category": "Network"},
    {"name": "Security Incident", "title": "Security Incident: {summary}", "description": "## Security Incident Report\n\n**Incident Summary**: {summary}\n**Detection Time**: {detection_time}\n**Affected Systems**: {affected}\n\n### Immediate Actions Taken\n{actions}\n\n### Escalation Required\n- [ ] CISO notification\n- [ ] Legal notification\n- [ ] External forensics", "type": "incident", "priority": "critical", "category": "Security"},
    {"name": "Hardware Failure", "title": "Hardware Failure: {equipment}", "description": "## Hardware Failure Report\n\n**Equipment**: {equipment}\n**Serial Number**: {serial}\n**Location**: {location}\n**Symptoms**: {symptoms}\n\n### Support Case\n- Vendor: {vendor}\n- Case #: (pending)", "type": "incident", "priority": "high", "category": "Hardware"},
]

# =============================================================================
# Helper Functions
# =============================================================================

def random_string(length: int = 8) -> str:
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def random_mac() -> str:
    return ':'.join([f'{random.randint(0, 255):02x}' for _ in range(6)])

def random_serial(prefix: str = "SN") -> str:
    return f"{prefix}-{random_string(4).upper()}-{random_string(6).upper()}"

_asset_counter = 1000
def next_asset_tag() -> str:
    global _asset_counter
    _asset_counter += 1
    return f"TCORP-{_asset_counter:06d}"

def random_date_past(days_min: int = 30, days_max: int = 730) -> date:
    return date.today() - timedelta(days=random.randint(days_min, days_max))

def random_date_future(days_min: int = 30, days_max: int = 365) -> date:
    return date.today() + timedelta(days=random.randint(days_min, days_max))

def random_datetime_past(days_max: int = 30) -> datetime:
    return datetime.now(timezone.utc) - timedelta(minutes=random.randint(1, days_max * 24 * 60))

# =============================================================================
# Data Storage (for cross-references)
# =============================================================================

class DataStore:
    def __init__(self):
        self.users: List[models.User] = []
        self.entities: List[models.Entity] = []
        self.locations: Dict[str, models.Location] = {}
        self.manufacturers: Dict[str, models.Manufacturer] = {}
        self.suppliers: Dict[str, models.Supplier] = {}
        self.equipment_types: Dict[str, models.EquipmentType] = {}
        self.equipment_models: Dict[str, models.EquipmentModel] = {}
        self.racks: Dict[str, models.Rack] = {}
        self.equipment: Dict[str, models.Equipment] = {}
        self.subnets: Dict[int, models.Subnet] = {}  # keyed by VLAN
        self.ip_addresses: Dict[str, models.IPAddress] = {}
        self.ports: Dict[str, models.NetworkPort] = {}
        self.software: List[models.Software] = []
        self.contracts: List[models.Contract] = []


store = DataStore()

# =============================================================================
# Seeder Functions
# =============================================================================

def seed_users(db: Session) -> None:
    print("  Creating IT team users...")
    for user_data in IT_TEAM:
        existing = db.query(models.User).filter(models.User.username == user_data["username"]).first()
        if existing:
            store.users.append(existing)
            continue

        user = models.User(
            username=user_data["username"],
            email=user_data["email"],
            hashed_password=get_password_hash("TechCorp2024!"),
            role=user_data["role"],
            permissions=user_data["permissions"],
            is_active=True
        )
        db.add(user)
        store.users.append(user)

    db.commit()
    print(f"    Created {len(store.users)} users")


def seed_entities(db: Session) -> None:
    print("  Creating business entities...")
    for entity_data in ENTITIES:
        existing = db.query(models.Entity).filter(models.Entity.name == entity_data["name"]).first()
        if existing:
            store.entities.append(existing)
            continue

        entity = models.Entity(
            name=entity_data["name"],
            description=entity_data["description"],
            is_active=True
        )
        db.add(entity)
        store.entities.append(entity)

    db.commit()
    print(f"    Created {len(store.entities)} entities")


def seed_locations(db: Session, minimal: bool = False) -> None:
    print("  Creating locations...")
    location_sets = ["paris_dc1", "offices"]
    if not minimal:
        location_sets.append("lyon_dc2")

    for loc_set in location_sets:
        for loc_data in LOCATIONS.get(loc_set, []):
            key = f"{loc_data['site']}-{loc_data['room']}"
            existing = db.query(models.Location).filter(
                models.Location.site == loc_data["site"],
                models.Location.room == loc_data["room"]
            ).first()
            if existing:
                store.locations[key] = existing
                continue

            location = models.Location(
                site=loc_data["site"],
                building=loc_data.get("building"),
                room=loc_data.get("room")
            )
            db.add(location)
            store.locations[key] = location

    db.commit()
    print(f"    Created {len(store.locations)} locations")


def seed_manufacturers(db: Session) -> None:
    print("  Creating manufacturers...")
    for key, mfr_data in MANUFACTURERS.items():
        existing = db.query(models.Manufacturer).filter(models.Manufacturer.name == mfr_data["name"]).first()
        if existing:
            store.manufacturers[key] = existing
            continue

        mfr = models.Manufacturer(
            name=mfr_data["name"],
            website=mfr_data["website"]
        )
        db.add(mfr)
        store.manufacturers[key] = mfr

    db.commit()
    print(f"    Created {len(store.manufacturers)} manufacturers")


def seed_suppliers(db: Session) -> None:
    print("  Creating suppliers...")
    for sup_data in SUPPLIERS:
        existing = db.query(models.Supplier).filter(models.Supplier.name == sup_data["name"]).first()
        if existing:
            store.suppliers[sup_data["name"]] = existing
            continue

        supplier = models.Supplier(
            name=sup_data["name"],
            contact_email=sup_data["contact_email"],
            phone=sup_data["phone"]
        )
        db.add(supplier)
        store.suppliers[sup_data["name"]] = supplier

    db.commit()
    print(f"    Created {len(store.suppliers)} suppliers")


def seed_equipment_types(db: Session) -> None:
    print("  Creating equipment types...")
    for type_data in EQUIPMENT_TYPES:
        existing = db.query(models.EquipmentType).filter(models.EquipmentType.name == type_data["name"]).first()
        if existing:
            store.equipment_types[type_data["name"]] = existing
            continue

        eq_type = models.EquipmentType(
            name=type_data["name"],
            icon=type_data.get("icon", "pi-box"),
            supports_remote_execution=type_data.get("supports_remote_execution", False),
            hierarchy_level=type_data.get("hierarchy_level", 99)
        )
        db.add(eq_type)
        store.equipment_types[type_data["name"]] = eq_type

    db.commit()
    print(f"    Created {len(store.equipment_types)} equipment types")


def seed_equipment_models(db: Session) -> None:
    print("  Creating equipment models...")
    for key, model_data in EQUIPMENT_MODELS.items():
        existing = db.query(models.EquipmentModel).filter(models.EquipmentModel.name == model_data["name"]).first()
        if existing:
            store.equipment_models[key] = existing
            continue

        mfr = store.manufacturers.get(model_data["manufacturer"])
        eq_type = store.equipment_types.get(model_data["type"])

        if not mfr or not eq_type:
            continue

        model = models.EquipmentModel(
            name=model_data["name"],
            manufacturer_id=mfr.id,
            equipment_type_id=eq_type.id,
            specs={
                "height_u": model_data.get("height_u", 1),
                "power_watts": model_data.get("power_watts", 500),
                "ports": model_data.get("ports", 4)
            }
        )
        db.add(model)
        store.equipment_models[key] = model

    db.commit()
    print(f"    Created {len(store.equipment_models)} equipment models")


def seed_racks(db: Session, minimal: bool = False) -> None:
    print("  Creating racks...")

    # Paris DC1 racks
    paris_racks = [
        {"name": "PAR-A1-R01", "location": "Paris DC1-Server Room A1", "height": 42},
        {"name": "PAR-A1-R02", "location": "Paris DC1-Server Room A1", "height": 42},
        {"name": "PAR-A1-R03", "location": "Paris DC1-Server Room A1", "height": 42},
        {"name": "PAR-A2-R01", "location": "Paris DC1-Server Room A2", "height": 42},
        {"name": "PAR-A2-R02", "location": "Paris DC1-Server Room A2", "height": 42},
        {"name": "PAR-B1-R01", "location": "Paris DC1-Network Room B1", "height": 42},
    ]

    lyon_racks = [
        {"name": "LYN-D1-R01", "location": "Lyon DC2-DR Room 1", "height": 42},
        {"name": "LYN-D1-R02", "location": "Lyon DC2-DR Room 1", "height": 42},
        {"name": "LYN-D2-R01", "location": "Lyon DC2-DR Room 2", "height": 42},
    ]

    office_racks = [
        {"name": "HQ-IT-R01", "location": "Paris HQ-Floor 15 - IT", "height": 24},
        {"name": "LYN-OFF-R01", "location": "Lyon Office-Floor 8 - Comms", "height": 12},
        {"name": "MRS-OFF-R01", "location": "Marseille Office-IT Closet", "height": 12},
    ]

    all_racks = paris_racks + office_racks
    if not minimal:
        all_racks += lyon_racks

    for rack_data in all_racks:
        existing = db.query(models.Rack).filter(models.Rack.name == rack_data["name"]).first()
        if existing:
            store.racks[rack_data["name"]] = existing
            continue

        location = store.locations.get(rack_data["location"])
        if not location:
            continue

        rack = models.Rack(
            name=rack_data["name"],
            location_id=location.id,
            height_u=rack_data["height"],
            width_mm=600,
            depth_mm=1200,
            max_power_kw=15.0
        )
        db.add(rack)
        store.racks[rack_data["name"]] = rack

    db.commit()
    print(f"    Created {len(store.racks)} racks")


def seed_subnets(db: Session) -> None:
    print("  Creating subnets (VLANs)...")
    for vlan_id, vlan_data in NETWORK_VLANS.items():
        existing = db.query(models.Subnet).filter(models.Subnet.cidr == vlan_data["cidr"]).first()
        if existing:
            store.subnets[vlan_id] = existing
            continue

        subnet = models.Subnet(
            cidr=vlan_data["cidr"],
            name=f"VLAN {vlan_id} - {vlan_data['name']}",
            description=vlan_data["description"]
        )
        db.add(subnet)
        store.subnets[vlan_id] = subnet

    db.commit()
    print(f"    Created {len(store.subnets)} subnets")


def create_equipment_with_ip(
    db: Session,
    name: str,
    model_key: str,
    rack_name: str,
    position_u: int,
    vlan: int,
    ip_suffix: int,
    status: str = "in_service",
    supplier_name: Optional[str] = None,
    warranty_expired: bool = False,
    warranty_expiring_soon: bool = False
) -> Optional[models.Equipment]:
    """Helper to create equipment with IP address assignment."""
    model = store.equipment_models.get(model_key)
    rack = store.racks.get(rack_name)

    if not model or not rack:
        return None

    height_u = model.specs.get("height_u", 1) if model.specs else 1

    supplier = store.suppliers.get(supplier_name) if supplier_name else None

    # Determine warranty expiry based on parameters
    if warranty_expired:
        warranty_expiry = datetime.now(timezone.utc) - timedelta(days=random.randint(30, 365))
    elif warranty_expiring_soon:
        warranty_expiry = datetime.now(timezone.utc) + timedelta(days=random.randint(7, 30))
    else:
        warranty_expiry = datetime.now(timezone.utc) + timedelta(days=random.randint(365, 1825))

    equipment = models.Equipment(
        name=name,
        model_id=model.id,
        serial_number=random_serial(),
        asset_tag=next_asset_tag(),
        status=status,
        location_id=rack.location_id,
        supplier_id=supplier.id if supplier else None,
        entity_id=store.entities[0].id if store.entities else None,
        rack_id=rack.id,
        position_u=position_u,
        height_u=height_u,
        purchase_date=random_date_past(365, 1095),
        warranty_expiry=warranty_expiry,
    )
    db.add(equipment)
    db.flush()

    store.equipment[name] = equipment

    # Create management IP
    if vlan in store.subnets:
        subnet = store.subnets[vlan]
        base = subnet.cidr.rsplit('.', 1)[0]
        ip_addr = f"{base}.{ip_suffix}"

        ip = models.IPAddress(
            address=ip_addr,
            subnet_id=subnet.id,
            status="active",
            hostname=f"{name.lower()}.techcorp.local",
            equipment_id=equipment.id
        )
        db.add(ip)
        store.ip_addresses[ip_addr] = ip

    return equipment


def seed_network_infrastructure(db: Session, minimal: bool = False) -> None:
    """Create core network infrastructure with proper topology."""
    print("  Creating network infrastructure...")

    # === Paris DC1 - Core Network ===
    # Core Routers (Network Room B1, PAR-B1-R01)
    create_equipment_with_ip(db, "CORE-RTR-01", "cisco_asr1001x", "PAR-B1-R01", 40, 10, 1, supplier_name="Westcon-Comstor")
    create_equipment_with_ip(db, "CORE-RTR-02", "cisco_asr1001x", "PAR-B1-R01", 38, 10, 2, supplier_name="Westcon-Comstor")

    # Core Switches
    create_equipment_with_ip(db, "CORE-SW-01", "cisco_nexus9336", "PAR-B1-R01", 36, 10, 3, supplier_name="Westcon-Comstor")
    create_equipment_with_ip(db, "CORE-SW-02", "cisco_nexus9336", "PAR-B1-R01", 34, 10, 4, supplier_name="Westcon-Comstor")

    # Firewalls
    create_equipment_with_ip(db, "FW-EDGE-01", "fortinet_fg600e", "PAR-B1-R01", 30, 10, 5, supplier_name="Exclusive Networks")
    create_equipment_with_ip(db, "FW-EDGE-02", "fortinet_fg600e", "PAR-B1-R01", 28, 10, 6, supplier_name="Exclusive Networks")
    create_equipment_with_ip(db, "FW-INTERNAL-01", "paloalto_pa5250", "PAR-B1-R01", 24, 10, 7, supplier_name="Exclusive Networks")

    # Load Balancers
    create_equipment_with_ip(db, "LB-PROD-01", "f5_i5800", "PAR-B1-R01", 22, 10, 8, supplier_name="Arrow ECS")
    create_equipment_with_ip(db, "LB-PROD-02", "f5_i5800", "PAR-B1-R01", 20, 10, 9, supplier_name="Arrow ECS")

    # Distribution Switches
    create_equipment_with_ip(db, "DIST-SW-A1-01", "cisco_catalyst9500", "PAR-A1-R01", 40, 10, 10, supplier_name="Westcon-Comstor")
    create_equipment_with_ip(db, "DIST-SW-A1-02", "cisco_catalyst9500", "PAR-A1-R01", 38, 10, 11, supplier_name="Westcon-Comstor")
    create_equipment_with_ip(db, "DIST-SW-A2-01", "cisco_catalyst9500", "PAR-A2-R01", 40, 10, 12, supplier_name="Westcon-Comstor")

    # Access Switches
    create_equipment_with_ip(db, "ACC-SW-A1-R01", "cisco_catalyst9300", "PAR-A1-R01", 36, 10, 20, supplier_name="Westcon-Comstor")
    create_equipment_with_ip(db, "ACC-SW-A1-R02", "cisco_catalyst9300", "PAR-A1-R02", 40, 10, 21, supplier_name="Westcon-Comstor")
    create_equipment_with_ip(db, "ACC-SW-A1-R03", "cisco_catalyst9300", "PAR-A1-R03", 40, 10, 22, supplier_name="Westcon-Comstor")
    create_equipment_with_ip(db, "ACC-SW-A2-R01", "cisco_catalyst9300", "PAR-A2-R01", 36, 10, 23, supplier_name="Westcon-Comstor")
    create_equipment_with_ip(db, "ACC-SW-A2-R02", "cisco_catalyst9300", "PAR-A2-R02", 40, 10, 24, supplier_name="Westcon-Comstor")

    # Wireless Controller
    create_equipment_with_ip(db, "WLC-01", "cisco_wlc9800", "PAR-B1-R01", 18, 10, 30, supplier_name="Westcon-Comstor")

    db.commit()
    print(f"    Created network infrastructure ({len([e for e in store.equipment.values() if 'SW' in e.name or 'RTR' in e.name or 'FW' in e.name or 'LB' in e.name or 'WLC' in e.name])} devices)")


def seed_server_infrastructure(db: Session, minimal: bool = False) -> None:
    """Create server and storage infrastructure with varied statuses."""
    print("  Creating server infrastructure...")

    # === Virtualization Hosts - Paris DC1 ===
    # ESXi hosts in Server Room A1
    for i in range(1, 5 if not minimal else 3):
        # ESX-PROD-04 is under maintenance (RAM upgrade)
        status = "maintenance" if i == 4 else "in_service"
        warranty_expired = i == 1  # First host has expired warranty
        create_equipment_with_ip(db, f"ESX-PROD-{i:02d}", "hpe_dl380g10", "PAR-A1-R01", 30 - (i-1)*2, 10, 40 + i,
                                 status=status, supplier_name="Ingram Micro", warranty_expired=warranty_expired)

    # ESXi hosts in Server Room A2 (Dev/Test)
    for i in range(1, 4 if not minimal else 2):
        # ESX-DEV-03 is retired (end of life)
        status = "retired" if i == 3 else "in_service"
        warranty_expiring = i == 2  # Second host warranty expiring soon
        create_equipment_with_ip(db, f"ESX-DEV-{i:02d}", "dell_r750", "PAR-A2-R01", 30 - (i-1)*2, 10, 50 + i,
                                 status=status, supplier_name="TD Synnex", warranty_expiring_soon=warranty_expiring)

    # Physical servers
    create_equipment_with_ip(db, "BACKUP-SRV-01", "dell_r650", "PAR-A1-R02", 38, 10, 60, supplier_name="TD Synnex")
    # MONITOR-SRV-01 warranty expiring soon
    create_equipment_with_ip(db, "MONITOR-SRV-01", "hpe_dl360g10", "PAR-A1-R02", 36, 10, 61,
                             supplier_name="Ingram Micro", warranty_expiring_soon=True)

    # Storage
    create_equipment_with_ip(db, "SAN-PROD-01", "netapp_aff400", "PAR-A1-R02", 30, 50, 10, supplier_name="Ingram Micro")
    # SAN-PROD-02 under maintenance (firmware upgrade)
    create_equipment_with_ip(db, "SAN-PROD-02", "netapp_aff400", "PAR-A1-R02", 26, 50, 11,
                             status="maintenance", supplier_name="Ingram Micro")
    create_equipment_with_ip(db, "SAN-DEV-01", "dell_unity500", "PAR-A2-R02", 30, 50, 20, supplier_name="TD Synnex")

    # Backup Appliance
    create_equipment_with_ip(db, "BACKUP-APP-01", "dell_dp4400", "PAR-A1-R02", 20, 52, 10, supplier_name="TD Synnex")

    # UPS Units
    create_equipment_with_ip(db, "UPS-A1-R01", "apc_srt10k", "PAR-A1-R01", 1, 10, 100, supplier_name="Arrow ECS")
    # UPS-A1-R02 warranty expired
    create_equipment_with_ip(db, "UPS-A1-R02", "apc_srt5k", "PAR-A1-R02", 1, 10, 101,
                             supplier_name="Arrow ECS", warranty_expired=True)
    create_equipment_with_ip(db, "UPS-B1-R01", "apc_srt10k", "PAR-B1-R01", 1, 10, 102, supplier_name="Arrow ECS")

    # === Equipment in Stock (spare parts) ===
    create_equipment_with_ip(db, "SPARE-SRV-01", "hpe_dl360g10", "PAR-A1-R03", 38, 10, 70,
                             status="stock", supplier_name="Ingram Micro")
    create_equipment_with_ip(db, "SPARE-SW-01", "cisco_catalyst9300", "PAR-A1-R03", 36, 10, 71,
                             status="stock", supplier_name="Westcon-Comstor")
    create_equipment_with_ip(db, "SPARE-SW-02", "aruba_6300", "PAR-A1-R03", 34, 10, 72,
                             status="stock", supplier_name="Westcon-Comstor")

    # === Retired equipment (decommissioned) ===
    create_equipment_with_ip(db, "OLD-SRV-01", "dell_r650", "PAR-A2-R02", 38, 10, 80,
                             status="retired", supplier_name="TD Synnex", warranty_expired=True)
    create_equipment_with_ip(db, "OLD-SW-01", "cisco_catalyst9300", "PAR-A2-R02", 36, 10, 81,
                             status="retired", supplier_name="Westcon-Comstor", warranty_expired=True)

    if not minimal:
        # Lyon DC2 DR Infrastructure
        create_equipment_with_ip(db, "CORE-RTR-DR-01", "juniper_mx204", "LYN-D1-R01", 40, 10, 201, supplier_name="Westcon-Comstor")
        create_equipment_with_ip(db, "CORE-SW-DR-01", "cisco_nexus93180", "LYN-D1-R01", 38, 10, 202, supplier_name="Westcon-Comstor")
        create_equipment_with_ip(db, "FW-DR-01", "fortinet_fg600e", "LYN-D1-R01", 34, 10, 203, supplier_name="Exclusive Networks")

        for i in range(1, 3):
            create_equipment_with_ip(db, f"ESX-DR-{i:02d}", "hpe_dl380g10", "LYN-D1-R02", 38 - (i-1)*2, 10, 210 + i, supplier_name="Ingram Micro")

        create_equipment_with_ip(db, "SAN-DR-01", "netapp_aff400", "LYN-D2-R01", 30, 50, 200, supplier_name="Ingram Micro")
        create_equipment_with_ip(db, "BACKUP-DR-01", "dell_dp4400", "LYN-D2-R01", 24, 52, 200, supplier_name="TD Synnex")

        # Lyon spare equipment
        create_equipment_with_ip(db, "SPARE-DR-SRV-01", "hpe_dl360g10", "LYN-D2-R01", 38, 10, 220,
                                 status="stock", supplier_name="Ingram Micro")

    # Office equipment
    create_equipment_with_ip(db, "SW-HQ-01", "aruba_6300", "HQ-IT-R01", 20, 10, 150, supplier_name="Westcon-Comstor")
    create_equipment_with_ip(db, "SW-LYON-01", "aruba_6300", "LYN-OFF-R01", 10, 10, 151, supplier_name="Westcon-Comstor")
    create_equipment_with_ip(db, "SW-MRS-01", "aruba_6300", "MRS-OFF-R01", 10, 10, 152, supplier_name="Westcon-Comstor")

    db.commit()

    # Count by status
    status_counts = {}
    for eq in store.equipment.values():
        status_counts[eq.status] = status_counts.get(eq.status, 0) + 1
    print(f"    Created server infrastructure:")
    for status, count in status_counts.items():
        print(f"      - {status}: {count} devices")


def seed_network_ports_and_connections(db: Session) -> None:
    """Create network ports and establish connections for topology."""
    print("  Creating network ports and connections...")

    port_count = 0
    connection_count = 0

    # Create ports for all equipment
    for eq_name, equipment in store.equipment.items():
        model = db.query(models.EquipmentModel).filter(models.EquipmentModel.id == equipment.model_id).first()
        if not model or not model.specs:
            continue

        num_ports = model.specs.get("ports", 4)
        eq_type = db.query(models.EquipmentType).filter(models.EquipmentType.id == model.equipment_type_id).first()

        # Determine port type based on equipment
        if "RTR" in eq_name or "Core" in eq_type.name if eq_type else False:
            port_types = [("sfp+", "10G"), ("sfp+", "10G"), ("sfp", "1G"), ("console", "")]
        elif "SW" in eq_name and ("CORE" in eq_name or "DIST" in eq_name):
            port_types = [("sfp+", "25G")] * min(num_ports // 2, 12) + [("sfp+", "10G")] * (num_ports - num_ports // 2)
        elif "SW" in eq_name:
            port_types = [("ethernet", "1G")] * (num_ports - 4) + [("sfp+", "10G")] * 4
        elif "ESX" in eq_name or "SRV" in eq_name:
            port_types = [("ethernet", "10G")] * num_ports
        elif "SAN" in eq_name:
            port_types = [("sfp+", "16G FC")] * (num_ports // 2) + [("ethernet", "10G")] * (num_ports // 2)
        else:
            port_types = [("ethernet", "1G")] * num_ports

        for i, (ptype, speed) in enumerate(port_types[:num_ports]):
            port_name = f"eth{i}" if ptype != "sfp+" and ptype != "sfp" else f"sfp{i}"
            if ptype == "console":
                port_name = "console0"

            port = models.NetworkPort(
                equipment_id=equipment.id,
                name=port_name,
                port_type=ptype,
                speed=speed,
                mac_address=random_mac()
            )
            db.add(port)
            port_key = f"{eq_name}:{port_name}"
            store.ports[port_key] = port
            port_count += 1

    db.commit()

    # Define topology connections
    connections = [
        # Core layer - Routers to Core Switches
        ("CORE-RTR-01:sfp0", "CORE-SW-01:sfp0"),
        ("CORE-RTR-01:sfp1", "CORE-SW-02:sfp0"),
        ("CORE-RTR-02:sfp0", "CORE-SW-01:sfp1"),
        ("CORE-RTR-02:sfp1", "CORE-SW-02:sfp1"),

        # Core Switches interconnect
        ("CORE-SW-01:sfp2", "CORE-SW-02:sfp2"),
        ("CORE-SW-01:sfp3", "CORE-SW-02:sfp3"),

        # Firewalls to Core
        ("FW-EDGE-01:eth0", "CORE-RTR-01:sfp2"),
        ("FW-EDGE-02:eth0", "CORE-RTR-02:sfp2"),
        ("FW-INTERNAL-01:eth0", "CORE-SW-01:sfp4"),
        ("FW-INTERNAL-01:eth1", "CORE-SW-02:sfp4"),

        # Load Balancers to Core
        ("LB-PROD-01:eth0", "CORE-SW-01:sfp5"),
        ("LB-PROD-02:eth0", "CORE-SW-02:sfp5"),

        # Distribution to Core
        ("DIST-SW-A1-01:sfp0", "CORE-SW-01:sfp6"),
        ("DIST-SW-A1-01:sfp1", "CORE-SW-02:sfp6"),
        ("DIST-SW-A1-02:sfp0", "CORE-SW-01:sfp7"),
        ("DIST-SW-A1-02:sfp1", "CORE-SW-02:sfp7"),
        ("DIST-SW-A2-01:sfp0", "CORE-SW-01:sfp8"),
        ("DIST-SW-A2-01:sfp1", "CORE-SW-02:sfp8"),

        # Access to Distribution
        ("ACC-SW-A1-R01:sfp0", "DIST-SW-A1-01:sfp4"),
        ("ACC-SW-A1-R01:sfp1", "DIST-SW-A1-02:sfp4"),
        ("ACC-SW-A1-R02:sfp0", "DIST-SW-A1-01:sfp5"),
        ("ACC-SW-A1-R02:sfp1", "DIST-SW-A1-02:sfp5"),
        ("ACC-SW-A1-R03:sfp0", "DIST-SW-A1-01:sfp6"),
        ("ACC-SW-A1-R03:sfp1", "DIST-SW-A1-02:sfp6"),
        ("ACC-SW-A2-R01:sfp0", "DIST-SW-A2-01:sfp4"),
        ("ACC-SW-A2-R02:sfp0", "DIST-SW-A2-01:sfp5"),

        # Servers to Access Switches
        ("ESX-PROD-01:eth0", "ACC-SW-A1-R01:eth0"),
        ("ESX-PROD-01:eth1", "ACC-SW-A1-R01:eth1"),
        ("ESX-PROD-02:eth0", "ACC-SW-A1-R01:eth2"),
        ("ESX-PROD-02:eth1", "ACC-SW-A1-R01:eth3"),
        ("ESX-PROD-03:eth0", "ACC-SW-A1-R02:eth0"),
        ("ESX-PROD-03:eth1", "ACC-SW-A1-R02:eth1"),

        ("ESX-DEV-01:eth0", "ACC-SW-A2-R01:eth0"),
        ("ESX-DEV-01:eth1", "ACC-SW-A2-R01:eth1"),
        ("ESX-DEV-02:eth0", "ACC-SW-A2-R01:eth2"),
        ("ESX-DEV-02:eth1", "ACC-SW-A2-R01:eth3"),

        # Storage to Distribution (iSCSI)
        ("SAN-PROD-01:eth0", "DIST-SW-A1-01:sfp8"),
        ("SAN-PROD-01:eth1", "DIST-SW-A1-02:sfp8"),
        ("SAN-PROD-02:eth0", "DIST-SW-A1-01:sfp9"),
        ("SAN-PROD-02:eth1", "DIST-SW-A1-02:sfp9"),
        ("SAN-DEV-01:eth0", "DIST-SW-A2-01:sfp8"),

        # Management servers
        ("BACKUP-SRV-01:eth0", "ACC-SW-A1-R02:eth10"),
        ("MONITOR-SRV-01:eth0", "ACC-SW-A1-R02:eth11"),
        ("BACKUP-APP-01:eth0", "ACC-SW-A1-R02:eth12"),

        # Wireless Controller
        ("WLC-01:eth0", "CORE-SW-01:sfp10"),
        ("WLC-01:eth1", "CORE-SW-02:sfp10"),

        # Office switches to Core (WAN uplinks simulated)
        ("SW-HQ-01:sfp0", "CORE-SW-01:sfp11"),
        ("SW-LYON-01:sfp0", "CORE-SW-01:sfp12"),
        ("SW-MRS-01:sfp0", "CORE-SW-01:sfp13"),
    ]

    # Create connections
    for port_a_key, port_b_key in connections:
        port_a = store.ports.get(port_a_key)
        port_b = store.ports.get(port_b_key)

        if port_a and port_b:
            port_a.connected_to_id = port_b.id
            port_b.connected_to_id = port_a.id
            connection_count += 1

    db.commit()
    print(f"    Created {port_count} ports with {connection_count} connections")


def seed_additional_ips(db: Session) -> None:
    """Create additional IP addresses for various networks."""
    print("  Creating additional IP addresses...")

    ip_count = 0

    # Production server IPs
    prod_servers = [e for e in store.equipment.values() if "ESX-PROD" in e.name]
    for i, server in enumerate(prod_servers):
        # Add IPs on different production VLANs
        for vlan, suffix_base in [(20, 10), (21, 10), (22, 10), (50, 110), (51, 110)]:
            if vlan in store.subnets:
                subnet = store.subnets[vlan]
                base = subnet.cidr.rsplit('.', 1)[0]
                ip_addr = f"{base}.{suffix_base + i}"

                if ip_addr not in store.ip_addresses:
                    ip = models.IPAddress(
                        address=ip_addr,
                        subnet_id=subnet.id,
                        status="active",
                        hostname=f"{server.name.lower()}-v{vlan}.techcorp.local",
                        equipment_id=server.id
                    )
                    db.add(ip)
                    store.ip_addresses[ip_addr] = ip
                    ip_count += 1

    # Dev server IPs
    dev_servers = [e for e in store.equipment.values() if "ESX-DEV" in e.name]
    for i, server in enumerate(dev_servers):
        for vlan, suffix_base in [(30, 10), (31, 10), (50, 130)]:
            if vlan in store.subnets:
                subnet = store.subnets[vlan]
                base = subnet.cidr.rsplit('.', 1)[0]
                ip_addr = f"{base}.{suffix_base + i}"

                if ip_addr not in store.ip_addresses:
                    ip = models.IPAddress(
                        address=ip_addr,
                        subnet_id=subnet.id,
                        status="active",
                        hostname=f"{server.name.lower()}-v{vlan}.techcorp.local",
                        equipment_id=server.id
                    )
                    db.add(ip)
                    store.ip_addresses[ip_addr] = ip
                    ip_count += 1

    # DMZ IPs (web/app gateways)
    for vlan in [40, 41]:
        if vlan in store.subnets:
            subnet = store.subnets[vlan]
            base = subnet.cidr.rsplit('.', 1)[0]
            for i in range(10, 20):
                ip_addr = f"{base}.{i}"
                if ip_addr not in store.ip_addresses:
                    ip = models.IPAddress(
                        address=ip_addr,
                        subnet_id=subnet.id,
                        status="active" if i < 15 else "reserved",
                        hostname=f"dmz-svc-{i}.techcorp.local" if i < 15 else None
                    )
                    db.add(ip)
                    store.ip_addresses[ip_addr] = ip
                    ip_count += 1

    # User network IPs (simulated DHCP scope)
    for vlan in [100, 101, 102]:
        if vlan in store.subnets:
            subnet = store.subnets[vlan]
            base = subnet.cidr.rsplit('.', 1)[0]
            for i in range(100, 150):
                ip_addr = f"{base}.{i}"
                if ip_addr not in store.ip_addresses:
                    status = random.choice(["active", "active", "active", "available"])
                    ip = models.IPAddress(
                        address=ip_addr,
                        subnet_id=subnet.id,
                        status=status,
                        hostname=f"ws-{random_string(6)}.techcorp.local" if status == "active" else None,
                        mac_address=random_mac() if status == "active" else None,
                        last_scanned_at=random_datetime_past(7) if status == "active" else None
                    )
                    db.add(ip)
                    store.ip_addresses[ip_addr] = ip
                    ip_count += 1

    db.commit()
    print(f"    Created {ip_count} additional IP addresses")


def seed_software(db: Session) -> None:
    """Create software catalog and licenses."""
    print("  Creating software catalog...")

    for sw_data in SOFTWARE_CATALOG:
        existing = db.query(models.Software).filter(models.Software.name == sw_data["name"]).first()
        if existing:
            store.software.append(existing)
            continue

        software = models.Software(
            name=sw_data["name"],
            publisher=sw_data["publisher"],
            category=sw_data["category"],
            version=sw_data["version"]
        )
        db.add(software)
        store.software.append(software)

    db.commit()
    print(f"    Created {len(store.software)} software entries")

    # Create licenses with varied expiration states
    print("  Creating software licenses...")
    license_count = 0
    expired_count = 0
    expiring_soon_count = 0

    # License data: (name, type, qty, price, status_modifier)
    # status_modifier: None=normal, "expired", "expiring_soon"
    license_data = [
        ("VMware vSphere Enterprise Plus", "perpetual", 16, 85000, None),
        ("VMware vCenter Server", "perpetual", 1, 12000, None),
        ("Microsoft Windows Server 2022 Datacenter", "perpetual", 8, 48000, None),
        ("Red Hat Enterprise Linux", "subscription", 20, 15000, "expiring_soon"),  # Expiring in <30 days
        ("Microsoft SQL Server Enterprise", "perpetual", 4, 56000, None),
        ("Veeam Backup & Replication", "subscription", 1, 18000, "expired"),  # Expired
        ("Zabbix Enterprise", "subscription", 1, 8000, "expiring_soon"),  # Expiring soon
        ("CrowdStrike Falcon", "subscription", 500, 45000, None),
        ("Microsoft 365 E5", "subscription", 200, 72000, None),
    ]

    for sw_name, lic_type, qty, price, status in license_data:
        software = next((s for s in store.software if s.name == sw_name), None)
        if not software:
            continue

        # Determine expiry date based on status
        if lic_type == "subscription":
            if status == "expired":
                expiry_date = date.today() - timedelta(days=random.randint(15, 45))  # Expired 15-45 days ago
                expired_count += 1
            elif status == "expiring_soon":
                expiry_date = date.today() + timedelta(days=random.randint(7, 25))  # Expires in 7-25 days
                expiring_soon_count += 1
            else:
                expiry_date = random_date_future(90, 365)  # Normal: expires in 90-365 days
        else:
            expiry_date = None

        license = models.SoftwareLicense(
            software_id=software.id,
            license_key=f"XXXX-{random_string(4).upper()}-{random_string(4).upper()}-{random_string(4).upper()}",
            license_type=lic_type,
            quantity=qty,
            purchase_date=random_date_past(365, 730),
            expiry_date=expiry_date,
            purchase_price=price
        )
        db.add(license)
        license_count += 1

    db.commit()
    print(f"    Created {license_count} licenses:")
    print(f"      - Expired: {expired_count}")
    print(f"      - Expiring soon (<30 days): {expiring_soon_count}")

    # Create installations
    print("  Creating software installations...")
    installation_count = 0

    # VMware on ESX hosts
    esxi_hosts = [e for e in store.equipment.values() if "ESX" in e.name]
    vmware_sw = next((s for s in store.software if "vSphere" in s.name), None)
    if vmware_sw:
        for host in esxi_hosts:
            inst = models.SoftwareInstallation(
                software_id=vmware_sw.id,
                equipment_id=host.id,
                installed_version=vmware_sw.version,
                installation_date=random_datetime_past(365)
            )
            db.add(inst)
            installation_count += 1

    db.commit()
    print(f"    Created {installation_count} installations")


def seed_contracts(db: Session) -> None:
    """Create maintenance and service contracts with varied expiration states."""
    print("  Creating contracts...")

    expired_count = 0
    expiring_soon_count = 0
    active_count = 0

    for i, contract_data in enumerate(CONTRACT_TEMPLATES):
        existing = db.query(models.Contract).filter(models.Contract.name == contract_data["name"]).first()
        if existing:
            store.contracts.append(existing)
            continue

        # Find supplier
        supplier = None
        for sup_name, sup in store.suppliers.items():
            if contract_data["vendor"] in sup_name:
                supplier = sup
                break

        if not supplier:
            supplier = list(store.suppliers.values())[0]

        # Vary contract status: some expired, some expiring soon, most active
        if i == 0:  # First contract is expired (Cisco SmartNet)
            start_date = date.today() - timedelta(days=random.randint(730, 1095))
            end_date = date.today() - timedelta(days=random.randint(15, 60))  # Expired 15-60 days ago
            status = "expired"
            expired_count += 1
        elif i == 1:  # Second contract expires very soon (HPE)
            start_date = date.today() - timedelta(days=random.randint(300, 350))
            end_date = date.today() + timedelta(days=random.randint(5, 15))  # Expires in 5-15 days
            status = "active"  # Still active but needs renewal urgently
            expiring_soon_count += 1
        elif i == 2:  # Third contract expiring in 30 days (Dell)
            start_date = date.today() - timedelta(days=random.randint(300, 350))
            end_date = date.today() + timedelta(days=random.randint(20, 35))  # Expires in 20-35 days
            status = "active"
            expiring_soon_count += 1
        elif i == 3:  # FortiCare - expired and not renewed
            start_date = date.today() - timedelta(days=random.randint(400, 500))
            end_date = date.today() - timedelta(days=random.randint(30, 90))  # Expired 30-90 days ago
            status = "expired"
            expired_count += 1
        else:
            # Active contracts with various end dates
            start_date = random_date_past(365, 730)
            end_date = start_date + timedelta(days=random.choice([365, 730, 1095]))
            # Make sure they're in the future
            if end_date < date.today():
                end_date = date.today() + timedelta(days=random.randint(90, 365))
            status = "active"
            active_count += 1

        contract = models.Contract(
            name=contract_data["name"],
            contract_type=contract_data["type"],
            contract_number=f"CTR-{random_string(8).upper()}",
            supplier_id=supplier.id,
            start_date=start_date,
            end_date=end_date,
            annual_cost=contract_data["annual_cost"],
            renewal_type="auto" if status == "active" else "manual",
            notes=f"Contract status: {status}" if status != "active" else None
        )
        db.add(contract)
        store.contracts.append(contract)

    db.commit()
    print(f"    Contract status distribution:")
    print(f"      - Active: {active_count}")
    print(f"      - Expiring soon (<30 days): {expiring_soon_count}")
    print(f"      - Expired: {expired_count}")

    # Link equipment to contracts
    print("  Linking equipment to contracts...")
    for contract in store.contracts:
        # Determine which equipment to link based on contract type
        if "Cisco" in contract.name:
            equipment_list = [e for e in store.equipment.values() if any(x in e.name for x in ["RTR", "SW", "WLC", "CORE", "DIST", "ACC"])]
        elif "HPE" in contract.name:
            equipment_list = [e for e in store.equipment.values() if "ESX" in e.name or "DL" in e.name]
        elif "Dell" in contract.name:
            equipment_list = [e for e in store.equipment.values() if "Dell" in e.name or "SAN-DEV" in e.name or "BACKUP" in e.name]
        elif "Fortinet" in contract.name:
            equipment_list = [e for e in store.equipment.values() if "FW" in e.name]
        elif "NetApp" in contract.name:
            equipment_list = [e for e in store.equipment.values() if "SAN-PROD" in e.name]
        else:
            equipment_list = []

        # Fallback for other contracts
        if not equipment_list:
            equipment_list = list(store.equipment.values())[:5]

        for eq in equipment_list[:10]:  # Limit to 10 per contract
            link = models.ContractEquipment(
                contract_id=contract.id,
                equipment_id=eq.id
            )
            db.add(link)

    db.commit()
    print(f"    Created {len(store.contracts)} contracts")


def seed_pdus(db: Session) -> None:
    """Create PDUs for racks."""
    print("  Creating PDUs...")
    pdu_count = 0

    for rack_name, rack in store.racks.items():
        # Each rack gets 2 PDUs (A and B feed)
        for feed in ["A", "B"]:
            pdu = models.PDU(
                name=f"PDU-{rack_name}-{feed}",
                rack_id=rack.id,
                pdu_type="metered" if "DC" in rack_name else "basic",
                total_ports=24 if rack.height_u >= 42 else 12,
                max_amps=32,
                voltage=230,
                phase="single"
            )
            db.add(pdu)
            pdu_count += 1

    db.commit()
    print(f"    Created {pdu_count} PDUs")


def seed_sla_policies(db: Session) -> None:
    """Create SLA policies."""
    print("  Creating SLA policies...")

    policies = [
        {
            "name": "Enterprise SLA",
            "description": "Enterprise-grade SLA for production systems",
            "critical_response_time": 15,
            "critical_resolution_time": 120,
            "high_response_time": 30,
            "high_resolution_time": 240,
            "medium_response_time": 120,
            "medium_resolution_time": 720,
            "low_response_time": 240,
            "low_resolution_time": 1440,
        },
        {
            "name": "Standard SLA",
            "description": "Standard SLA for non-critical systems",
            "critical_response_time": 30,
            "critical_resolution_time": 240,
            "high_response_time": 60,
            "high_resolution_time": 480,
            "medium_response_time": 240,
            "medium_resolution_time": 1440,
            "low_response_time": 480,
            "low_resolution_time": 2880,
        },
    ]

    for policy_data in policies:
        existing = db.query(models.SLAPolicy).filter(models.SLAPolicy.name == policy_data["name"]).first()
        if existing:
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
            business_start="08:00",
            business_end="18:00",
            business_days=[1, 2, 3, 4, 5]
        )
        db.add(policy)

    db.commit()
    print("    Created SLA policies")


def seed_ticket_templates(db: Session) -> None:
    """Create ticket templates."""
    print("  Creating ticket templates...")

    for tmpl_data in TICKET_TEMPLATES:
        existing = db.query(models.TicketTemplate).filter(models.TicketTemplate.name == tmpl_data["name"]).first()
        if existing:
            continue

        template = models.TicketTemplate(
            name=tmpl_data["name"],
            title_template=tmpl_data["title"],
            description_template=tmpl_data["description"],
            ticket_type=tmpl_data["type"],
            priority=tmpl_data["priority"],
            category=tmpl_data["category"],
            is_active=True
        )
        db.add(template)

    db.commit()
    print(f"    Created {len(TICKET_TEMPLATES)} ticket templates")


def seed_tickets(db: Session, count: int = 35) -> None:
    """Create realistic tickets with SLA breaches and varied states."""
    print("  Creating tickets...")

    # Tickets with various scenarios including SLA breaches
    ticket_scenarios = [
        # === SLA BREACHED TICKETS ===
        {"title": "CRITICAL: Core switch CORE-SW-01 down", "type": "incident", "priority": "critical", "category": "Network", "status": "open", "sla_breached": True, "breach_hours": 4},
        {"title": "Production database unreachable", "type": "incident", "priority": "critical", "category": "Database", "status": "open", "sla_breached": True, "breach_hours": 3},
        {"title": "Major network outage affecting 50+ users", "type": "incident", "priority": "high", "category": "Network", "status": "open", "sla_breached": True, "breach_hours": 8},
        {"title": "Email server not responding", "type": "incident", "priority": "high", "category": "Infrastructure", "status": "pending", "sla_breached": True, "breach_hours": 6},
        {"title": "VPN gateway overloaded - remote workers affected", "type": "incident", "priority": "high", "category": "Network", "status": "open", "sla_breached": True, "breach_hours": 12},

        # === RESOLVED WITHIN SLA ===
        {"title": "Network connectivity issue - Lyon office", "type": "incident", "priority": "high", "category": "Network", "status": "resolved"},
        {"title": "Server ESX-PROD-02 memory alert", "type": "incident", "priority": "medium", "category": "Infrastructure", "status": "closed"},
        {"title": "Certificate expiring on LB-PROD-01", "type": "incident", "priority": "critical", "category": "Security", "status": "resolved"},
        {"title": "Storage capacity warning on SAN-PROD-01", "type": "incident", "priority": "medium", "category": "Storage", "status": "resolved"},
        {"title": "Firewall rule change for new application", "type": "change", "priority": "medium", "category": "Security", "status": "closed"},

        # === OPEN TICKETS (at risk of SLA breach) ===
        {"title": "VPN connection timeout for remote users", "type": "incident", "priority": "high", "category": "Network", "status": "open", "at_risk": True},
        {"title": "Backup job failed - BACKUP-APP-01", "type": "incident", "priority": "high", "category": "Backup", "status": "open"},
        {"title": "Performance degradation on database servers", "type": "incident", "priority": "high", "category": "Database", "status": "open", "at_risk": True},
        {"title": "Monitoring alerts not triggering correctly", "type": "incident", "priority": "medium", "category": "Monitoring", "status": "open"},
        {"title": "Disk space critical on BACKUP-SRV-01", "type": "incident", "priority": "high", "category": "Storage", "status": "open"},

        # === PENDING TICKETS ===
        {"title": "Request: New VM for marketing campaign", "type": "request", "priority": "medium", "category": "Infrastructure", "status": "pending"},
        {"title": "VLAN configuration for new department", "type": "change", "priority": "medium", "category": "Network", "status": "pending"},
        {"title": "Waiting for vendor - ESX-PROD-04 RAM replacement", "type": "incident", "priority": "medium", "category": "Hardware", "status": "pending"},

        # === NEW TICKETS ===
        {"title": "Request: Additional storage for dev environment", "type": "request", "priority": "low", "category": "Storage", "status": "new"},
        {"title": "Patch deployment - Windows servers", "type": "change", "priority": "medium", "category": "Infrastructure", "status": "new"},
        {"title": "New employee onboarding - A. Martin", "type": "request", "priority": "low", "category": "Onboarding", "status": "new"},
        {"title": "Access request for new contractor", "type": "request", "priority": "medium", "category": "Access", "status": "new"},

        # === CLOSED TICKETS ===
        {"title": "User password reset - unable to use self-service", "type": "request", "priority": "low", "category": "Access", "status": "closed"},
        {"title": "Printer offline in meeting room 3A", "type": "incident", "priority": "low", "category": "Hardware", "status": "closed"},
        {"title": "Software installation - Adobe Creative Suite", "type": "request", "priority": "low", "category": "Software", "status": "closed"},
        {"title": "Laptop screen replacement - J. Dupont", "type": "incident", "priority": "medium", "category": "Hardware", "status": "closed"},

        # === MORE INCIDENTS (various states) ===
        {"title": "WiFi dropping in conference rooms", "type": "incident", "priority": "medium", "category": "Network", "status": "open"},
        {"title": "Slow response from internal applications", "type": "incident", "priority": "medium", "category": "Infrastructure", "status": "open"},
        {"title": "Security scan detected vulnerabilities", "type": "incident", "priority": "high", "category": "Security", "status": "open"},
        {"title": "UPS battery warning - UPS-A1-R02", "type": "incident", "priority": "medium", "category": "Power", "status": "open"},

        # === CHANGE REQUESTS ===
        {"title": "Scheduled maintenance - Core router firmware", "type": "change", "priority": "high", "category": "Network", "status": "new"},
        {"title": "Database migration to new cluster", "type": "change", "priority": "high", "category": "Database", "status": "pending"},
        {"title": "Firewall rule audit and cleanup", "type": "change", "priority": "medium", "category": "Security", "status": "open"},

        # === PROBLEM MANAGEMENT ===
        {"title": "Recurring network drops in Building B", "type": "problem", "priority": "medium", "category": "Network", "status": "open"},
        {"title": "Root cause analysis - Recent storage failures", "type": "problem", "priority": "high", "category": "Storage", "status": "open"},
    ]

    # Get users by role for assignment
    tech_users = [u for u in store.users if u.role in ["tech", "admin", "superadmin"]]
    helpdesk_users = [u for u in store.users if u.role == "user"]
    all_users = tech_users + helpdesk_users

    sla_breached_count = 0
    at_risk_count = 0
    resolved_count = 0

    for i, scenario in enumerate(ticket_scenarios[:count]):
        requester = random.choice(all_users)
        assigned_to = random.choice(tech_users) if scenario["status"] not in ["new"] else None

        # Determine SLA times based on priority
        sla_hours = {"critical": 2, "high": 4, "medium": 8, "low": 24}.get(scenario["priority"], 8)

        # Handle SLA breached tickets
        if scenario.get("sla_breached"):
            breach_hours = scenario.get("breach_hours", 4)
            created_at = datetime.now(timezone.utc) - timedelta(hours=sla_hours + breach_hours)
            sla_due_date = created_at + timedelta(hours=sla_hours)  # SLA already passed
            sla_breached_count += 1
        elif scenario.get("at_risk"):
            # Ticket close to SLA breach (created near the SLA deadline)
            created_at = datetime.now(timezone.utc) - timedelta(hours=sla_hours - 1)
            sla_due_date = created_at + timedelta(hours=sla_hours)  # About to breach
            at_risk_count += 1
        else:
            created_at = random_datetime_past(30)
            sla_due_date = created_at + timedelta(hours=sla_hours)

        ticket = models.Ticket(
            title=scenario["title"],
            description=f"## Issue Description\n\n{scenario['title']}\n\n### Details\n\nThis is a test ticket generated for demonstration purposes.\n\n### Environment\n- Location: Paris DC1\n- Affected users: {'Critical - 50+' if scenario['priority'] == 'critical' else 'Multiple' if scenario['priority'] == 'high' else 'Limited'}",
            ticket_type=scenario["type"],
            status=scenario["status"],
            priority=scenario["priority"],
            category=scenario["category"],
            requester_id=requester.id,
            assigned_to_id=assigned_to.id if assigned_to else None,
            entity_id=store.entities[0].id if store.entities else None,
            created_at=created_at,
            updated_at=created_at + timedelta(hours=random.randint(1, 48)) if not scenario.get("sla_breached") else datetime.now(timezone.utc) - timedelta(hours=1),
            sla_due_date=sla_due_date,
            sla_breached=scenario.get("sla_breached", False)
        )

        if scenario["status"] in ["resolved", "closed"]:
            resolved_count += 1
            ticket.resolved_at = created_at + timedelta(hours=random.randint(1, sla_hours - 1))  # Resolved within SLA
            ticket.resolution = "Issue has been resolved. Root cause identified and fix applied."

        if scenario["status"] == "closed":
            ticket.closed_at = ticket.resolved_at + timedelta(hours=random.randint(1, 8))

        db.add(ticket)
        db.flush()

        # Add comments based on status
        if scenario["status"] not in ["new"]:
            comment = models.TicketComment(
                ticket_id=ticket.id,
                user_id=(assigned_to or requester).id,
                content="Initial investigation started. Checking system logs and monitoring dashboards." if not scenario.get("sla_breached") else "URGENT: Escalating to senior team. SLA breach in progress.",
                is_internal=False,
                created_at=created_at + timedelta(hours=1)
            )
            db.add(comment)

            if scenario.get("sla_breached"):
                # Add escalation comment for breached tickets
                escalation = models.TicketComment(
                    ticket_id=ticket.id,
                    user_id=tech_users[0].id,  # Manager
                    content="SLA BREACH ALERT: This ticket has exceeded the SLA deadline. Management has been notified. Please prioritize resolution.",
                    is_internal=True,
                    created_at=sla_due_date + timedelta(minutes=15)
                )
                db.add(escalation)

            if scenario["status"] in ["resolved", "closed"]:
                resolution_comment = models.TicketComment(
                    ticket_id=ticket.id,
                    user_id=(assigned_to or requester).id,
                    content="Issue resolved. Applied configuration changes and verified service is operational.",
                    is_internal=False,
                    is_resolution=True,
                    created_at=ticket.resolved_at
                )
                db.add(resolution_comment)

    db.commit()
    print(f"    Created {min(count, len(ticket_scenarios))} tickets:")
    print(f"      - SLA Breached: {sla_breached_count}")
    print(f"      - At Risk: {at_risk_count}")
    print(f"      - Resolved/Closed: {resolved_count}")


def seed_knowledge_articles(db: Session) -> None:
    """Create knowledge base articles."""
    print("  Creating knowledge articles...")

    author = store.users[0] if store.users else None
    if not author:
        return

    for article_data in KB_ARTICLES:
        existing = db.query(models.KnowledgeArticle).filter(models.KnowledgeArticle.slug == article_data["slug"]).first()
        if existing:
            continue

        article = models.KnowledgeArticle(
            title=article_data["title"],
            slug=article_data["slug"],
            category=article_data["category"],
            summary=article_data["summary"],
            content=article_data["content"],
            author_id=author.id,
            is_published=True,
            is_internal=article_data.get("is_internal", False),
            view_count=random.randint(10, 500),
            helpful_count=random.randint(5, 50),
            not_helpful_count=random.randint(0, 5),
            version=1,
            created_at=random_datetime_past(180),
            published_at=random_datetime_past(170)
        )
        db.add(article)

    db.commit()
    print(f"    Created {len(KB_ARTICLES)} knowledge articles")


def seed_notifications(db: Session) -> None:
    """Create comprehensive notifications covering all alert types."""
    print("  Creating notifications...")

    # Critical/Urgent notifications (unread, recent)
    critical_notifications = [
        {"type": "error", "title": "SLA BREACH: Critical ticket", "message": "Ticket 'CRITICAL: Core switch CORE-SW-01 down' has breached SLA. Immediate action required.", "link_type": "ticket"},
        {"type": "error", "title": "SLA BREACH: Database unreachable", "message": "Ticket 'Production database unreachable' has exceeded SLA deadline by 3 hours.", "link_type": "ticket"},
        {"type": "error", "title": "Contract Expired", "message": "Contract 'Cisco SmartNet Total Care' has expired. Equipment at risk without support.", "link_type": "contract"},
        {"type": "error", "title": "Contract Expired", "message": "Contract 'Fortinet FortiCare Premium' expired. Firewall support coverage ended.", "link_type": "contract"},
        {"type": "error", "title": "Warranty Expired", "message": "Equipment 'ESX-PROD-01' warranty has expired. Consider renewal or replacement.", "link_type": "equipment"},
        {"type": "error", "title": "Warranty Expired", "message": "Equipment 'UPS-A1-R02' warranty expired. No support coverage available.", "link_type": "equipment"},
    ]

    # Warning notifications (some unread)
    warning_notifications = [
        {"type": "warning", "title": "Contract Expiring Soon", "message": "Contract 'HPE Proactive Care 24x7' expires in 12 days. Start renewal process.", "link_type": "contract"},
        {"type": "warning", "title": "Contract Expiring Soon", "message": "Contract 'Dell ProSupport Plus' expires in 28 days. Contact vendor for renewal.", "link_type": "contract"},
        {"type": "warning", "title": "Warranty Expiring", "message": "Equipment 'MONITOR-SRV-01' warranty expires in 21 days.", "link_type": "equipment"},
        {"type": "warning", "title": "Warranty Expiring", "message": "Equipment 'ESX-DEV-02' warranty expiring soon. Schedule replacement planning.", "link_type": "equipment"},
        {"type": "warning", "title": "License Expiring", "message": "VMware vSphere license expires in 45 days. Contact VMware for renewal.", "link_type": "software"},
        {"type": "warning", "title": "Certificate Expiring", "message": "SSL certificate on LB-PROD-01 expires in 30 days. Schedule renewal.", "link_type": "equipment"},
        {"type": "warning", "title": "Storage Warning", "message": "SAN-PROD-01 capacity at 85%. Consider expanding or archiving old data.", "link_type": "equipment"},
        {"type": "warning", "title": "Equipment in Maintenance", "message": "ESX-PROD-04 scheduled for maintenance (RAM upgrade). Workloads migrated.", "link_type": "equipment"},
        {"type": "warning", "title": "SLA At Risk", "message": "Ticket 'VPN connection timeout' approaching SLA deadline in 1 hour.", "link_type": "ticket"},
    ]

    # Info notifications (mostly read)
    info_notifications = [
        {"type": "info", "title": "Backup Completed", "message": "Nightly backup completed successfully for all systems.", "link_type": None},
        {"type": "info", "title": "Scheduled Maintenance", "message": "Core router firmware upgrade scheduled for Sunday 02:00-04:00.", "link_type": "ticket"},
        {"type": "info", "title": "New Equipment Added", "message": "3 spare devices added to inventory: SPARE-SRV-01, SPARE-SW-01, SPARE-SW-02.", "link_type": "equipment"},
        {"type": "info", "title": "System Update", "message": "Inframate platform updated to version 2.0.0 with new features.", "link_type": None},
        {"type": "info", "title": "Weekly Report", "message": "Weekly IT metrics report available. 35 tickets processed, 92% SLA compliance.", "link_type": None},
    ]

    # Success notifications
    success_notifications = [
        {"type": "success", "title": "Patch Applied", "message": "Security patches applied to all Windows servers successfully.", "link_type": None},
        {"type": "success", "title": "Ticket Resolved", "message": "Ticket 'Network connectivity issue - Lyon office' resolved within SLA.", "link_type": "ticket"},
        {"type": "success", "title": "Equipment Deployed", "message": "New server ESX-PROD-04 successfully deployed and added to cluster.", "link_type": "equipment"},
        {"type": "success", "title": "Contract Renewed", "message": "Contract 'VMware Production Support' renewed for 2 years.", "link_type": "contract"},
    ]

    # Ticket notifications
    ticket_notifications = [
        {"type": "ticket", "title": "New Ticket Assigned", "message": "Ticket 'Backup job failed - BACKUP-APP-01' has been assigned to you.", "link_type": "ticket"},
        {"type": "ticket", "title": "Ticket Updated", "message": "Ticket 'VPN connection timeout for remote users' has new comments.", "link_type": "ticket"},
        {"type": "ticket", "title": "Ticket Escalated", "message": "Ticket 'Performance degradation on database servers' escalated to you.", "link_type": "ticket"},
        {"type": "ticket", "title": "High Priority Ticket", "message": "New high-priority ticket: 'Security scan detected vulnerabilities'.", "link_type": "ticket"},
    ]

    all_notifications = critical_notifications + warning_notifications + info_notifications + success_notifications + ticket_notifications

    # Distribute notifications to users based on role
    tech_users = [u for u in store.users if u.role in ["tech", "admin", "superadmin"]]
    all_active_users = [u for u in store.users if u.is_active]

    notification_count = 0

    # Admins/Superadmins get critical notifications
    for user in [u for u in store.users if u.role in ["admin", "superadmin"]]:
        for notif_data in critical_notifications:
            notif = models.Notification(
                user_id=user.id,
                notification_type=notif_data["type"],
                title=notif_data["title"],
                message=notif_data["message"],
                link_type=notif_data.get("link_type"),
                is_read=False,  # Critical notifications are unread
                created_at=random_datetime_past(3)  # Recent
            )
            db.add(notif)
            notification_count += 1

    # Tech users get warnings and tickets
    for user in tech_users:
        selected_warnings = random.sample(warning_notifications, min(4, len(warning_notifications)))
        for notif_data in selected_warnings:
            notif = models.Notification(
                user_id=user.id,
                notification_type=notif_data["type"],
                title=notif_data["title"],
                message=notif_data["message"],
                link_type=notif_data.get("link_type"),
                is_read=random.random() > 0.5,  # 50% unread
                created_at=random_datetime_past(7)
            )
            db.add(notif)
            notification_count += 1

        selected_tickets = random.sample(ticket_notifications, min(2, len(ticket_notifications)))
        for notif_data in selected_tickets:
            notif = models.Notification(
                user_id=user.id,
                notification_type=notif_data["type"],
                title=notif_data["title"],
                message=notif_data["message"],
                link_type=notif_data.get("link_type"),
                is_read=random.random() > 0.4,  # 40% unread
                created_at=random_datetime_past(5)
            )
            db.add(notif)
            notification_count += 1

    # All users get info and success notifications
    for user in all_active_users:
        selected_info = random.sample(info_notifications + success_notifications, min(3, len(info_notifications) + len(success_notifications)))
        for notif_data in selected_info:
            notif = models.Notification(
                user_id=user.id,
                notification_type=notif_data["type"],
                title=notif_data["title"],
                message=notif_data["message"],
                link_type=notif_data.get("link_type"),
                is_read=random.random() > 0.3,  # 30% unread
                created_at=random_datetime_past(14)
            )
            db.add(notif)
            notification_count += 1

    db.commit()
    print(f"    Created {notification_count} notifications")
    print(f"      - Critical alerts: {len(critical_notifications)} per admin")
    print(f"      - Warnings: {len(warning_notifications)} available")
    print(f"      - Ticket alerts: {len(ticket_notifications)} distributed")


def clean_test_data(db: Session) -> None:
    """Remove all test data."""
    print("Cleaning existing data...")

    tables = [
        models.WebhookDelivery,
        models.Webhook,
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
        models.Attachment,
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
            if deleted > 0:
                print(f"  Deleted {deleted} from {table.__tablename__}")
        except Exception as e:
            print(f"  Warning: {table.__tablename__}: {e}")
            db.rollback()

    # Delete test users (keep admin)
    deleted_users = db.query(models.User).filter(
        models.User.username.in_([u["username"] for u in IT_TEAM])
    ).delete(synchronize_session=False)
    if deleted_users > 0:
        print(f"  Deleted {deleted_users} test users")

    db.commit()
    print("Cleanup complete!\n")


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Seed realistic infrastructure data")
    parser.add_argument("--clean", action="store_true", help="Remove existing data first")
    parser.add_argument("--minimal", action="store_true", help="Single DC only (faster)")
    args = parser.parse_args()

    print("=" * 70)
    print("TechCorp Infrastructure Seeder")
    print("=" * 70)
    print(f"Mode: {'Minimal (Paris DC only)' if args.minimal else 'Full (Paris DC + Lyon DR)'}")
    print()

    db = SessionLocal()

    try:
        if args.clean:
            clean_test_data(db)

        print("Creating TechCorp infrastructure...")
        print()

        # Core setup
        seed_users(db)
        seed_entities(db)
        seed_locations(db, args.minimal)
        seed_manufacturers(db)
        seed_suppliers(db)
        seed_equipment_types(db)
        seed_equipment_models(db)

        # Infrastructure
        seed_racks(db, args.minimal)
        seed_subnets(db)
        seed_network_infrastructure(db, args.minimal)
        seed_server_infrastructure(db, args.minimal)
        seed_network_ports_and_connections(db)
        seed_additional_ips(db)
        seed_pdus(db)

        # Assets & Contracts
        seed_software(db)
        seed_contracts(db)

        # Helpdesk & KB
        seed_sla_policies(db)
        seed_ticket_templates(db)
        seed_tickets(db)
        seed_knowledge_articles(db)
        seed_notifications(db)

        print()
        print("=" * 70)
        print("Infrastructure seeding complete!")
        print("=" * 70)
        print()
        print("Summary:")
        print(f"  - {len(store.equipment)} equipment items")
        print(f"  - {len(store.racks)} racks")
        print(f"  - {len(store.subnets)} subnets (VLANs)")
        print(f"  - {len(store.ip_addresses)} IP addresses")
        print(f"  - {len(store.ports)} network ports")
        print(f"  - {len(store.contracts)} contracts")
        print(f"  - {len(store.software)} software entries")
        print()
        print("Test users (password: TechCorp2024!):")
        for user in IT_TEAM:
            print(f"  - {user['username']} ({user['role']}) - {user['full_name']}")
        print()

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
