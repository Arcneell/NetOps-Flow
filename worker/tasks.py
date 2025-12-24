"""
Celery Worker Tasks with Docker Sandboxing.
Provides secure script execution in ephemeral containers.
"""
import os
import subprocess
import datetime
import logging
import socket
import json
import tempfile
import uuid
from typing import Optional, Tuple, List

import nmap
import paramiko
import winrm
from celery import Celery
from sqlalchemy.orm import Session

# Structured logging
logger = logging.getLogger(__name__)


def get_json_logger():
    """Get JSON-formatted logger for structured logging."""
    return logger


# Configuration from environment
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery("netops_worker", broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)

# Configuration
SCRIPTS_DIR = os.environ.get("SCRIPTS_DIR", "/scripts_storage")
SSH_TIMEOUT = int(os.environ.get("SSH_TIMEOUT", "30"))
SSH_BANNER_TIMEOUT = int(os.environ.get("SSH_BANNER_TIMEOUT", "30"))
WINRM_TIMEOUT = int(os.environ.get("WINRM_TIMEOUT", "60"))
SCRIPT_EXECUTION_TIMEOUT = int(os.environ.get("SCRIPT_EXECUTION_TIMEOUT", "300"))
MAX_OUTPUT_SIZE = int(os.environ.get("MAX_OUTPUT_SIZE", str(1024 * 1024)))

# Docker Sandboxing Configuration
DOCKER_SANDBOX_ENABLED = os.environ.get("DOCKER_SANDBOX_ENABLED", "true").lower() == "true"
DOCKER_SANDBOX_IMAGE = os.environ.get("DOCKER_SANDBOX_IMAGE", "netops-sandbox:latest")
DOCKER_SANDBOX_MEMORY = os.environ.get("DOCKER_SANDBOX_MEMORY", "256m")
DOCKER_SANDBOX_CPU = float(os.environ.get("DOCKER_SANDBOX_CPU", "0.5"))
DOCKER_SANDBOX_NETWORK = os.environ.get("DOCKER_SANDBOX_NETWORK", "none")


def log_event(event_type: str, **kwargs):
    """Log structured event."""
    log_data = {
        "event_type": event_type,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        **kwargs
    }
    logger.info(json.dumps(log_data))


def truncate_output(output: str, max_size: int = MAX_OUTPUT_SIZE) -> str:
    """Truncate output if it exceeds max size."""
    if len(output) > max_size:
        return output[:max_size] + "\n\n[Output truncated - exceeded maximum size]"
    return output


class DockerSandbox:
    """
    Docker-based sandbox for script execution.
    Provides isolation using ephemeral containers.
    """

    def __init__(self):
        self._client = None

    @property
    def client(self):
        """Lazy initialization of Docker client."""
        if self._client is None:
            try:
                import docker
                self._client = docker.from_env()
            except Exception as e:
                logger.error(f"Failed to initialize Docker client: {e}")
                raise RuntimeError("Docker is not available for sandboxing")
        return self._client

    def is_available(self) -> bool:
        """Check if Docker is available."""
        try:
            self.client.ping()
            return True
        except Exception:
            return False

    def ensure_sandbox_image(self) -> bool:
        """Ensure sandbox image exists, build if necessary."""
        try:
            self.client.images.get(DOCKER_SANDBOX_IMAGE)
            return True
        except Exception:
            logger.warning(f"Sandbox image {DOCKER_SANDBOX_IMAGE} not found, attempting to build...")
            return self._build_sandbox_image()

    def _build_sandbox_image(self) -> bool:
        """Build the sandbox image."""
        dockerfile_content = '''
FROM python:3.11-slim

# Install interpreters
RUN apt-get update && apt-get install -y --no-install-recommends \\
    bash \\
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for script execution
RUN useradd -m -s /bin/bash sandbox
USER sandbox
WORKDIR /workspace

# Default command
CMD ["/bin/bash"]
'''
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                dockerfile_path = os.path.join(tmpdir, "Dockerfile")
                with open(dockerfile_path, "w") as f:
                    f.write(dockerfile_content)

                self.client.images.build(
                    path=tmpdir,
                    tag=DOCKER_SANDBOX_IMAGE,
                    rm=True
                )
            logger.info(f"Built sandbox image: {DOCKER_SANDBOX_IMAGE}")
            return True
        except Exception as e:
            logger.error(f"Failed to build sandbox image: {e}")
            return False

    def execute(
        self,
        script_path: str,
        script_type: str,
        args: Optional[List[str]] = None,
        timeout: int = SCRIPT_EXECUTION_TIMEOUT
    ) -> Tuple[int, str, str]:
        """
        Execute a script in a sandboxed Docker container.

        Args:
            script_path: Path to the script file
            script_type: Type of script (python, bash, powershell)
            args: Script arguments
            timeout: Execution timeout in seconds

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        container = None
        container_name = f"sandbox-{uuid.uuid4().hex[:12]}"

        try:
            # Ensure image exists
            if not self.ensure_sandbox_image():
                return -1, "", "Sandbox image not available"

            # Prepare command
            if script_type == "python":
                cmd = ["python3", "/workspace/script.py"]
            elif script_type == "bash":
                cmd = ["bash", "/workspace/script.sh"]
            else:
                cmd = ["/workspace/script"]

            if args:
                cmd.extend(args)

            log_event(
                "sandbox_execution_start",
                container_name=container_name,
                script_type=script_type,
                timeout=timeout
            )

            # Create container
            container = self.client.containers.create(
                image=DOCKER_SANDBOX_IMAGE,
                name=container_name,
                command=cmd,
                volumes={
                    script_path: {
                        "bind": f"/workspace/script.{self._get_extension(script_type)}",
                        "mode": "ro"
                    }
                },
                mem_limit=DOCKER_SANDBOX_MEMORY,
                cpu_period=100000,
                cpu_quota=int(100000 * DOCKER_SANDBOX_CPU),
                network_mode=DOCKER_SANDBOX_NETWORK,
                user="sandbox",
                read_only=True,
                tmpfs={"/tmp": "size=64M,mode=1777"},
                security_opt=["no-new-privileges"],
                cap_drop=["ALL"],
                detach=True
            )

            # Start and wait for completion
            container.start()
            result = container.wait(timeout=timeout)

            # Get logs
            stdout = container.logs(stdout=True, stderr=False).decode('utf-8', errors='replace')
            stderr = container.logs(stdout=False, stderr=True).decode('utf-8', errors='replace')

            exit_code = result.get("StatusCode", -1)

            log_event(
                "sandbox_execution_complete",
                container_name=container_name,
                exit_code=exit_code,
                stdout_size=len(stdout),
                stderr_size=len(stderr)
            )

            return exit_code, truncate_output(stdout), truncate_output(stderr)

        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)

            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                log_event(
                    "sandbox_execution_timeout",
                    container_name=container_name,
                    timeout=timeout
                )
                return -1, "", f"Script execution timed out after {timeout} seconds"

            log_event(
                "sandbox_execution_error",
                container_name=container_name,
                error_type=error_type,
                error_message=error_msg
            )
            return -1, "", f"Sandbox execution error: {error_msg}"

        finally:
            # Cleanup container
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass

    def _get_extension(self, script_type: str) -> str:
        """Get file extension for script type."""
        extensions = {
            "python": "py",
            "bash": "sh",
            "powershell": "ps1"
        }
        return extensions.get(script_type, "sh")


# Global sandbox instance
_sandbox: Optional[DockerSandbox] = None


def get_sandbox() -> DockerSandbox:
    """Get or create sandbox instance."""
    global _sandbox
    if _sandbox is None:
        _sandbox = DockerSandbox()
    return _sandbox


def run_local(cmd: List[str]) -> Tuple[int, str, str]:
    """Execute a command locally with proper error handling."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=SCRIPT_EXECUTION_TIMEOUT,
            cwd="/tmp"
        )
        stdout = truncate_output(result.stdout)
        stderr = truncate_output(result.stderr)
        return result.returncode, stdout, stderr
    except subprocess.TimeoutExpired:
        log_event("local_execution_timeout", command=cmd[0], timeout=SCRIPT_EXECUTION_TIMEOUT)
        return -1, "", f"Script execution timed out after {SCRIPT_EXECUTION_TIMEOUT} seconds."
    except FileNotFoundError as e:
        log_event("local_execution_error", error_type="FileNotFoundError", message=str(e))
        return -1, "", f"Interpreter not found: {str(e)}"
    except PermissionError as e:
        log_event("local_execution_error", error_type="PermissionError", message=str(e))
        return -1, "", f"Permission denied: {str(e)}"
    except Exception as e:
        log_event("local_execution_error", error_type=type(e).__name__, message=str(e))
        return -1, "", f"Execution error: {str(e)}"


def run_ssh_with_args(
    equipment,
    file_path: str,
    script_type: str,
    args_str: str
) -> Tuple[int, str, str]:
    """Execute a script on a remote server via SSH."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    port = equipment.remote_port or 22
    remote_ip = equipment.remote_ip
    username = equipment.remote_username

    # Decrypt password if encrypted
    password = equipment.remote_password
    try:
        from backend.core.security import decrypt_value
        password = decrypt_value(password)
    except Exception:
        pass  # Use password as-is if decryption fails

    try:
        if not remote_ip or not username:
            return -1, "", "SSH Error: Missing equipment IP or username"

        log_event(
            "ssh_connection_start",
            host=remote_ip,
            port=port,
            username=username
        )

        client.connect(
            hostname=remote_ip,
            port=port,
            username=username,
            password=password,
            timeout=SSH_TIMEOUT,
            banner_timeout=SSH_BANNER_TIMEOUT,
            auth_timeout=SSH_TIMEOUT,
            allow_agent=False,
            look_for_keys=False
        )

        # Upload script
        sftp = client.open_sftp()
        remote_filename = os.path.basename(file_path)
        remote_filename = "".join(c for c in remote_filename if c.isalnum() or c in "._-")
        remote_path = f"/tmp/{remote_filename}"

        sftp.put(file_path, remote_path)
        sftp.chmod(remote_path, 0o700)
        sftp.close()

        # Build command
        if script_type == "python":
            command = f"python3 {remote_path}{args_str}"
        elif script_type == "bash":
            command = f"bash {remote_path}{args_str}"
        elif script_type == "powershell":
            command = f"pwsh {remote_path}{args_str}"
        else:
            command = f"{remote_path}{args_str}"

        log_event("ssh_command_execute", command=command)

        stdin, stdout, stderr = client.exec_command(
            command,
            timeout=SCRIPT_EXECUTION_TIMEOUT
        )

        exit_status = stdout.channel.recv_exit_status()
        out = truncate_output(stdout.read().decode('utf-8', errors='replace'))
        err = truncate_output(stderr.read().decode('utf-8', errors='replace'))

        # Cleanup
        try:
            cleanup_client = client.open_sftp()
            cleanup_client.remove(remote_path)
            cleanup_client.close()
        except Exception:
            pass

        client.close()

        log_event(
            "ssh_execution_complete",
            host=remote_ip,
            exit_code=exit_status
        )

        return exit_status, out, err

    except socket.timeout:
        log_event("ssh_connection_timeout", host=remote_ip, timeout=SSH_TIMEOUT)
        return -1, "", f"SSH Error: Connection timed out to {remote_ip}"
    except paramiko.AuthenticationException:
        log_event("ssh_auth_failed", host=remote_ip)
        return -1, "", "SSH Error: Authentication failed. Check username/password."
    except paramiko.SSHException as e:
        log_event("ssh_error", host=remote_ip, error=str(e))
        return -1, "", f"SSH Error: {str(e)}"
    except socket.error as e:
        log_event("ssh_socket_error", host=remote_ip, error=str(e))
        return -1, "", f"SSH Error: Cannot connect to {remote_ip}:{port} - {str(e)}"
    except Exception as e:
        log_event("ssh_unexpected_error", host=remote_ip, error=str(e))
        return -1, "", f"SSH Error: {str(e)}"
    finally:
        try:
            client.close()
        except Exception:
            pass


def run_winrm_with_args(
    equipment,
    file_path: str,
    script_args: Optional[List[str]] = None
) -> Tuple[int, str, str]:
    """Execute a PowerShell script via WinRM."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            script_content = f.read()

        if not equipment.remote_ip or not equipment.remote_username:
            return -1, "", "WinRM Error: Missing equipment IP or username"

        port = equipment.remote_port or 5985
        use_ssl = port == 5986

        # Decrypt password
        password = equipment.remote_password
        try:
            from backend.core.security import decrypt_value
            password = decrypt_value(password)
        except Exception:
            pass

        log_event(
            "winrm_connection_start",
            host=equipment.remote_ip,
            port=port,
            ssl=use_ssl
        )

        if use_ssl:
            session = winrm.Session(
                f'https://{equipment.remote_ip}:{port}/wsman',
                auth=(equipment.remote_username, password),
                transport='ntlm',
                server_cert_validation='ignore'
            )
        else:
            session = winrm.Session(
                f'http://{equipment.remote_ip}:{port}/wsman',
                auth=(equipment.remote_username, password),
                transport='ntlm'
            )

        # Prepare script
        if script_args:
            args_block = " ".join([f'"{arg}"' for arg in script_args])
            ps_script = f"$args = @({args_block})\n$ProgressPreference = 'SilentlyContinue'\n{script_content}"
        else:
            ps_script = f"$ProgressPreference = 'SilentlyContinue'\n{script_content}"

        result = session.run_ps(ps_script)

        stdout = truncate_output(result.std_out.decode('utf-8', errors='replace'))
        stderr = truncate_output(result.std_err.decode('utf-8', errors='replace'))

        log_event(
            "winrm_execution_complete",
            host=equipment.remote_ip,
            exit_code=result.status_code
        )

        return result.status_code, stdout, stderr

    except FileNotFoundError:
        log_event("winrm_file_not_found", path=file_path)
        return -1, "", "WinRM Error: Script file not found"
    except winrm.exceptions.WinRMTransportError as e:
        log_event("winrm_transport_error", host=equipment.remote_ip, error=str(e))
        return -1, "", f"WinRM Error: Cannot connect to {equipment.remote_ip}. Ensure WinRM is enabled."
    except winrm.exceptions.InvalidCredentialsError:
        log_event("winrm_auth_failed", host=equipment.remote_ip)
        return -1, "", "WinRM Error: Authentication failed. Check username/password."
    except Exception as e:
        log_event("winrm_error", host=equipment.remote_ip, error=str(e))
        return -1, "", f"WinRM Error: {str(e)}"


@celery_app.task(bind=True)
def execute_script_task(
    self,
    execution_id: int,
    filename: str,
    script_type: str,
    equipment_id: int = None,
    script_args: list = None
):
    """Execute a script locally (sandboxed) or on remote equipment."""
    from backend.core.database import SessionLocal
    from backend.models import ScriptExecution, Equipment

    db: Session = SessionLocal()
    try:
        execution = db.query(ScriptExecution).filter(
            ScriptExecution.id == execution_id
        ).first()

        if not execution:
            log_event("execution_not_found", execution_id=execution_id)
            return "Execution not found"

        execution.status = "running"
        db.commit()

        file_path = os.path.join(SCRIPTS_DIR, filename)

        # Security check
        real_path = os.path.realpath(file_path)
        if not real_path.startswith(os.path.realpath(SCRIPTS_DIR)):
            execution.status = "failure"
            execution.stderr = "Security error: Invalid file path"
            execution.completed_at = datetime.datetime.utcnow()
            db.commit()
            log_event("path_traversal_attempt", filename=filename)
            return "Security error"

        if not os.path.exists(file_path):
            execution.status = "failure"
            execution.stderr = f"File not found: {filename}"
            execution.completed_at = datetime.datetime.utcnow()
            db.commit()
            return "File not found"

        args_str = ""
        if script_args:
            args_str = " " + " ".join([f'"{arg}"' for arg in script_args])

        return_code = 0
        stdout = ""
        stderr = ""

        if equipment_id:
            # Remote execution
            equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
            if not equipment:
                stderr = "Target equipment not found in database"
                return_code = -1
            else:
                log_event(
                    "remote_execution_start",
                    equipment_name=equipment.name,
                    equipment_ip=equipment.remote_ip,
                    connection_type=equipment.connection_type
                )

                if equipment.connection_type == "ssh":
                    return_code, stdout, stderr = run_ssh_with_args(
                        equipment, file_path, script_type, args_str
                    )
                elif equipment.connection_type == "winrm":
                    return_code, stdout, stderr = run_winrm_with_args(
                        equipment, file_path, script_args
                    )
                else:
                    stderr = f"Unknown connection type: {equipment.connection_type}"
                    return_code = -1
        else:
            # Local execution - use Docker sandbox if available
            log_event("local_execution_start", filename=filename, sandboxed=DOCKER_SANDBOX_ENABLED)

            if DOCKER_SANDBOX_ENABLED:
                try:
                    sandbox = get_sandbox()
                    if sandbox.is_available():
                        return_code, stdout, stderr = sandbox.execute(
                            file_path, script_type, script_args
                        )
                    else:
                        log_event("sandbox_unavailable", fallback="direct_execution")
                        # Fallback to direct execution
                        return_code, stdout, stderr = _execute_directly(
                            file_path, script_type, script_args
                        )
                except Exception as e:
                    log_event("sandbox_error", error=str(e), fallback="direct_execution")
                    return_code, stdout, stderr = _execute_directly(
                        file_path, script_type, script_args
                    )
            else:
                return_code, stdout, stderr = _execute_directly(
                    file_path, script_type, script_args
                )

        execution.stdout = stdout
        execution.stderr = stderr
        execution.status = "success" if return_code == 0 else "failure"
        execution.completed_at = datetime.datetime.utcnow()
        db.commit()

        log_event(
            "execution_complete",
            execution_id=execution_id,
            status=execution.status,
            return_code=return_code
        )

        return execution.status

    except Exception as e:
        log_event(
            "execution_error",
            execution_id=execution_id,
            error_type=type(e).__name__,
            error_message=str(e)
        )
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


def _execute_directly(
    file_path: str,
    script_type: str,
    script_args: Optional[List[str]] = None
) -> Tuple[int, str, str]:
    """Execute script directly (fallback when sandbox unavailable)."""
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

    return run_local(cmd)


@celery_app.task(bind=True)
def scan_subnet_task(self, subnet_id: int):
    """Scan a subnet for active hosts using nmap."""
    from backend.core.database import SessionLocal
    from backend.models import Subnet, IPAddress

    db: Session = SessionLocal()
    try:
        subnet = db.query(Subnet).filter(Subnet.id == subnet_id).first()

        if not subnet:
            log_event("subnet_not_found", subnet_id=subnet_id)
            return "Subnet not found"

        log_event("subnet_scan_start", subnet_id=subnet_id, cidr=str(subnet.cidr))

        nm = nmap.PortScanner()

        try:
            nm.scan(hosts=str(subnet.cidr), arguments='-sn -PR -R --max-retries 2')
        except nmap.PortScannerError as e:
            log_event("nmap_error", subnet_id=subnet_id, error=str(e))
            return f"Scan failed: {str(e)}"
        except Exception as e:
            log_event("scan_error", subnet_id=subnet_id, error=str(e))
            return f"Scan failed: {str(e)}"

        scanned_hosts = nm.all_hosts()
        log_event(
            "subnet_scan_hosts_found",
            subnet_id=subnet_id,
            host_count=len(scanned_hosts)
        )

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

        log_event(
            "subnet_scan_complete",
            subnet_id=subnet_id,
            cidr=str(subnet.cidr),
            hosts_found=len(scanned_hosts)
        )

        return f"Scan complete for {subnet.cidr}. Found {len(scanned_hosts)} hosts."

    except Exception as e:
        log_event(
            "subnet_scan_error",
            subnet_id=subnet_id,
            error_type=type(e).__name__,
            error_message=str(e)
        )
        return f"Scan failed: {str(e)}"
    finally:
        db.close()


# ==================== EXPIRATION NOTIFICATION TASKS ====================

@celery_app.task(bind=True)
def check_expiring_warranties_task(self, days_threshold: int = 30):
    """
    Check for equipment warranties expiring within the threshold.
    Logs alerts for administrators.
    """
    from backend.core.database import SessionLocal
    from backend.models import Equipment

    db: Session = SessionLocal()
    try:
        today = datetime.date.today()
        threshold_date = today + datetime.timedelta(days=days_threshold)

        expiring = db.query(Equipment).filter(
            Equipment.warranty_expiry.isnot(None),
            Equipment.warranty_expiry >= today,
            Equipment.warranty_expiry <= threshold_date
        ).all()

        alerts = []
        for eq in expiring:
            days_remaining = (eq.warranty_expiry.date() - today).days
            severity = "critical" if days_remaining <= 7 else "warning" if days_remaining <= 14 else "info"

            alert = {
                "type": "warranty_expiration",
                "equipment_id": eq.id,
                "equipment_name": eq.name,
                "serial_number": eq.serial_number,
                "expiry_date": eq.warranty_expiry.isoformat(),
                "days_remaining": days_remaining,
                "severity": severity
            }
            alerts.append(alert)

            log_event(
                "warranty_expiration_alert",
                **alert
            )

        log_event(
            "warranty_check_complete",
            total_alerts=len(alerts),
            critical=len([a for a in alerts if a["severity"] == "critical"]),
            warning=len([a for a in alerts if a["severity"] == "warning"])
        )

        return {
            "status": "complete",
            "alerts_count": len(alerts),
            "alerts": alerts
        }

    except Exception as e:
        log_event(
            "warranty_check_error",
            error_type=type(e).__name__,
            error_message=str(e)
        )
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@celery_app.task(bind=True)
def check_expiring_contracts_task(self, days_threshold: int = 30):
    """
    Check for contracts expiring within the threshold.
    Logs alerts for administrators.
    """
    from backend.core.database import SessionLocal
    from backend.models import Contract

    db: Session = SessionLocal()
    try:
        today = datetime.date.today()
        threshold_date = today + datetime.timedelta(days=days_threshold)

        expiring = db.query(Contract).filter(
            Contract.end_date >= today,
            Contract.end_date <= threshold_date
        ).all()

        alerts = []
        for contract in expiring:
            days_remaining = (contract.end_date - today).days
            severity = "critical" if days_remaining <= 7 else "warning" if days_remaining <= 14 else "info"

            alert = {
                "type": "contract_expiration",
                "contract_id": contract.id,
                "contract_name": contract.name,
                "contract_type": contract.contract_type,
                "contract_number": contract.contract_number,
                "end_date": contract.end_date.isoformat(),
                "days_remaining": days_remaining,
                "severity": severity,
                "renewal_type": contract.renewal_type
            }
            alerts.append(alert)

            log_event(
                "contract_expiration_alert",
                **alert
            )

        log_event(
            "contract_check_complete",
            total_alerts=len(alerts),
            critical=len([a for a in alerts if a["severity"] == "critical"]),
            warning=len([a for a in alerts if a["severity"] == "warning"])
        )

        return {
            "status": "complete",
            "alerts_count": len(alerts),
            "alerts": alerts
        }

    except Exception as e:
        log_event(
            "contract_check_error",
            error_type=type(e).__name__,
            error_message=str(e)
        )
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@celery_app.task(bind=True)
def check_expiring_licenses_task(self, days_threshold: int = 30):
    """
    Check for software licenses expiring within the threshold.
    Logs alerts for administrators.
    """
    from backend.core.database import SessionLocal
    from backend.models import SoftwareLicense, Software

    db: Session = SessionLocal()
    try:
        today = datetime.date.today()
        threshold_date = today + datetime.timedelta(days=days_threshold)

        expiring = db.query(SoftwareLicense).filter(
            SoftwareLicense.expiry_date.isnot(None),
            SoftwareLicense.expiry_date >= today,
            SoftwareLicense.expiry_date <= threshold_date
        ).all()

        alerts = []
        for lic in expiring:
            software = db.query(Software).filter(
                Software.id == lic.software_id
            ).first()

            days_remaining = (lic.expiry_date - today).days
            severity = "critical" if days_remaining <= 7 else "warning" if days_remaining <= 14 else "info"

            alert = {
                "type": "license_expiration",
                "license_id": lic.id,
                "software_id": lic.software_id,
                "software_name": software.name if software else "Unknown",
                "license_type": lic.license_type,
                "quantity": lic.quantity,
                "expiry_date": lic.expiry_date.isoformat(),
                "days_remaining": days_remaining,
                "severity": severity
            }
            alerts.append(alert)

            log_event(
                "license_expiration_alert",
                **alert
            )

        log_event(
            "license_check_complete",
            total_alerts=len(alerts),
            critical=len([a for a in alerts if a["severity"] == "critical"]),
            warning=len([a for a in alerts if a["severity"] == "warning"])
        )

        return {
            "status": "complete",
            "alerts_count": len(alerts),
            "alerts": alerts
        }

    except Exception as e:
        log_event(
            "license_check_error",
            error_type=type(e).__name__,
            error_message=str(e)
        )
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@celery_app.task(bind=True)
def check_all_expirations_task(self, days_threshold: int = 30):
    """
    Master task to check all expiration types.
    Runs warranty, contract, and license checks.
    """
    log_event("expiration_check_start", threshold_days=days_threshold)

    warranty_result = check_expiring_warranties_task.delay(days_threshold)
    contract_result = check_expiring_contracts_task.delay(days_threshold)
    license_result = check_expiring_licenses_task.delay(days_threshold)

    log_event(
        "expiration_check_tasks_queued",
        warranty_task=str(warranty_result.id),
        contract_task=str(contract_result.id),
        license_task=str(license_result.id)
    )

    return {
        "status": "queued",
        "warranty_task_id": str(warranty_result.id),
        "contract_task_id": str(contract_result.id),
        "license_task_id": str(license_result.id)
    }


# ==================== SOFTWARE COLLECTION TASKS ====================

@celery_app.task(bind=True)
def collect_software_inventory_task(self, equipment_id: int):
    """
    Collect installed software from equipment via SSH/WinRM.
    Uses sandboxed execution for safety.
    """
    from backend.core.database import SessionLocal
    from backend.models import Equipment, Software, SoftwareInstallation
    from backend.core.security import decrypt_value

    db: Session = SessionLocal()
    try:
        equipment = db.query(Equipment).filter(
            Equipment.id == equipment_id
        ).first()

        if not equipment:
            log_event("software_collection_error", equipment_id=equipment_id, error="Equipment not found")
            return {"status": "error", "message": "Equipment not found"}

        if not equipment.remote_ip or not equipment.connection_type:
            log_event("software_collection_error", equipment_id=equipment_id, error="Remote execution not configured")
            return {"status": "error", "message": "Remote execution not configured"}

        log_event(
            "software_collection_start",
            equipment_id=equipment_id,
            equipment_name=equipment.name,
            connection_type=equipment.connection_type
        )

        # Determine command based on OS type
        if equipment.os_type == "linux":
            # Try dpkg first, then rpm
            command = "dpkg -l 2>/dev/null || rpm -qa 2>/dev/null"
        elif equipment.os_type == "windows":
            command = "Get-Package | Select-Object Name, Version | ConvertTo-Json"
        else:
            return {"status": "error", "message": f"Unsupported OS type: {equipment.os_type}"}

        # Execute command
        if equipment.connection_type == "ssh":
            return_code, stdout, stderr = _collect_via_ssh(equipment, command)
        elif equipment.connection_type == "winrm":
            return_code, stdout, stderr = _collect_via_winrm(equipment, command)
        else:
            return {"status": "error", "message": f"Unknown connection type: {equipment.connection_type}"}

        if return_code != 0:
            log_event(
                "software_collection_error",
                equipment_id=equipment_id,
                return_code=return_code,
                stderr=stderr[:500]
            )
            return {"status": "error", "message": stderr[:500]}

        # Parse output and store
        software_list = _parse_software_output(stdout, equipment.os_type)
        new_count = 0
        updated_count = 0

        for sw_info in software_list:
            # Find or create software entry
            software = db.query(Software).filter(
                Software.name == sw_info["name"]
            ).first()

            if not software:
                software = Software(
                    name=sw_info["name"],
                    version=sw_info.get("version"),
                    category="discovered",
                    entity_id=equipment.entity_id
                )
                db.add(software)
                db.flush()

            # Check for existing installation
            installation = db.query(SoftwareInstallation).filter(
                SoftwareInstallation.software_id == software.id,
                SoftwareInstallation.equipment_id == equipment_id
            ).first()

            if installation:
                installation.installed_version = sw_info.get("version")
                installation.discovered_at = datetime.datetime.utcnow()
                updated_count += 1
            else:
                installation = SoftwareInstallation(
                    software_id=software.id,
                    equipment_id=equipment_id,
                    installed_version=sw_info.get("version"),
                    discovered_at=datetime.datetime.utcnow()
                )
                db.add(installation)
                new_count += 1

        db.commit()

        log_event(
            "software_collection_complete",
            equipment_id=equipment_id,
            equipment_name=equipment.name,
            new_software=new_count,
            updated_software=updated_count,
            total_found=len(software_list)
        )

        return {
            "status": "success",
            "equipment": equipment.name,
            "new_software": new_count,
            "updated_software": updated_count,
            "total_found": len(software_list)
        }

    except Exception as e:
        log_event(
            "software_collection_error",
            equipment_id=equipment_id,
            error_type=type(e).__name__,
            error_message=str(e)
        )
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


def _collect_via_ssh(equipment, command: str) -> Tuple[int, str, str]:
    """Execute collection command via SSH."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        from backend.core.security import decrypt_value
        password = equipment.remote_password
        try:
            password = decrypt_value(password)
        except Exception:
            pass

        client.connect(
            hostname=equipment.remote_ip,
            port=equipment.remote_port or 22,
            username=equipment.remote_username,
            password=password,
            timeout=SSH_TIMEOUT,
            allow_agent=False,
            look_for_keys=False
        )

        stdin, stdout, stderr = client.exec_command(command, timeout=60)
        exit_status = stdout.channel.recv_exit_status()

        return (
            exit_status,
            stdout.read().decode('utf-8', errors='replace'),
            stderr.read().decode('utf-8', errors='replace')
        )
    except Exception as e:
        return -1, "", str(e)
    finally:
        client.close()


def _collect_via_winrm(equipment, command: str) -> Tuple[int, str, str]:
    """Execute collection command via WinRM."""
    try:
        from backend.core.security import decrypt_value
        password = equipment.remote_password
        try:
            password = decrypt_value(password)
        except Exception:
            pass

        port = equipment.remote_port or 5985
        use_ssl = port == 5986

        if use_ssl:
            session = winrm.Session(
                f'https://{equipment.remote_ip}:{port}/wsman',
                auth=(equipment.remote_username, password),
                transport='ntlm',
                server_cert_validation='ignore'
            )
        else:
            session = winrm.Session(
                f'http://{equipment.remote_ip}:{port}/wsman',
                auth=(equipment.remote_username, password),
                transport='ntlm'
            )

        result = session.run_ps(command)
        return (
            result.status_code,
            result.std_out.decode('utf-8', errors='replace'),
            result.std_err.decode('utf-8', errors='replace')
        )
    except Exception as e:
        return -1, "", str(e)


def _parse_software_output(output: str, os_type: str) -> List[dict]:
    """Parse software list output from different OS types."""
    software_list = []

    if os_type == "linux":
        # Parse dpkg or rpm output
        for line in output.split('\n'):
            parts = line.split()
            if len(parts) >= 3 and parts[0] in ('ii', 'hi', 'rc'):
                # dpkg format: status  name  version  description
                software_list.append({
                    "name": parts[1].split(':')[0],  # Remove architecture suffix
                    "version": parts[2]
                })
            elif len(parts) >= 1 and '-' in parts[0]:
                # rpm format: name-version-release.arch
                name_parts = parts[0].rsplit('-', 2)
                if len(name_parts) >= 2:
                    software_list.append({
                        "name": name_parts[0],
                        "version": name_parts[1] if len(name_parts) > 1 else None
                    })

    elif os_type == "windows":
        # Parse PowerShell JSON output
        try:
            import json
            packages = json.loads(output)
            if isinstance(packages, list):
                for pkg in packages:
                    if isinstance(pkg, dict) and "Name" in pkg:
                        software_list.append({
                            "name": pkg["Name"],
                            "version": pkg.get("Version")
                        })
        except json.JSONDecodeError:
            # Fallback: try line-by-line parsing
            for line in output.split('\n'):
                if line.strip():
                    software_list.append({"name": line.strip(), "version": None})

    return software_list
