import os
import subprocess
import datetime
import logging
import socket
import base64
import nmap
import paramiko
import winrm
from celery import Celery
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models import ScriptExecution, Subnet, IPAddress, Server

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration Celery
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery("netops_worker", broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)

# Security and configuration constants
SCRIPTS_DIR = "/scripts_storage"
SSH_TIMEOUT = 30  # seconds
SSH_BANNER_TIMEOUT = 30  # seconds
WINRM_TIMEOUT = 60  # seconds
SCRIPT_EXECUTION_TIMEOUT = 300  # 5 minutes
MAX_OUTPUT_SIZE = 1024 * 1024  # 1MB max output


def truncate_output(output: str, max_size: int = MAX_OUTPUT_SIZE) -> str:
    """Truncate output if it exceeds max size."""
    if len(output) > max_size:
        return output[:max_size] + "\n\n[Output truncated - exceeded maximum size]"
    return output


def run_local(cmd):
    """Execute a command locally with proper error handling."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=SCRIPT_EXECUTION_TIMEOUT,
            cwd="/tmp"  # Run in a safe directory
        )
        stdout = truncate_output(result.stdout)
        stderr = truncate_output(result.stderr)
        return result.returncode, stdout, stderr
    except subprocess.TimeoutExpired:
        logger.warning(f"Script execution timed out: {cmd}")
        return -1, "", "Script execution timed out after 5 minutes."
    except FileNotFoundError as e:
        logger.error(f"Interpreter not found: {e}")
        return -1, "", f"Interpreter not found: {str(e)}"
    except PermissionError as e:
        logger.error(f"Permission denied: {e}")
        return -1, "", f"Permission denied: {str(e)}"
    except Exception as e:
        logger.error(f"Local execution error: {e}")
        return -1, "", f"Execution error: {str(e)}"


def run_ssh_with_args(server, file_path, script_type, args_str):
    """Execute a script on a remote server via SSH with proper error handling."""
    client = paramiko.SSHClient()
    # Note: AutoAddPolicy is used for simplicity. In production, consider using
    # known_hosts file validation or a custom policy
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Validate connection parameters
        if not server.ip_address or not server.username:
            return -1, "", "SSH Error: Missing server IP or username"

        # Attempt connection
        logger.info(f"Connecting to {server.ip_address}:{server.port} via SSH")
        client.connect(
            hostname=server.ip_address,
            port=server.port,
            username=server.username,
            password=server.password,
            timeout=SSH_TIMEOUT,
            banner_timeout=SSH_BANNER_TIMEOUT,
            auth_timeout=SSH_TIMEOUT,
            allow_agent=False,
            look_for_keys=False
        )

        # Upload script
        sftp = client.open_sftp()
        remote_filename = os.path.basename(file_path)
        # Sanitize remote filename
        remote_filename = "".join(c for c in remote_filename if c.isalnum() or c in "._-")
        remote_path = f"/tmp/{remote_filename}"

        logger.info(f"Uploading script to {remote_path}")
        sftp.put(file_path, remote_path)
        sftp.chmod(remote_path, 0o700)  # Make executable
        sftp.close()

        # Build execution command
        if script_type == "python":
            command = f"python3 {remote_path}{args_str}"
        elif script_type == "bash":
            command = f"bash {remote_path}{args_str}"
        elif script_type == "powershell":
            command = f"pwsh {remote_path}{args_str}"
        else:
            command = f"{remote_path}{args_str}"

        logger.info(f"Executing: {command}")
        stdin, stdout, stderr = client.exec_command(
            command,
            timeout=SCRIPT_EXECUTION_TIMEOUT
        )

        # Wait for completion
        exit_status = stdout.channel.recv_exit_status()
        out = truncate_output(stdout.read().decode('utf-8', errors='replace'))
        err = truncate_output(stderr.read().decode('utf-8', errors='replace'))

        # Cleanup remote file
        try:
            cleanup_client = client.open_sftp()
            cleanup_client.remove(remote_path)
            cleanup_client.close()
        except Exception:
            pass  # Best effort cleanup

        client.close()
        logger.info(f"SSH execution completed with exit code: {exit_status}")
        return exit_status, out, err

    except socket.timeout:
        logger.error(f"SSH connection timeout to {server.ip_address}")
        return -1, "", f"SSH Error: Connection timed out to {server.ip_address}"
    except paramiko.AuthenticationException:
        logger.error(f"SSH authentication failed for {server.ip_address}")
        return -1, "", "SSH Error: Authentication failed. Check username/password."
    except paramiko.SSHException as e:
        logger.error(f"SSH error: {e}")
        return -1, "", f"SSH Error: {str(e)}"
    except socket.error as e:
        logger.error(f"Socket error connecting to {server.ip_address}: {e}")
        return -1, "", f"SSH Error: Cannot connect to {server.ip_address}:{server.port} - {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected SSH error: {e}")
        return -1, "", f"SSH Error: {str(e)}"
    finally:
        try:
            client.close()
        except Exception:
            pass


def run_winrm_with_args(server, file_path, script_args=None):
    """Execute a PowerShell script on a remote Windows server via WinRM."""
    try:
        # Read script content
        with open(file_path, 'r', encoding='utf-8') as f:
            script_content = f.read()

        # Validate server
        if not server.ip_address or not server.username:
            return -1, "", "WinRM Error: Missing server IP or username"

        # Determine WinRM port and transport
        port = server.port if server.port else 5985
        use_ssl = port == 5986

        logger.info(f"Connecting to {server.ip_address}:{port} via WinRM (SSL: {use_ssl})")

        # Create session
        if use_ssl:
            session = winrm.Session(
                f'https://{server.ip_address}:{port}/wsman',
                auth=(server.username, server.password),
                transport='ntlm',
                server_cert_validation='ignore'
            )
        else:
            session = winrm.Session(
                f'http://{server.ip_address}:{port}/wsman',
                auth=(server.username, server.password),
                transport='ntlm'
            )

        # Prepare script with arguments
        if script_args:
            args_block = " ".join([f'"{arg}"' for arg in script_args])
            ps_script = f"$args = @({args_block})\n$ProgressPreference = 'SilentlyContinue'\n{script_content}"
        else:
            ps_script = f"$ProgressPreference = 'SilentlyContinue'\n{script_content}"

        logger.info("Executing PowerShell script via WinRM")
        result = session.run_ps(ps_script)

        stdout = truncate_output(result.std_out.decode('utf-8', errors='replace'))
        stderr = truncate_output(result.std_err.decode('utf-8', errors='replace'))

        logger.info(f"WinRM execution completed with status: {result.status_code}")
        return result.status_code, stdout, stderr

    except FileNotFoundError:
        logger.error(f"Script file not found: {file_path}")
        return -1, "", f"WinRM Error: Script file not found"
    except winrm.exceptions.WinRMTransportError as e:
        logger.error(f"WinRM transport error: {e}")
        return -1, "", f"WinRM Error: Cannot connect to {server.ip_address}. Ensure WinRM is enabled and accessible."
    except winrm.exceptions.InvalidCredentialsError:
        logger.error(f"WinRM authentication failed for {server.ip_address}")
        return -1, "", "WinRM Error: Authentication failed. Check username/password."
    except Exception as e:
        logger.error(f"WinRM error: {e}")
        return -1, "", f"WinRM Error: {str(e)}"


@celery_app.task(bind=True)
def execute_script_task(self, execution_id: int, filename: str, script_type: str, server_id: int = None, script_args: list = None):
    """Execute a script locally or on a remote server."""
    db: Session = SessionLocal()
    try:
        execution = db.query(ScriptExecution).filter(ScriptExecution.id == execution_id).first()

        if not execution:
            logger.error(f"Execution {execution_id} not found")
            return "Execution not found"

        execution.status = "running"
        db.commit()

        file_path = os.path.join(SCRIPTS_DIR, filename)

        # Security check: ensure file is within scripts directory
        real_path = os.path.realpath(file_path)
        if not real_path.startswith(os.path.realpath(SCRIPTS_DIR)):
            execution.status = "failure"
            execution.stderr = "Security error: Invalid file path"
            execution.completed_at = datetime.datetime.utcnow()
            db.commit()
            logger.warning(f"Attempted path traversal attack: {filename}")
            return "Security error"

        if not os.path.exists(file_path):
            execution.status = "failure"
            execution.stderr = f"File not found: {filename}"
            execution.completed_at = datetime.datetime.utcnow()
            db.commit()
            return "File not found"

        # Prepare arguments string for SSH (sanitized in main.py)
        args_str = ""
        if script_args:
            args_str = " " + " ".join([f'"{arg}"' for arg in script_args])

        return_code = 0
        stdout = ""
        stderr = ""

        if server_id:
            server = db.query(Server).filter(Server.id == server_id).first()
            if not server:
                stderr = "Target server not found in database"
                return_code = -1
            else:
                logger.info(f"Executing script on remote server: {server.name} ({server.ip_address})")
                if server.connection_type == "ssh":
                    return_code, stdout, stderr = run_ssh_with_args(server, file_path, script_type, args_str)
                elif server.connection_type == "winrm":
                    return_code, stdout, stderr = run_winrm_with_args(server, file_path, script_args)
                else:
                    stderr = f"Unknown connection type: {server.connection_type}"
                    return_code = -1
        else:
            # LOCAL EXECUTION
            logger.info(f"Executing script locally: {filename}")
            cmd = []
            if script_type == "python":
                cmd = ["python3", file_path]
            elif script_type == "bash":
                cmd = ["bash", file_path]
            elif script_type == "powershell":
                cmd = ["pwsh", "-File", file_path]
            else:
                cmd = [file_path]

            if script_args:
                cmd.extend(script_args)

            return_code, stdout, stderr = run_local(cmd)

        execution.stdout = stdout
        execution.stderr = stderr
        execution.status = "success" if return_code == 0 else "failure"
        execution.completed_at = datetime.datetime.utcnow()
        db.commit()

        logger.info(f"Execution {execution_id} completed with status: {execution.status}")
        return execution.status

    except Exception as e:
        logger.error(f"Unexpected error in execute_script_task: {e}")
        try:
            execution.status = "failure"
            execution.stderr = f"Unexpected error: {str(e)}"
            execution.completed_at = datetime.datetime.utcnow()
            db.commit()
        except Exception:
            pass
        return "failure"
    finally:
        db.close()


@celery_app.task(bind=True)
def scan_subnet_task(self, subnet_id: int):
    """Scan a subnet for active hosts using nmap."""
    db: Session = SessionLocal()
    try:
        subnet = db.query(Subnet).filter(Subnet.id == subnet_id).first()

        if not subnet:
            logger.error(f"Subnet {subnet_id} not found")
            return "Subnet not found"

        logger.info(f"Starting scan for subnet: {subnet.cidr}")
        nm = nmap.PortScanner()

        try:
            # Use ARP ping scan for local networks, ICMP otherwise
            nm.scan(hosts=str(subnet.cidr), arguments='-sn -PR -R --max-retries 2')
        except nmap.PortScannerError as e:
            logger.error(f"Nmap scan error: {e}")
            return f"Scan failed: {str(e)}"
        except Exception as e:
            logger.error(f"Scan error: {e}")
            return f"Scan failed: {str(e)}"

        scanned_hosts = nm.all_hosts()
        logger.info(f"Found {len(scanned_hosts)} hosts in {subnet.cidr}")

        for host in scanned_hosts:
            status = 'active' if nm[host].state() == 'up' else 'available'
            hostname = nm[host].hostname() if nm[host].hostname() else None
            mac = None
            if 'addresses' in nm[host] and 'mac' in nm[host]['addresses']:
                mac = nm[host]['addresses']['mac']

            existing_ip = db.query(IPAddress).filter(
                IPAddress.subnet_id == subnet_id,
                IPAddress.address == host
            ).first()

            if existing_ip:
                existing_ip.status = status
                existing_ip.last_scanned_at = datetime.datetime.utcnow()
                if hostname:
                    existing_ip.hostname = hostname
                if mac:
                    existing_ip.mac_address = mac
            else:
                new_ip = IPAddress(
                    address=host,
                    subnet_id=subnet_id,
                    status=status,
                    hostname=hostname,
                    mac_address=mac,
                    last_scanned_at=datetime.datetime.utcnow()
                )
                db.add(new_ip)

        db.commit()
        logger.info(f"Scan complete for {subnet.cidr}")
        return f"Scan complete for {subnet.cidr}. Found {len(scanned_hosts)} hosts."

    except Exception as e:
        logger.error(f"Unexpected error in scan_subnet_task: {e}")
        return f"Scan failed: {str(e)}"
    finally:
        db.close()
