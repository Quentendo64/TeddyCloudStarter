#!/usr/bin/env python3
"""
Let's Encrypt certificate management functionality for TeddyCloudStarter.
"""
import subprocess
from pathlib import Path

from rich.console import Console

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
        self.base_dir_param = base_dir
        self.translator = translator

        # Will be initialized when needed
        if base_dir is not None:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = None

    def _ensure_base_dir(self):
        """Lazily initialize the base directory if needed"""
        if self.base_dir is not None:
            # Already initialized
            return

        # Try to get project path from config
        from ..config_manager import ConfigManager

        config_manager = ConfigManager()
        project_path = None
        try:
            if config_manager and config_manager.config:
                project_path = config_manager.config.get("environment", {}).get("path")
        except Exception:
            pass

        if project_path:
            self.base_dir = Path(project_path)
        else:
            # Log an error if no project path is found
            console.print(
                "[bold red]Warning: No project path found for certificate operations. Using current directory as fallback.[/]"
            )
            self.base_dir = Path.cwd()
            if self.translator:
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
        Ensures nginx-edge is running and uses the correct volumes.
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
        # Ensure DockerManager is provided
        if docker_manager is None:
            from ..docker.manager import DockerManager

            docker_manager = DockerManager(translator=self.translator)
        if not docker_manager.is_available():
            console.print(f"[bold red]{self._translate('Docker is not available.')}[/]")
            return False

        # Ensure nginx-edge is running
        services = docker_manager.get_services_status(project_path)
        if services.get("nginx-edge", {}).get("state", "").lower() != "running":
            console.print(
                f"[bold yellow]{self._translate('Starting nginx-edge service for webroot challenge...')}[/]"
            )
            started = docker_manager.start_service("nginx-edge", project_path)
            if not started:
                console.print(
                    f"[bold red]{self._translate('Failed to start nginx-edge service. Cannot proceed with certificate request.')}[/]"
                )
                return False

        # Prepare certbot command
        certbot_image = "certbot/certbot:latest"
        webroot_path = "/var/www/certbot"
        cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            "certbot_conf:/etc/letsencrypt",
            "-v",
            "certbot_www:/var/www/certbot",
            "-v",
            "certbot_logs:/var/log/letsencrypt",
            certbot_image,
            "certonly",
            "--webroot",
            "-w",
            webroot_path,
            "-d",
            domain,
        ]
        if email:
            cmd += ["--email", email]
        else:
            cmd += ["--register-unsafely-without-email"]
        if sans:
            for san in sans:
                cmd += ["-d", san]
        if staging:
            cmd += ["--staging"]
        if force_renewal:
            cmd += ["--force-renewal"]
        cmd += ["--agree-tos", "--non-interactive"]

        console.print(
            f"[bold cyan]{self._translate('Requesting Let\'s Encrypt certificate for')} {domain}...[/]"
        )
        try:
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
            if result.returncode == 0:
                console.print(
                    f"[bold green]{self._translate('Certificate successfully obtained for')} {domain}[/]"
                )
                return True
            else:
                console.print(
                    f"[bold red]{self._translate('Failed to obtain certificate for')} {domain}[/]"
                )
                console.print(result.stdout)
                console.print(result.stderr)
                return False
        except Exception as e:
            console.print(
                f"[bold red]{self._translate('Error running certbot:')} {e}[/]"
            )
            return False
