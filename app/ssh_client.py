"""
Secure SSH client for pfSense configuration retrieval.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple
import paramiko

logger = logging.getLogger(__name__)


class SecureSSHClient:
    """Wrapper around paramiko with security best practices."""

    def __init__(
        self,
        hostname: str,
        username: str,
        timeout: int = 30,
        known_hosts_check: bool = True,
    ):
        """
        Initialize SSH client.

        Args:
            hostname: Remote host IP or hostname
            username: SSH username
            timeout: Connection timeout in seconds
            known_hosts_check: Whether to verify host keys
        """
        self.hostname = hostname
        self.username = username
        self.timeout = timeout
        self.known_hosts_check = known_hosts_check
        self._client: Optional[paramiko.SSHClient] = None

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def connect(self) -> None:
        """
        Establish SSH connection using key-based authentication only.

        Raises:
            paramiko.AuthenticationException: If authentication fails
            paramiko.SSHException: If connection fails
            ValueError: If known_hosts check fails
        """
        self._client = paramiko.SSHClient()

        if self.known_hosts_check:
            # Load system host keys
            known_hosts_path = Path.home() / ".ssh" / "known_hosts"
            if known_hosts_path.exists():
                self._client.load_host_keys(str(known_hosts_path))
            # Reject unknown hosts
            self._client.set_missing_host_key_policy(paramiko.RejectPolicy())
        else:
            logger.warning(
                f"SSH host key verification disabled for {self.hostname}. "
                "This is insecure and vulnerable to MITM attacks!"
            )
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            logger.info(f"Connecting to {self.hostname} as {self.username}")
            self._client.connect(
                self.hostname,
                username=self.username,
                timeout=self.timeout,
                look_for_keys=True,
                allow_agent=True,
                # Password authentication disabled for security
                password=None,
            )
            logger.info(f"Successfully connected to {self.hostname}")
        except paramiko.AuthenticationException:
            logger.error(f"Authentication failed for {self.hostname}")
            raise
        except paramiko.SSHException as e:
            logger.error(f"SSH connection failed for {self.hostname}: {e}")
            raise

    def execute_command(self, command: str) -> Tuple[str, str, int]:
        """
        Execute a command on the remote host.

        Args:
            command: Command to execute

        Returns:
            Tuple of (stdout, stderr, exit_code)

        Raises:
            RuntimeError: If not connected
            paramiko.SSHException: If command execution fails
        """
        if not self._client:
            raise RuntimeError("Not connected. Call connect() first.")

        logger.debug(f"Executing command: {command}")

        try:
            stdin, stdout, stderr = self._client.exec_command(command, timeout=30)
            exit_code = stdout.channel.recv_exit_status()

            stdout_data = stdout.read().decode("utf-8", errors="ignore")
            stderr_data = stderr.read().decode("utf-8", errors="ignore")

            logger.debug(f"Command exit code: {exit_code}")

            return stdout_data, stderr_data, exit_code

        except paramiko.SSHException as e:
            logger.error(f"Command execution failed: {e}")
            raise

    def read_file(self, remote_path: str) -> Optional[str]:
        """
        Read a file from the remote system using SFTP (safer than exec_command).

        Args:
            remote_path: Path to file on remote system

        Returns:
            File contents as string, or None if file doesn't exist

        Raises:
            RuntimeError: If not connected
        """
        if not self._client:
            raise RuntimeError("Not connected. Call connect() first.")

        try:
            sftp = self._client.open_sftp()
            with sftp.file(remote_path, "r") as f:
                content = f.read().decode("utf-8", errors="ignore")
            sftp.close()
            logger.info(f"Successfully read file: {remote_path}")
            return content
        except FileNotFoundError:
            logger.warning(f"File not found: {remote_path}")
            return None
        except Exception as e:
            logger.error(f"Failed to read file {remote_path}: {e}")
            raise

    def file_exists(self, remote_path: str) -> bool:
        """
        Check if a file exists on the remote system using SFTP.

        Args:
            remote_path: Path to check

        Returns:
            True if file exists, False otherwise
        """
        if not self._client:
            raise RuntimeError("Not connected. Call connect() first.")

        try:
            sftp = self._client.open_sftp()
            sftp.stat(remote_path)
            sftp.close()
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Error checking file existence {remote_path}: {e}")
            return False

    def close(self) -> None:
        """Close the SSH connection."""
        if self._client:
            try:
                self._client.close()
                logger.info(f"Closed connection to {self.hostname}")
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
            finally:
                self._client = None
