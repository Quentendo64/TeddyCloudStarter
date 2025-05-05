#!/usr/bin/env python3
"""
Let's Encrypt certificate management functionality for TeddyCloudStarter.
"""
import subprocess
from pathlib import Path

from rich.console import Console
from ..utilities.logger import logger

# Re-export console to ensure compatibility
console = Console()


class LetsEncryptManager:
    """
    Handles Let's Encrypt certificate operations for TeddyCloudStarter.

    This class provides methods for requesting Let's Encrypt certificates
    using both standalone and webroot methods, in both staging and production
    environments.
    """

    def __init__(self, translator=None, base_dir=None):
        """
        Initialize the Let's Encrypt manager.

        Args:
            translator: Optional translator instance for localization
            base_dir: Optional base directory of the project
        """
        # Store parameters for lazy initialization
        logger.debug("Initializing LetsEncryptManager instance.")
        self.base_dir_param = base_dir
        self.translator = translator

        # Will be initialized when needed
        if base_dir is not None:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = None

    def _ensure_base_dir(self):
        """Lazily initialize the base directory if needed"""
        logger.debug("Ensuring base directory for Let's Encrypt operations.")
        if self.base_dir is not None:
            logger.debug("Base directory already initialized.")
            return

        # Try to get project path from config
        from ..config_manager import ConfigManager

        config_manager = ConfigManager()
        project_path = None
        try:
            if config_manager and config_manager.config:
                project_path = config_manager.config.get("environment", {}).get("path")
                logger.debug(f"Project path from config: {project_path}")
        except Exception as e:
            logger.warning(f"Failed to get project path from config: {e}")

        if project_path:
            logger.info(f"Using project path for base_dir: {project_path}")
            self.base_dir = Path(project_path)
        else:
            logger.warning("No project path found. Using current directory as fallback.")
            console.print(
                "[bold red]Warning: No project path found for certificate operations. Using current directory as fallback.[/]"
            )
            self.base_dir = Path.cwd()
            if self.translator:
                logger.info("Translator available. Printing warning about project path.")
                console.print(
                    f"[yellow]{self.translator.get('Please set a project path to ensure certificates are stored in the correct location.')}[/]"
                )

    def _translate(self, text: str) -> str:
        """
        Helper method to translate text if translator is available.

        Args:
            text: The text to translate

        Returns:
            str: Translated text if translator is available, otherwise original text
        """
        if self.translator:
            return self.translator.get(text)
        return text

    def create_letsencrypt_certificate_webroot(
        self,
        domain,
        email=None,
        sans=None,
        staging=False,
        force_renewal=False,
        project_path=None,
        docker_manager=None,
    ):
        """
        Create a Let's Encrypt certificate using certbot in webroot mode.
        1. Starts all services with docker compose up -d
        2. Runs a temporary certbot container with correct volumes
        3. Checks if certificate files exist in the Docker volume
        Args:
            domain (str): The main domain for the certificate
            email (str): Optional email for Let's Encrypt registration
            sans (list): Optional list of Subject Alternative Names
            staging (bool): Use Let's Encrypt staging endpoint if True
            force_renewal (bool): Force certificate renewal if True
            project_path (str): Optional project path for data dir
            docker_manager: DockerManager instance to control services
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info(f"Starting Let's Encrypt certificate creation for domain: {domain}")
        import shlex
        from rich.console import Console
        console = Console()
        import subprocess
        from pathlib import Path

        # Compose file path
        if project_path:
            compose_file = str(Path(project_path) / "data" / "docker-compose.yml")
        else:
            compose_file = str(Path("data") / "docker-compose.yml")
        logger.debug(f"Using docker-compose file: {compose_file}")

        # 1. Start all services
        up_cmd = [
            "docker", "compose", "-f", compose_file, "up", "-d"
        ]
        logger.info("Starting all services with docker compose up -d...")
        logger.debug(f"Running command: {' '.join(up_cmd)}")
        try:
            subprocess.run(up_cmd, check=True)
            logger.success("Docker services started successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start Docker services: {e}")
            return False

        # 2. Run certbot in a temporary container
        # Get volume names (assume default names based on compose project)
        project_name = Path(compose_file).stem.replace("docker-compose", "teddycloudstarter")
        certbot_conf_vol = f"{project_name}_certbot_conf"
        certbot_www_vol = f"{project_name}_certbot_www"
        certbot_logs_vol = f"{project_name}_certbot_logs"
        certbot_image = "certbot/certbot:latest"
        certbot_cmd = [
            "sudo", "docker", "run", "--rm",
            "-v", f"{certbot_conf_vol}:/etc/letsencrypt",
            "-v", f"{certbot_www_vol}:/var/www/certbot",
            "-v", f"{certbot_logs_vol}:/var/log/letsencrypt",
            certbot_image,
            "certonly", "--webroot",
            "-w", "/var/www/certbot",
            "-d", domain,
            "--agree-tos", "--non-interactive"
        ]
        if email:
            certbot_cmd += ["--email", email]
        else:
            certbot_cmd += ["--register-unsafely-without-email"]
        if sans:
            for san in sans:
                certbot_cmd += ["-d", san]
        if staging:
            certbot_cmd += ["--staging"]
        if force_renewal:
            certbot_cmd += ["--force-renewal"]

        logger.info(f"Running certbot to issue certificate for {domain}...")
        logger.debug(f"Running command: {' '.join(certbot_cmd)}")
        result = subprocess.run(certbot_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Certbot failed for {domain}!")
            logger.debug(f"Certbot stdout: {result.stdout}")
            logger.debug(f"Certbot stderr: {result.stderr}")
            console.print(f"[red]Certbot failed![/]")
            console.print(result.stdout)
            console.print(result.stderr)
            return False
        logger.success(f"Certbot succeeded for {domain}.")

        # 3. Check if certificate files exist in the Docker volume
        check_cmd = [
            "sudo", "docker", "run", "--rm",
            "-v", f"{certbot_conf_vol}:/etc/letsencrypt",
            "alpine", "ls", f"/etc/letsencrypt/live/{domain}"
        ]
        logger.info(f"Checking for certificate files in Docker volume for {domain}...")
        logger.debug(f"Running command: {' '.join(check_cmd)}")
        check_result = subprocess.run(check_cmd, capture_output=True, text=True)
        if check_result.returncode == 0:
            logger.success(f"Certificate files found for {domain}.")
            console.print(f"[green]Certificate files found for {domain}![/]")
            return True
        else:
            logger.error(f"Certificate files not found for {domain}!")
            logger.debug(f"Check stdout: {check_result.stdout}")
            logger.debug(f"Check stderr: {check_result.stderr}")
            console.print(f"[red]Certificate files not found for {domain}![/]")
            console.print(check_result.stdout)
            console.print(check_result.stderr)
            return False
