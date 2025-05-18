#!/usr/bin/env python3
"""
Docker management functionality for TeddyCloudStarter.
"""
import os
import subprocess
import time
from typing import Dict, Optional, Tuple

from rich.console import Console
from ..utilities.logger import logger

console = Console()


class DockerManager:
    """Handles Docker operations."""

    def __init__(self, translator=None):
        self.docker_available = False
        self.compose_cmd = None
        self.translator = translator
        logger.debug("Initializing DockerManager instance.")
        self._check_docker()

    def _check_docker(self):
        """Check if Docker and Docker Compose are available."""
        logger.debug("Checking Docker and Docker Compose availability.")
        try:
            subprocess.run(
                ["docker", "--version"], check=True, capture_output=True, text=True
            )
            logger.debug("Docker is available.")
            subprocess.run(
                ["docker", "compose", "version"],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.debug("Docker Compose is available.")
            self.compose_cmd = ["docker", "compose"]
            self.docker_available = True
            logger.info("Docker and Docker Compose are available.")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            self.docker_available = False
            logger.error(f"Docker or Docker Compose not available: {e}")

    @staticmethod
    def check_docker_prerequisites() -> Tuple[bool, Dict[str, bool], Optional[str]]:
        """
        OS-independent check for Docker and Docker Compose availability.

        Returns:
            Tuple containing:
                - bool: True if all prerequisites are met, False otherwise
                - Dict: Dictionary with keys 'docker' and 'docker_compose' showing individual availability
                - str: Error message if prerequisites are not met, None otherwise
        """
        logger.debug("Checking Docker prerequisites (static method).")
        prerequisites = {"docker": False, "docker_compose": False}

        error_message = None

        try:
            result = subprocess.run(
                ["docker", "--version"], check=True, capture_output=True, text=True
            )
            prerequisites["docker"] = True
            logger.debug(f"Docker version output: {result.stdout.strip()}")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            prerequisites["docker"] = False
            logger.warning(f"Docker not available: {e}")

        try:
            result = subprocess.run(
                ["docker", "compose", "version"],
                check=True,
                capture_output=True,
                text=True,
            )
            prerequisites["docker_compose"] = True
            logger.debug(f"Docker Compose version output: {result.stdout.strip()}")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.debug(f"docker compose not found, trying docker-compose: {e}")
            try:
                result = subprocess.run(
                    ["docker-compose", "--version"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                prerequisites["docker_compose"] = True
                logger.debug(f"docker-compose version output: {result.stdout.strip()}")
            except (subprocess.SubprocessError, FileNotFoundError) as e2:
                prerequisites["docker_compose"] = False
                logger.warning(f"Docker Compose not available: {e2}")

        all_met = all(prerequisites.values())

        if not all_met:
            missing_components = []

            if not prerequisites["docker"]:
                missing_components.append("Docker")
            if not prerequisites["docker_compose"]:
                missing_components.append("Docker Compose")

            if missing_components:
                error_message = (
                    f"Missing required components: {', '.join(missing_components)}. "
                )
                logger.error(error_message)

                if os.name == "nt":
                    error_message += "Please install Docker Desktop for Windows from https://www.docker.com/products/docker-desktop"
                elif os.name == "posix":
                    if os.path.exists("/etc/os-release"):
                        with open("/etc/os-release", "r") as f:
                            os_info = f.read()
                            if "ID=ubuntu" in os_info:
                                error_message += "For Ubuntu, follow the official Docker installation guide: https://docs.docker.com/engine/install/ubuntu/"
                            elif "ID=debian" in os_info:
                                error_message += "For Debian, follow the official Docker installation guide: https://docs.docker.com/engine/install/debian/"
                            elif "ID=fedora" in os_info:
                                error_message += "For Fedora, follow the official Docker installation guide: https://docs.docker.com/engine/install/fedora/"
                            elif "ID=rhel" in os_info or "ID=centos" in os_info:
                                error_message += "For RHEL/CentOS, follow the official Docker installation guide: https://docs.docker.com/engine/install/rhel/"
                            else:
                                error_message += "Please follow the official Docker installation guide for your Linux distribution: https://docs.docker.com/engine/install/"
                    else:
                        error_message += "Please follow the official Docker installation guide for your operating system: https://docs.docker.com/get-docker/"
                else:
                    error_message += "Please follow the official Docker installation guide for your operating system: https://docs.docker.com/get-docker/"

        logger.info(f"Docker prerequisites check result: {prerequisites}, error: {error_message}")
        return all_met, prerequisites, error_message

    def is_available(self):
        """Return True if Docker is available."""
        return self.docker_available

    def _translate(self, text):
        """Helper method to translate text if translator is available."""
        if self.translator:
            return self.translator.get(text)
        return text

    def _get_data_dir(self, project_path=None):
        """Helper to get the correct data directory based on project_path."""
        base_path = project_path if project_path else os.getcwd()
        return os.path.join(base_path, "data")

    def down_services(self, project_path=None):
        """
        Completely stop and remove Docker containers, networks defined in docker-compose.yml.
        This is more thorough than just stopping services as it removes the containers entirely.

        Args:
            project_path: Path to the project directory (optional)

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.docker_available:
            console.print(f"[bold red]{self._translate('Docker is not available.')}[/]")
            return False
        try:
            console.print(
                f"[bold yellow]{self._translate('Stopping and removing all Docker services...')}[/]"
            )
            original_dir = os.getcwd()
            data_dir = self._get_data_dir(project_path)
            docker_compose_path = os.path.join(data_dir, "docker-compose.yml")
            if not os.path.exists(docker_compose_path):
                console.print(
                    f"[yellow]{self._translate('No docker-compose.yml found, skipping Docker service shutdown')}"
                )
                return False
            os.chdir(data_dir)
            try:
                subprocess.run(
                    self.compose_cmd + ["down"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                console.print(
                    f"[green]{self._translate('Docker services stopped and removed successfully')}[/]"
                )
                return True
            finally:
                os.chdir(original_dir)
        except subprocess.SubprocessError as e:
            error_msg = f"Error stopping Docker services: {e}"
            console.print(f"[yellow]{self._translate(error_msg)}[/]")
            console.print(
                f"[yellow]{self._translate('Continuing with operations...')}[/]"
            )
            return False
        except Exception as e:
            error_msg = f"Unexpected error stopping Docker services: {e}"
            console.print(f"[yellow]{self._translate(error_msg)}[/]")
            console.print(
                f"[yellow]{self._translate('Continuing with operations...')}[/]"
            )
            return False

    def get_services_status(self, project_path=None) -> Dict[str, Dict]:
        """Get status of all services in docker-compose.yml."""
        if not self.docker_available:
            console.print(f"[bold red]{self._translate('Docker is not available.')}[/]")
            return {}

        services = {}

        try:
            original_dir = os.getcwd()
            data_dir = self._get_data_dir(project_path)
            docker_compose_path = os.path.join(data_dir, "docker-compose.yml")
            if not os.path.exists(docker_compose_path):
                error_msg = f"docker-compose.yml not found at {docker_compose_path}"
                console.print(f"[bold yellow]{self._translate(error_msg)}[/]")
                return {}
            os.chdir(data_dir)
            try:
                service_list_result = subprocess.run(
                    self.compose_cmd + ["config", "--services"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                service_list = [
                    s.strip()
                    for s in service_list_result.stdout.strip().split("\n")
                    if s.strip()
                ]

                for service in service_list:
                    services[service] = {
                        "state": self._translate("Stopped"),
                        "running_for": "",
                    }

                ps_result = subprocess.run(
                    self.compose_cmd + ["ps", "--all", "--format", "json"],
                    check=True,
                    capture_output=True,
                    text=True,
                )

                import json

                try:
                    json_lines = [
                        line.strip()
                        for line in ps_result.stdout.strip().split("\n")
                        if line.strip()
                    ]

                    for line in json_lines:
                        container = json.loads(line)
                        service = container.get("Service", "")
                        state = container.get("State", "")
                        running_for = container.get("RunningFor", "")

                        if service in service_list:
                            services[service] = {
                                "state": (
                                    self._translate("Running")
                                    if state.lower() == "running"
                                    else self._translate("Stopped")
                                ),
                                "running_for": (
                                    running_for if state.lower() == "running" else ""
                                ),
                            }

                except json.JSONDecodeError as e:
                    error_msg = (
                        f"Failed to parse JSON output from docker compose ps: {e}"
                    )
                    console.print(f"[yellow]{self._translate(error_msg)}[/]")

                return services

            finally:
                os.chdir(original_dir)

        except subprocess.SubprocessError as e:
            error_msg = f"Error getting services status: {e}"
            console.print(f"[bold red]{self._translate(error_msg)}[/]")

            try:
                os.chdir(data_dir)
                result = subprocess.run(
                    self.compose_cmd + ["config", "--services"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                service_list = result.stdout.strip().split("\n")
                for service in service_list:
                    service = service.strip()
                    if service:
                        services[service] = {
                            "state": self._translate("Unknown"),
                            "running_for": "",
                        }
                os.chdir(original_dir)
            except:
                pass

            return services
        except FileNotFoundError:
            error_msg = f"Error: docker-compose.yml not found in {data_dir}."
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return {}

    def restart_services(self, project_path=None):
        """Restart all Docker services."""
        if not self.docker_available:
            console.print(f"[bold red]{self._translate('Docker is not available.')}[/]")
            return False

        try:
            console.print(
                f"[bold cyan]{self._translate('Restarting Docker services...')}[/]"
            )
            original_dir = os.getcwd()
            data_dir = self._get_data_dir(project_path)
            os.chdir(data_dir)
            try:
                subprocess.run(self.compose_cmd + ["down"], check=True)
                subprocess.run(self.compose_cmd + ["up", "-d"], check=True)
                console.print(
                    f"[bold green]{self._translate('Services restarted successfully.')}[/]"
                )
                return True
            finally:
                os.chdir(original_dir)
        except subprocess.SubprocessError as e:
            error_msg = f"Error restarting services: {e}"
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return False
        except FileNotFoundError:
            error_msg = f"Error: docker-compose.yml not found in {data_dir}."
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return False

    def restart_service(self, service_name: str, project_path=None):
        """Restart a specific Docker service."""
        if not self.docker_available:
            console.print(f"[bold red]{self._translate('Docker is not available.')}[/]")
            return False

        try:
            msg = f"Restarting service {service_name}..."
            console.print(f"[bold cyan]{self._translate(msg)}[/]")
            original_dir = os.getcwd()
            data_dir = self._get_data_dir(project_path)
            os.chdir(data_dir)
            try:
                subprocess.run(self.compose_cmd + ["restart", service_name], check=True)
                success_msg = f"Service {service_name} restarted successfully."
                console.print(f"[bold green]{self._translate(success_msg)}[/]")
                return True
            finally:
                os.chdir(original_dir)
        except subprocess.SubprocessError as e:
            error_msg = f"Error restarting service {service_name}: {e}"
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return False
        except FileNotFoundError:
            error_msg = f"Error: docker-compose.yml not found in {data_dir}."
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return False

    def start_services(self, project_path=None):
        """Start all Docker services."""
        if not self.docker_available:
            console.print(f"[bold red]{self._translate('Docker is not available.')}[/]")
            return False

        try:
            console.print(
                f"[bold cyan]{self._translate('Starting Docker services...')}[/]"
            )
            original_dir = os.getcwd()
            data_dir = self._get_data_dir(project_path)
            os.chdir(data_dir)
            try:
                subprocess.run(self.compose_cmd + ["up", "-d"], check=True)
                console.print(
                    f"[bold green]{self._translate('Services started successfully.')}[/]"
                )
                return True
            finally:
                os.chdir(original_dir)
        except subprocess.SubprocessError as e:
            error_msg = f"Error starting services: {e}"
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return False
        except FileNotFoundError:
            error_msg = f"Error: docker-compose.yml not found in {data_dir}."
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return False

    def start_service(self, service_name: str, project_path=None):
        """Start a specific Docker service."""
        if not self.docker_available:
            console.print(f"[bold red]{self._translate('Docker is not available.')}[/]")
            return False

        try:
            msg = f"Starting service {service_name}..."
            console.print(f"[bold cyan]{self._translate(msg)}[/]")
            original_dir = os.getcwd()
            data_dir = self._get_data_dir(project_path)
            os.chdir(data_dir)
            try:
                subprocess.run(
                    self.compose_cmd + ["up", "-d", service_name], check=True
                )
                success_msg = f"Service {service_name} started successfully."
                console.print(f"[bold green]{self._translate(success_msg)}[/]")
                return True
            finally:
                os.chdir(original_dir)
        except subprocess.SubprocessError as e:
            error_msg = f"Error starting service {service_name}: {e}"
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return False
        except FileNotFoundError:
            error_msg = f"Error: docker-compose.yml not found in {data_dir}."
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return False

    def stop_services(self, project_path=None):
        """Stop all Docker services."""
        if not self.docker_available:
            console.print(f"[bold red]{self._translate('Docker is not available.')}[/]")
            return False

        try:
            console.print(
                f"[bold cyan]{self._translate('Stopping all Docker services...')}[/]"
            )
            original_dir = os.getcwd()
            data_dir = self._get_data_dir(project_path)
            os.chdir(data_dir)
            try:
                subprocess.run(self.compose_cmd + ["stop"], check=True)
                console.print(
                    f"[bold green]{self._translate('All services stopped successfully.')}[/]"
                )
                return True
            finally:
                os.chdir(original_dir)
        except subprocess.SubprocessError as e:
            error_msg = f"Error stopping services: {e}"
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return False
        except FileNotFoundError:
            error_msg = f"Error: docker-compose.yml not found in {data_dir}."
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return False

    def stop_service(self, service_name: str, project_path=None):
        """Stop a specific Docker service."""
        if not self.docker_available:
            console.print(f"[bold red]{self._translate('Docker is not available.')}[/]")
            return False

        try:
            msg = f"Stopping service {service_name}..."
            console.print(f"[bold cyan]{self._translate(msg)}[/]")
            original_dir = os.getcwd()
            data_dir = self._get_data_dir(project_path)
            os.chdir(data_dir)
            try:
                subprocess.run(self.compose_cmd + ["stop", service_name], check=True)
                success_msg = f"Service {service_name} stopped successfully."
                console.print(f"[bold green]{self._translate(success_msg)}[/]")
                return True
            finally:
                os.chdir(original_dir)
        except subprocess.SubprocessError as e:
            error_msg = f"Error stopping service {service_name}: {e}"
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return False
        except FileNotFoundError:
            error_msg = f"Error: docker-compose.yml not found in {data_dir}."
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return False

    def get_logs(self, service_name=None, lines=0, project_path=None):
        """
        Get logs from Docker services.

        Args:
            service_name: Optional specific service to get logs from
            lines: Number of lines to get (0 for all)
            project_path: Path to the project directory

        Returns:
            Subprocess.Popen object that can be used to control the logs process
        """
        if not self.docker_available:
            console.print(f"[bold red]{self._translate('Docker is not available.')}[/]")
            return None

        try:
            original_dir = os.getcwd()

            base_path = project_path if project_path else original_dir

            data_dir = os.path.join(base_path, "data")
            os.chdir(data_dir)

            try:
                cmd = self.compose_cmd + ["logs", "-f"]

                if lines > 0:
                    cmd.extend(["-n", str(lines)])

                if service_name:
                    cmd.append(service_name)

                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                )

                os.chdir(original_dir)

                return process

            except Exception as e:
                os.chdir(original_dir)
                error_msg = f"Error starting logs process: {e}"
                console.print(f"[bold red]{self._translate(error_msg)}[/]")
                return None

        except FileNotFoundError:
            error_msg = f"Error: docker-compose.yml not found in {data_dir}."
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return None

    def get_volumes(self):
        """Get a list of Docker volumes that start with teddycloudstarter_"""
        if not self.docker_available:
            console.print(f"[bold red]{self._translate('Docker is not available.')}[/]")
            return []

        try:
            result = subprocess.run(
                [
                    "docker",
                    "volume",
                    "ls",
                    "--filter",
                    "name=teddycloudstarter_",
                    "--format",
                    "{{.Name}}",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            volumes = [
                vol.strip() for vol in result.stdout.strip().split("\n") if vol.strip()
            ]
            return volumes
        except subprocess.SubprocessError as e:
            error_msg = f"Error getting Docker volumes: {e}"
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return []

    def backup_volume(self, volume_name, project_path=None):
        """
        Backup a Docker volume to a tar.gz file in data/backup directory.

        Args:
            volume_name: Name of the Docker volume to backup
            project_path: Path to project directory (optional)

        Returns:
            str: Path to the backup file if successful, None otherwise
        """
        if not self.docker_available:
            console.print(f"[bold red]{self._translate('Docker is not available.')}[/]")
            return None

        try:
            base_path = project_path if project_path else "."

            backup_dir = os.path.join(base_path, "data", "backup")
            os.makedirs(backup_dir, exist_ok=True)

            timestamp = time.strftime("%Y%m%d-%H%M%S")
            backup_name = volume_name.replace("teddycloudstarter_", "teddycloud-")
            backup_file = f"{backup_name}-backup-{timestamp}.tar.gz"
            backup_path = os.path.join(backup_dir, backup_file)

            volume_path = "/" + volume_name.replace("teddycloudstarter_", "")

            msg = f"Backing up volume {volume_name} to {backup_path}..."
            console.print(f"[bold cyan]{self._translate(msg)}[/]")

            abs_backup_dir = os.path.abspath(backup_dir)

            if os.name == "nt":
                backup_mount = abs_backup_dir.replace("\\", "/")
                cmd = [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    f"{volume_name}:{volume_path}",
                    "-v",
                    f"{backup_mount}:/backup",
                    "alpine",
                    "tar",
                    "czf",
                    f"/backup/{backup_file}",
                    volume_path,
                ]
            else:
                cmd = [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    f"{volume_name}:{volume_path}",
                    "-v",
                    f"{abs_backup_dir}:/backup",
                    "alpine",
                    "tar",
                    "czf",
                    f"/backup/{backup_file}",
                    volume_path,
                ]

            subprocess.run(cmd, check=True)
            success_msg = (
                f"Volume {volume_name} backed up successfully to {backup_path}"
            )
            console.print(f"[bold green]{self._translate(success_msg)}[/]")
            return backup_path

        except subprocess.SubprocessError as e:
            error_msg = f"Error backing up volume {volume_name}: {e}"
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return None
        except Exception as e:
            error_msg = f"Unexpected error backing up volume {volume_name}: {e}"
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return None

    def get_volume_backups(self, project_path=None, volume_name=None):
        """
        Get a list of available backup files for a specific volume or all volumes.

        Args:
            project_path: Path to project directory (optional)
            volume_name: Optional name of a specific volume

        Returns:
            dict: Dictionary mapping volume names to lists of backup files
        """
        base_path = project_path if project_path else "."

        backup_dir = os.path.join(base_path, "data", "backup")
        if not os.path.exists(backup_dir):
            return {}

        backups = {}
        backup_files = os.listdir(backup_dir)

        for file in backup_files:
            if not file.startswith("teddycloud-") or not file.endswith(".tar.gz"):
                continue

            try:
                parts = file.split("-backup-")
                if len(parts) != 2:
                    continue

                vol_name = parts[0]
                full_vol_name = "teddycloudstarter_" + vol_name.replace(
                    "teddycloud-", ""
                )

                if volume_name is None or volume_name == full_vol_name:
                    if full_vol_name not in backups:
                        backups[full_vol_name] = []
                    backups[full_vol_name].append(file)
            except:
                continue

        for vol_name in backups:
            backups[vol_name].sort(reverse=True)

        return backups

    def show_backup_contents(self, backup_file, project_path=None):
        """
        Show the contents of a backup file.

        Args:
            backup_file: Name of the backup file
            project_path: Path to the project directory (optional)

        Returns:
            bool: True if successful, False otherwise
        """
        base_path = project_path if project_path else "."
        backup_path = os.path.join(base_path, "data", "backup", backup_file)

        if not os.path.exists(backup_path):
            error_msg = f"Backup file {backup_file} not found."
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return False

        try:
            cmd = [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{os.path.abspath(os.path.join(base_path, 'data', 'backup'))}:/backup:ro",
                "alpine",
                "tar",
                "-tf",
                f"/backup/{backup_file}",
            ]

            result = subprocess.run(cmd, check=True, capture_output=True, text=True)

            msg = f"Contents of {backup_file}:"
            console.print(f"[bold cyan]{self._translate(msg)}[/]")
            console.print(result.stdout)
            return True

        except subprocess.SubprocessError as e:
            error_msg = f"Error showing backup contents: {e}"
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return False

    def restore_volume(self, volume_name, backup_file, project_path=None):
        """
        Restore a Docker volume from a backup file.

        Args:
            volume_name: Name of the Docker volume to restore
            backup_file: Name of the backup file
            project_path: Path to the project directory (optional)

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.docker_available:
            console.print(f"[bold red]{self._translate('Docker is not available.')}[/]")
            return False

        base_path = project_path if project_path else "."
        backup_path = os.path.join(base_path, "data", "backup", backup_file)

        if not os.path.exists(backup_path):
            error_msg = f"Backup file {backup_file} not found."
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return False

        try:
            volumes = self.get_volumes()
            if volume_name not in volumes:
                error_msg = f"Volume {volume_name} does not exist."
                console.print(f"[bold red]{self._translate(error_msg)}[/]")
                return False

            volume_path = "/" + volume_name.replace("teddycloudstarter_", "")

            warning_msg = f"Warning: This will overwrite the current contents of volume {volume_name}."
            console.print(f"[bold yellow]{self._translate(warning_msg)}[/]")
            warning_msg2 = (
                "Make sure all Docker containers using this volume are stopped."
            )
            console.print(f"[bold yellow]{self._translate(warning_msg2)}[/]")

            abs_backup_dir = os.path.abspath(os.path.join(base_path, "data", "backup"))

            msg = f"Restoring volume {volume_name} from {backup_file}..."
            console.print(f"[bold cyan]{self._translate(msg)}[/]")

            if os.name == "nt":
                backup_mount = abs_backup_dir.replace("\\", "/")
                cmd = [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    f"{volume_name}:{volume_path}",
                    "-v",
                    f"{backup_mount}:/backup:ro",
                    "alpine",
                    "sh",
                    "-c",
                    f"rm -rf {volume_path}/* && tar -xzf /backup/{backup_file} -C / --strip-components=1",
                ]
            else:
                cmd = [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    f"{volume_name}:{volume_path}",
                    "-v",
                    f"{abs_backup_dir}:/backup:ro",
                    "alpine",
                    "sh",
                    "-c",
                    f"rm -rf {volume_path}/* && tar -xzf /backup/{backup_file} -C / --strip-components=1",
                ]

            subprocess.run(cmd, check=True)
            success_msg = (
                f"Volume {volume_name} restored successfully from {backup_file}"
            )
            console.print(f"[bold green]{self._translate(success_msg)}[/]")
            return True

        except subprocess.SubprocessError as e:
            error_msg = f"Error restoring volume {volume_name}: {e}"
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return False
        except Exception as e:
            error_msg = f"Unexpected error restoring volume {volume_name}: {e}"
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return False
