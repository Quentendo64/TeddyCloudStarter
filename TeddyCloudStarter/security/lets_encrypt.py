#!/usr/bin/env python3
"""
Let's Encrypt certificate management functionality for TeddyCloudStarter.
"""
import subprocess
import time
import socket
import os
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, Tuple
from rich.console import Console
from rich.prompt import Confirm

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
        self.translator = translator
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        
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

    def _check_docker_service_exists(self, service_name: str) -> bool:
        """
        Check if a Docker service/container exists.
        
        Args:
            service_name: The name of the service to check
            
        Returns:
            bool: True if the service exists, False otherwise
        """
        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "--format", "{{.Names}}", "--filter", f"name={service_name}"],
                capture_output=True, text=True, check=True
            )
            return service_name in result.stdout
        except Exception:
            return False
    
    def _check_service_status(self, service_name: str) -> bool:
        """
        Check if a Docker service is running.
        
        Args:
            service_name: The name of the service to check
            
        Returns:
            bool: True if the service is running, False otherwise
        """
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}", "--filter", f"name={service_name}"],
                capture_output=True, text=True, check=True
            )
            return service_name in result.stdout
        except Exception:
            return False

    def _start_service(self, service_name: str) -> bool:
        """
        Start a Docker service if it's not already running.
        First tries docker start, then tries docker-compose up if that fails.
        
        Args:
            service_name: The name of the service to start
            
        Returns:
            bool: True if the service was started successfully, False otherwise
        """
        if self._check_service_status(service_name):
            # Service is already running
            return True
            
        try:
            # First try to simply start the container if it exists
            if self._check_docker_service_exists(service_name):
                console.print(f"[cyan]{self._translate('Starting existing')} {service_name} {self._translate('service')}...[/]")
                try:
                    subprocess.run(
                        ["docker", "start", service_name],
                        check=True, capture_output=True
                    )
                    # Wait a moment for the service to initialize
                    time.sleep(3)
                    return True
                except Exception as e:
                    console.print(f"[yellow]{self._translate('Could not start existing container:')} {e}[/]")
                    # Fall through to try docker-compose
            
            # If direct start failed or container doesn't exist, try using docker-compose
            console.print(f"[cyan]{self._translate('Starting')} {service_name} {self._translate('using docker-compose')}...[/]")
            
            # Check for docker-compose.yml in the current directory or project directory
            compose_file = self.base_dir / "docker-compose.yml"
            if not compose_file.exists():
                console.print(f"[yellow]{self._translate('No docker-compose.yml found in')} {self.base_dir}[/]")
                
                # Try creating a temporary docker-compose file for basic services
                if service_name == "nginx-edge":
                    return self._create_temp_nginx_service()
                else:
                    console.print(f"[bold red]{self._translate('Cannot start')} {service_name}: {self._translate('No docker-compose.yml found')}[/]")
                    return False
            
            # Start the specific service using docker-compose
            cmd = ["docker-compose", "-f", str(compose_file), "up", "-d", service_name]
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                # Wait a moment for the service to initialize
                time.sleep(5)
                return True
            except Exception as e:
                console.print(f"[bold red]{self._translate('Failed to start')} {service_name} {self._translate('with docker-compose')}: {e}[/]")
                
                # If we need nginx-edge, offer to create a temporary nginx container
                if service_name == "nginx-edge":
                    return self._create_temp_nginx_service()
                    
                return False
                
        except Exception as e:
            console.print(f"[bold red]{self._translate('Failed to start')} {service_name}: {e}[/]")
            return False

    def _create_temp_nginx_service(self) -> bool:
        """
        Create a temporary nginx service for Let's Encrypt validation when the main services are not available.
        
        Returns:
            bool: True if successful, False otherwise
        """
        use_temp = Confirm.ask(
            f"[bold yellow]{self._translate('nginx-edge service not available. Create a temporary nginx container for Let\'s Encrypt?')}[/]",
            default=True
        )
        
        if not use_temp:
            return False
            
        # Create a temporary nginx container for Let's Encrypt validation
        try:
            # Stop any existing temp container
            subprocess.run(
                ["docker", "rm", "-f", "temp-nginx-letsencrypt"],
                capture_output=True, text=True
            )
            
            # Create minimal nginx config for Let's Encrypt validation
            temp_dir = self.base_dir / "temp_letsencrypt"
            temp_dir.mkdir(exist_ok=True)
            
            # Create nginx config with the .well-known directory properly set up
            nginx_conf = temp_dir / "nginx.conf"
            with open(nginx_conf, "w") as f:
                f.write("""
server {
    listen 80;
    server_name _;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 404;
    }
}
""")
            
            # Start a temporary nginx container
            console.print(f"[cyan]{self._translate('Starting temporary nginx container for Let\'s Encrypt validation...')}[/]")
            subprocess.run([
                "docker", "run", "-d",
                "--name", "temp-nginx-letsencrypt",
                "-p", "80:80",
                "-v", f"{temp_dir.absolute()}/nginx.conf:/etc/nginx/conf.d/default.conf",
                "-v", "certbot_www:/var/www/certbot",
                "nginx:alpine"
            ], check=True)
            
            time.sleep(3)
            console.print(f"[bold green]{self._translate('Temporary nginx container started successfully')}[/]")
            return True
            
        except Exception as e:
            console.print(f"[bold red]{self._translate('Failed to create temporary nginx container:')} {e}[/]")
            return False
    
    def _stop_container(self, container_name: str) -> None:
        """
        Stop and remove a Docker container if it's running.
        
        Args:
            container_name: The name of the container to stop
        """
        try:
            subprocess.run(
                ["docker", "rm", "-f", container_name],
                capture_output=True, text=True
            )
        except Exception:
            pass
    
    def _check_certbot_container(self) -> Tuple[bool, str]:
        """
        Check if teddycloud-certbot container exists, 
        if not try to find any certbot container.
        
        Returns:
            Tuple[bool, str]: (exists, container_name) - True if a container was found and the name of the container
        """
        # First check for the standard certbot container
        if self._check_docker_service_exists("teddycloud-certbot"):
            return True, "teddycloud-certbot"
            
        # Then check for any certbot container
        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "--format", "{{.Names}}", "--filter", "ancestor=certbot/certbot"],
                capture_output=True, text=True, check=True
            )
            lines = result.stdout.strip().split('\n')
            if lines and lines[0]:
                # Found an existing certbot container
                return True, lines[0]
        except Exception:
            pass
            
        return False, "teddycloud-certbot"  # Default name

    def _display_error_details(self, stderr: str) -> None:
        """
        Display detailed error information from certbot stderr output.
        
        Args:
            stderr: The stderr output from certbot
        """
        if stderr:
            error_lines = stderr.split('\n')
            filtered_errors = [line for line in error_lines if line.strip() and not line.startswith('Saving debug log')]
            
            if filtered_errors:
                console.print(f"[bold red]{self._translate('Error details:')}[/]")
                for line in filtered_errors[:10]:  # Show at most 10 lines to avoid flooding
                    if "error:" in line.lower() or "critical:" in line.lower() or "problem" in line.lower():
                        console.print(f"[red]{line}[/]")
                    else:
                        console.print(line)
                
                if len(filtered_errors) > 10:
                    console.print(f"[dim]{self._translate('... additional error lines omitted ...')}[/]")

    def test_domain(self, domain: str) -> bool:
        """
        Test if a domain is properly set up for Let's Encrypt.
        
        Tests DNS resolution and tries to obtain a test certificate in staging mode.
        If staging mode fails, offers to try production mode.
        
        Args:
            domain: Domain name to test
            
        Returns:
            bool: True if domain passed at least one test, False otherwise
        """
        console.print(f"[bold cyan]{self._translate('Testing domain for Let\'s Encrypt compatibility...')}[/]")
        
        # 1. Check domain DNS resolution
        console.print(f"[cyan]{self._translate('Step 1: Testing DNS resolution for')} {domain}...[/]")
        try:
            socket.gethostbyname(domain)
            console.print(f"[bold green]{self._translate('DNS resolution successful!')}[/]")
            dns_check_passed = True
        except socket.gaierror:
            console.print(f"[bold red]{self._translate('DNS resolution failed. Your domain may not be properly configured.')}[/]")
            console.print(f"[yellow]{self._translate('Make sure your domain points to this server\'s public IP address.')}[/]")
            dns_check_passed = False
        
        # 2. Test HTTP connectivity (port 80 reachability)
        console.print(f"[cyan]{self._translate('Step 2: Testing port 80 accessibility for ACME challenge...')}[/]")
        
        # Create simple Docker container to test port 80
        try:
            check_cmd = [
                "docker", "run", "--rm",
                "busybox", "wget", "-q", "-T", "5", "-O-",
                f"http://{domain}/.well-known/acme-challenge/test"
            ]
            process = subprocess.run(check_cmd, capture_output=True, text=True)
            
            # We actually expect a 404 error (page not found), if we get a connection
            http_check_passed = process.returncode == 1 and "404" in process.stderr
            
            if http_check_passed:
                console.print(f"[bold green]{self._translate('Port 80 appears to be accessible!')}[/]")
            else:
                console.print(f"[bold yellow]{self._translate('Port 80 might not be reachable from the internet.')}[/]")
                console.print(f"[yellow]{self._translate('Make sure port 80 is forwarded to this server if you\'re behind a router/firewall.')}[/]")
        except Exception as e:
            console.print(f"[bold yellow]{self._translate('Could not test HTTP connectivity:')} {str(e)}[/]")
            http_check_passed = False
        
        # 3. Request a certificate in staging mode
        console.print(f"[cyan]{self._translate('Step 3: Testing certificate issuance in staging mode...')}[/]")
        
        # Use standalone mode for testing
        staging_success = self.request_certificate(
            domain=domain, 
            mode="standalone", 
            staging=True
        )
        
        if staging_success:
            console.print(f"[bold green]{self._translate('Staging certificate request successful!')}[/]")
            console.print(f"[green]{self._translate('Your domain seems to be properly configured for Let\'s Encrypt.')}[/]")
            return True
        else:
            console.print(f"[bold yellow]{self._translate('Staging certificate request failed.')}[/]")
            
            # If DNS check passed, we'll offer to try production mode
            if dns_check_passed:
                try_production = Confirm.ask(
                    f"[bold yellow]{self._translate('Would you like to try a real certificate request?')}[/]"
                )
                
                if try_production:
                    console.print(f"[cyan]{self._translate('Attempting production Let\'s Encrypt certificate request...')}[/]")
                    production_success = self.request_certificate(
                        domain=domain,
                        mode="standalone",
                        staging=False
                    )
                    
                    if production_success:
                        console.print(f"[bold green]{self._translate('Production certificate request successful!')}[/]")
                        console.print(f"[green]{self._translate('Your domain is properly configured for Let\'s Encrypt.')}[/]")
                        return True
                    else:
                        console.print(f"[bold red]{self._translate('Production certificate request also failed.')}[/]")
                        console.print(f"[yellow]{self._translate('Please check that:')}[/]")
                        console.print(f"[yellow]- {self._translate('Your domain points to this server')}")
                        console.print(f"[yellow]- {self._translate('Ports 80 and 443 are properly forwarded')}")
                        console.print(f"[yellow]- {self._translate('No firewall is blocking incoming connections')}")
                        return False
            else:
                console.print(f"[bold red]{self._translate('Domain validation failed. Cannot proceed with Let\'s Encrypt.')}[/]")
                return False

    def _reload_or_restart_nginx(self, service_name: str = "nginx-edge") -> bool:
        """
        Reload nginx configuration or restart the service if reload fails.
        
        Args:
            service_name: The name of the nginx service to reload/restart
            
        Returns:
            bool: True if successful, False otherwise
        """
        console.print(f"[cyan]{self._translate('Reloading nginx to apply the new certificates...')}[/]")
        
        # First try to reload the configuration
        try:
            reload_cmd = ["docker", "exec", service_name, "nginx", "-s", "reload"]
            subprocess.run(reload_cmd, check=True, capture_output=True)
            console.print(f"[green]{self._translate('Nginx configuration reloaded successfully')}[/]")
            return True
        except Exception as e:
            console.print(f"[yellow]{self._translate('Warning: Could not reload nginx:')} {e}[/]")
            console.print(f"[cyan]{self._translate('Attempting to restart the nginx service instead...')}[/]")
            
            # Try docker restart command
            try:
                restart_cmd = ["docker", "restart", service_name]
                subprocess.run(restart_cmd, check=True, capture_output=True)
                console.print(f"[green]{self._translate('Nginx service restarted successfully')}[/]")
                return True
            except Exception as e2:
                console.print(f"[yellow]{self._translate('Warning: Could not restart nginx service:')} {e2}[/]")
                
                # Try docker-compose restart as a last resort
                try:
                    compose_file = self.base_dir / "docker-compose.yml"
                    if compose_file.exists():
                        restart_cmd = ["docker-compose", "-f", str(compose_file), "restart", service_name]
                        subprocess.run(restart_cmd, check=True, capture_output=True)
                        console.print(f"[green]{self._translate('Nginx service restarted with docker-compose successfully')}[/]")
                        return True
                except Exception as e3:
                    console.print(f"[bold yellow]{self._translate('Failed to restart nginx:')} {e3}[/]")
                    console.print(f"[bold yellow]{self._translate('You may need to restart the nginx service manually.')}[/]")
                    return False

    def request_certificate(self, 
                          domain: str,
                          mode: str = "webroot", 
                          staging: bool = False, 
                          email: Optional[str] = None,
                          additional_domains: Optional[List[str]] = None,
                          force_renewal: bool = False) -> bool:
        """
        Request a Let's Encrypt certificate.
        
        Args:
            domain: Main domain name for the certificate
            mode: Authentication mode, either "webroot" or "standalone"
            staging: Whether to use staging environment, default is False (production)
            email: Optional email address for registration
            additional_domains: Optional list of additional domain names (SANs)
            force_renewal: Whether to force certificate renewal, default is False
            
        Returns:
            bool: True if successful, False otherwise
        """
        mode_str = "standalone" if mode == "standalone" else "webroot"
        staging_str = "staging" if staging else "production"
        
        log_message = f"Requesting Let's Encrypt certificate ({staging_str}) using {mode_str} mode"
        if force_renewal:
            log_message += " (force renewal)"
        console.print(f"[bold cyan]{self._translate(log_message)}...[/]")
        
        try:
            # Build domain list starting with main domain
            domains = [domain]
            if additional_domains:
                domains.extend(additional_domains)
                
            # Handle cleanup for any temporary resources
            temp_nginx_created = False
            temp_container_created = False
            
            try:
                if mode == "standalone":
                    # Execute certbot in standalone mode with a temporary container
                    # (This doesn't use the existing services since standalone needs to bind port 80)
                    
                    # Make sure no conflicting containers are running
                    self._stop_container("temp-nginx-letsencrypt")
                    
                    # Build standalone mode command
                    cmd = [
                        "docker", "run", "--rm",
                        "--name", "certbot-temp",
                        "-p", "80:80",  # Required for standalone mode
                        "-v", "certbot_conf:/etc/letsencrypt"
                    ]
                    
                    # Add certbot command
                    cmd.extend([
                        "certbot/certbot", "certonly", 
                        "--standalone",
                        "-v"  # Verbose output
                    ])
                    
                    temp_container_created = True
                    
                else:  # webroot mode
                    # Start nginx to serve ACME challenges
                    nginx_started = self._start_service("nginx-edge")
                    
                    if not nginx_started:
                        # If nginx-edge failed to start and we couldn't create a temp container, fail
                        if not self._check_service_status("temp-nginx-letsencrypt"):
                            console.print(f"[bold red]{self._translate('Failed to start any nginx service for Let\'s Encrypt validation')}[/]")
                            return False
                        temp_nginx_created = True
                    
                    # Check if we can use the teddycloud-certbot container
                    certbot_exists, certbot_name = self._check_certbot_container()
                    
                    if certbot_exists and self._check_service_status(certbot_name):
                        # Use the existing certbot container
                        console.print(f"[cyan]{self._translate('Using existing certbot container')} {certbot_name}[/]")
                        
                        # Execute certbot in webroot mode using the existing container
                        cmd = [
                            "docker", "exec",
                            certbot_name,
                            "certbot", "certonly",
                            "--webroot",
                            "--webroot-path=/var/www/certbot",
                            "-v"  # Verbose output
                        ]
                    else:
                        # Create a temporary container for certbot
                        console.print(f"[cyan]{self._translate('Creating temporary certbot container')}[/]")
                        
                        # Build webroot mode command with a temporary container
                        cmd = [
                            "docker", "run", "--rm",
                            "--name", "certbot-temp",
                            "-v", "certbot_conf:/etc/letsencrypt",
                            "-v", "certbot_www:/var/www/certbot"
                        ]
                        
                        # Add certbot command
                        cmd.extend([
                            "certbot/certbot", "certonly",
                            "--webroot",
                            "--webroot-path=/var/www/certbot",
                            "-v"  # Verbose output
                        ])
                        
                        temp_container_created = True
                
                # Add staging flag if requested
                if staging:
                    cmd.append("--staging")
                    
                # Add force renewal if requested
                if force_renewal:
                    cmd.append("--force-renewal")
                    
                # Add email or register-unsafely-without-email
                if email:
                    cmd.extend(["--email", email])
                else:
                    cmd.append("--register-unsafely-without-email")
                    
                # Add agreement to Terms of Service
                cmd.append("--agree-tos")
                
                # Add domains
                for d in domains:
                    cmd.extend(["-d", d])
                
                # Print the command for debugging purposes
                console.print(f"[dim]{self._translate('Running command:')} {' '.join(cmd)}[/]")
                    
                # Run the command
                process = subprocess.run(cmd, capture_output=True, text=True)
                
                # Check result
                if process.returncode == 0:
                    console.print(f"[bold green]{self._translate('Certificate request was successful!')}[/]")
                    
                    # For webroot mode, we should reload nginx to pick up the new certificates
                    if mode == "webroot" and not temp_nginx_created:
                        self._reload_or_restart_nginx("nginx-edge")
                    
                    return True
                else:
                    error_msg = f"Certificate request failed with return code {process.returncode}"
                    console.print(f"[bold red]{self._translate(error_msg)}[/]")
                    self._display_error_details(process.stderr)
                    return False
            finally:
                # Clean up temporary resources
                if temp_nginx_created:
                    console.print(f"[cyan]{self._translate('Cleaning up temporary nginx container...')}[/]")
                    self._stop_container("temp-nginx-letsencrypt")
                
                if temp_container_created:
                    console.print(f"[cyan]{self._translate('Cleaning up temporary certbot container...')}[/]")
                    self._stop_container("certbot-temp")
                    
        except Exception as e:
            error_msg = f"Error requesting certificate: {e}"
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return False
            
    def force_refresh_certificates(self, 
                                domain: str, 
                                email: Optional[str] = None, 
                                additional_domains: Optional[List[str]] = None) -> bool:
        """
        Force refresh Let's Encrypt certificates.
        
        This is a convenience wrapper around request_certificate with force_renewal=True.
        
        Args:
            domain: Domain name for the certificate
            email: Optional email address for notifications
            additional_domains: Optional list of additional domain names (SANs)
            
        Returns:
            bool: True if successful, False otherwise
        """
        console.print(f"[bold cyan]{self._translate('Force refreshing Let\'s Encrypt certificates...')}[/]")
        
        # Use webroot mode for refreshing
        return self.request_certificate(
            domain=domain,
            mode="webroot",
            staging=False,
            email=email,
            additional_domains=additional_domains,
            force_renewal=True
        )