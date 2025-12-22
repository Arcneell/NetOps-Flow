# NetOps Flow

A self-hosted NetDevOps platform for network operations management, featuring IP Address Management (IPAM) and script automation capabilities.

## Features

### IPAM (IP Address Management)
- Create and manage subnets with CIDR validation
- Allocate and track IP addresses within subnets
- Automatic subnet scanning using nmap to discover active hosts
- Track IP address status (active/available), hostname, and MAC address

### Script Runner
- Upload and manage Python (`.py`) and Bash (`.sh`) scripts
- Execute scripts locally on the server or remotely via SSH/WinRM
- Support for script arguments
- Real-time capture of stdout/stderr logs
- Execution status tracking (pending, running, success, failure, cancelled)
- Ability to stop running executions

### Network Topology
- Visual network topology display showing subnets and IP addresses
- Color-coded visualization (green for active IPs, gray for available)

### Dashboard
- Statistics overview: total subnets, active IPs, scripts, and executions
- System status monitoring
- Quick action buttons for common tasks

### User Management
- User authentication with JWT tokens
- Role-based access control (admin/user)
- Granular permissions (IPAM, Topology, Scripts, Settings)

## Architecture

- **Backend**: FastAPI (Python 3.11)
- **Worker**: Celery + Redis
- **Database**: PostgreSQL 15
- **Frontend**: Vue.js 3 + TailwindCSS + PrimeVue

## Getting Started

1. Ensure Docker and Docker Compose are installed.
2. Run the stack:
   ```bash
   docker-compose up --build
   ```

3. Access the services:
   - **Frontend**: http://localhost:3000
   - **API Docs**: http://localhost:8000/docs

## Default Credentials

### Application Login
- **Username**: `admin`
- **Password**: `admin`

### Database
- **Username**: `netops`
- **Password**: `netopspassword`
- **Database**: `netops_flow`

> **Important**: Change the default credentials immediately after installation for security purposes.
