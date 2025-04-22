#!/usr/bin/env python3
"""
TeddyCloudWizard class for TeddyCloudStarter.
"""
import os
import time
import shutil
import re
import jinja2
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import questionary

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.table import Table
from rich import box
from rich.markdown import Markdown
from questionary import Style

from .config_manager import ConfigManager
from .docker_manager import DockerManager
from .translator import Translator
from .certificates import CertificateManager
from .utils import check_port_available, validate_domain_name, validate_ip_address
from .configurations import TEMPLATES
from .log_viewer import show_live_logs

# Global console instance for rich output
console = Console()

# Custom style for questionary
custom_style = Style([
    ('qmark', 'fg:#673ab7 bold'),       # Purple question mark
    ('question', 'bold'),               # Bold question text
    ('answer', 'fg:#4caf50 bold'),      # Green answer text
    ('pointer', 'fg:#673ab7 bold'),     # Purple pointer
    ('highlighted', 'fg:#673ab7 bold'), # Purple highlighted option
    ('selected', 'fg:#4caf50'),         # Green selected option
    ('separator', 'fg:#673ab7'),        # Purple separator
    ('instruction', 'fg:#f44336'),      # Red instruction text
])


class TeddyCloudWizard:
    """Main wizard class for TeddyCloud setup."""
    
    def __init__(self, locales_dir: Path):
        self.translator = Translator(locales_dir)
        self.config_manager = ConfigManager(translator=self.translator)
        self.docker_manager = DockerManager(translator=self.translator)
        self.cert_manager = CertificateManager(translator=self.translator)
        self.templates = TEMPLATES
    
    def refresh_server_configuration(self):
        """Refresh server configuration by renewing docker-compose.yml and nginx*.conf."""
        console.print("[bold cyan]Refreshing server configuration...[/]")

        # Create backup directory with timestamp
        timestamp = time.strftime("%Y%m%d%H%M%S")
        backup_dir = Path("backup") / timestamp
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Define files to backup and refresh
        files_to_refresh = [
            Path("data/docker-compose.yml"),
            Path("data/configurations/nginx-auth.conf"),
            Path("data/configurations/nginx-edge.conf")
        ]

        for file_path in files_to_refresh:
            if file_path.exists():
                # Backup the file
                backup_path = backup_dir / file_path.name
                shutil.copy2(file_path, backup_path)
                console.print(f"[green]Backed up {file_path} to {backup_path}[/]")
            else:
                console.print(f"[yellow]File {file_path} does not exist, skipping backup...[/]")

        # Now regenerate the configuration files based on current config
        try:
            # Generate docker-compose.yml
            if self._generate_docker_compose():
                console.print(f"[green]Successfully refreshed docker-compose.yml[/]")
            else:
                console.print(f"[bold red]Failed to refresh docker-compose.yml[/]")
            
            # Inform the user about next steps
            console.print("[bold green]Server configuration refreshed successfully![/]")
            console.print("[cyan]You may need to restart Docker services for changes to take effect.[/]")
            
            # Ask if user wants to restart services
            if questionary.confirm(
                self.translator.get("Would you like to restart Docker services now?"),
                default=True,
                style=custom_style
            ).ask():
                self.docker_manager.restart_services()
                
        except Exception as e:
            console.print(f"[bold red]Error during configuration refresh: {e}[/]")
            console.print("[yellow]Your configuration files may be incomplete. Restore from backup if needed.[/]")
            console.print(f"[yellow]Backups can be found in: {backup_dir}[/]")

    def _generate_docker_compose(self):
        """Generate docker-compose.yml based on config."""
        try:
            env = jinja2.Environment(autoescape=True)
            
            # Use the unified template
            template = env.from_string(self.templates.get("docker-compose", ""))
            
            # Create a context dictionary with all necessary variables
            context = {
                "mode": self.config_manager.config["mode"]
            }
            
            # Add mode-specific variables to context
            if self.config_manager.config["mode"] == "direct":
                context.update({
                    "admin_http": self.config_manager.config["ports"]["admin_http"],
                    "admin_https": self.config_manager.config["ports"]["admin_https"],
                    "teddycloud": self.config_manager.config["ports"]["teddycloud"]
                })
            else:  # nginx mode
                context.update({
                    "domain": self.config_manager.config["nginx"]["domain"],
                    "https_mode": self.config_manager.config["nginx"]["https_mode"],
                    "security_type": self.config_manager.config["nginx"]["security"]["type"],
                    "allowed_ips": self.config_manager.config["nginx"]["security"]["allowed_ips"]
                })
            
            rendered = template.render(**context)
            with open("data/docker-compose.yml", "w") as f:
                f.write(rendered)
            
            # Generate nginx configs if needed
            if self.config_manager.config["mode"] == "nginx":
                self._generate_nginx_configs()
            
            console.print("[bold green]Docker Compose configuration generated successfully.[/]")
            return True
        except Exception as e:
            console.print(f"[bold red]Error generating Docker Compose file: {e}[/]")
            return False
    
    def _generate_nginx_configs(self):
        """Generate nginx configuration files."""
        try:
            env = jinja2.Environment(autoescape=True)
            
            # Ensure configuration directory exists
            Path("data/configurations").mkdir(exist_ok=True)
            
            # Generate nginx-edge.conf
            edge_template = env.from_string(self.templates.get("nginx-edge", ""))
            edge_context = {
                "domain": self.config_manager.config["nginx"]["domain"],
                "https_mode": self.config_manager.config["nginx"]["https_mode"],
                "security_type": self.config_manager.config["nginx"]["security"]["type"],
                "allowed_ips": self.config_manager.config["nginx"]["security"]["allowed_ips"]
            }
            
            with open("data/configurations/nginx-edge.conf", "w") as f:
                f.write(edge_template.render(**edge_context))
            
            # Generate nginx-auth.conf if needed
            if self.config_manager.config["nginx"]["security"]["type"] == "client_cert":
                auth_template = env.from_string(self.templates.get("nginx-auth", ""))
                auth_context = {
                    "allowed_ips": self.config_manager.config["nginx"]["security"]["allowed_ips"]
                }
                
                with open("data/configurations/nginx-auth.conf", "w") as f:
                    f.write(auth_template.render(**auth_context))
            
            console.print("[bold green]Nginx configurations generated successfully.[/]")
            return True
        except Exception as e:
            console.print(f"[bold red]Error generating Nginx configurations: {e}[/]")
            return False
    
    def select_language(self):
        """Let the user select a language."""
        languages = {
            "en": "English",
            "de": "Deutsch",
            # Add more languages as they become available
        }
        
        available_langs = {k: v for k, v in languages.items() 
                          if k in self.translator.available_languages}
        
        if not available_langs:
            available_langs = {"en": "English"}
        
        choices = [f"{code}: {name}" for code, name in available_langs.items()]
        
        language_choice = questionary.select(
            self.translator.get("Select language / Sprache wählen:"),
            choices=choices,
            style=custom_style
        ).ask()
        
        if language_choice:
            lang_code = language_choice.split(':')[0].strip()
            self.translator.set_language(lang_code)
            self.config_manager.config["language"] = lang_code
            # Save the selected language in config.json
            self.config_manager.save()
    
    def show_welcome(self):
        """Show welcome message."""
        console.print(Panel(
            f"[bold blue]{self.translator.get('TeddyCloudStarter')}[/] - {self.translator.get('Docker Setup Wizard')}\n\n"
            f"{self.translator.get('This wizard will help you set up TeddyCloud with Docker.')}",
            box=box.ROUNDED,
            border_style="cyan"
        ))

    def show_develmsg(self):
        """Show developer message."""
        console.print(Panel(
            f"[bold red]{self.translator.get('WARNING')}[/] - {self.translator.get('Very early development state')}\n\n"
            f"[bold white]{self.translator.get('Keep in mind that this project is not finished yet.')}\n"
            f"[bold white]{self.translator.get('NGINX Configs are not the correct ones yet. Some features are not available.')}\n"
            f"[bold white]{self.translator.get('But it should bring you the concept of how it will work. Soon™')}",
            box=box.ROUNDED,
            border_style="red"
        ))

    def show_pre_wizard(self):
        """Show pre-wizard menu when config exists."""
        current_config = self.config_manager.config

        # Display current configuration
        table = Table(title=self.translator.get("Current Configuration"), box=box.ROUNDED)
        table.add_column(self.translator.get("Setting"), style="cyan")
        table.add_column(self.translator.get("Value"), style="green")

        table.add_row(self.translator.get("Mode"), current_config["mode"])

        if current_config["mode"] == "direct":
            for port_name, port_value in current_config["ports"].items():
                if port_value:  # Only show ports that are set
                    table.add_row(f"{self.translator.get('Port')}: {port_name}", str(port_value))
        else:  # nginx mode
            table.add_row(self.translator.get("Domain"), current_config["nginx"]["domain"])
            table.add_row(self.translator.get("HTTPS Mode"), current_config["nginx"]["https_mode"])
            table.add_row(self.translator.get("Security Type"), current_config["nginx"]["security"]["type"])
            if current_config["nginx"]["security"]["allowed_ips"]:
                table.add_row(self.translator.get("Allowed IPs"), ", ".join(current_config["nginx"]["security"]["allowed_ips"]))

        console.print(table)

        # Build choices based on config
        choices = []

        # Check if we need to add certificate management menu option
        if current_config["mode"] == "nginx" and (
            current_config["nginx"]["https_mode"] == "letsencrypt" or 
            current_config["nginx"]["security"]["type"] == "client_cert"
        ):
            choices.append(self.translator.get("Certificate management"))

        # Add standard menu options with restructured items
        choices.extend([
            self.translator.get("Configuration management"),
            self.translator.get("Docker management"),
            self.translator.get("Backup / Recovery management"),
            self.translator.get("Exit")
        ])

        # Show pre-wizard menu
        action = questionary.select(
            self.translator.get("What would you like to do?"),
            choices=choices,
            style=custom_style
        ).ask()

        if action == self.translator.get("Certificate management"):
            self.show_certificate_management_menu()
            return self.show_pre_wizard()  # Show menu again after certificate management
        elif action == self.translator.get("Configuration management"):
            result = self.show_configuration_management_menu()
            if result:  # If configuration was modified or wizard was run
                return True
            return self.show_pre_wizard()  # Show menu again
        elif action == self.translator.get("Docker management"):
            self.show_docker_management_menu()
            return self.show_pre_wizard()  # Show menu again
        elif action == self.translator.get("Backup / Recovery management"):
            self.show_backup_recovery_menu()
            return self.show_pre_wizard()  # Show menu again

        return False  # Exit
    
    def show_certificate_management_menu(self):
        """Show certificate management submenu."""
        current_config = self.config_manager.config
        choices = []
        
        # Add appropriate options based on configuration
        if current_config["mode"] == "nginx":
            if current_config["nginx"]["https_mode"] == "letsencrypt":
                choices.append(self.translator.get("Force refresh Let's Encrypt certificates"))
            
            if current_config["nginx"]["security"]["type"] == "client_cert":
                choices.append(self.translator.get("Create additional client certificate"))
                choices.append(self.translator.get("Invalidate client certificate"))
        
        # Add back option
        choices.append(self.translator.get("Back to main menu"))
        
        action = questionary.select(
            self.translator.get("Certificate Management"),
            choices=choices,
            style=custom_style
        ).ask()
        
        if action == self.translator.get("Create additional client certificate"):
            client_name = questionary.text(
                self.translator.get("Enter a name for the client certificate:"),
                default="TeddyCloudClient",
                validate=lambda text: bool(text.strip()),
                style=custom_style
            ).ask()
            self.cert_manager.generate_client_certificate(client_name)
            return self.show_certificate_management_menu()  # Show submenu again
        elif action == self.translator.get("Invalidate client certificate"):
            self.cert_manager.revoke_client_certificate()
            return self.show_certificate_management_menu()  # Show submenu again
        elif action == self.translator.get("Force refresh Let's Encrypt certificates"):
            domain = current_config["nginx"]["domain"]
            
            # Ask for email
            use_email = questionary.confirm(
                self.translator.get("Would you like to receive email notifications about certificate expiry?"),
                default=True,
                style=custom_style
            ).ask()
            
            email = None
            if use_email:
                email = questionary.text(
                    self.translator.get("Enter your email address:"),
                    validate=lambda x: re.match(r"[^@]+@[^@]+\.[^@]+", x),
                    style=custom_style
                ).ask()
            
            self.cert_manager.force_refresh_letsencrypt_certificates(domain, email)
            return self.show_certificate_management_menu()  # Show submenu again
        
        # Back to main menu or exit if no selection
        return
    
    def show_configuration_management_menu(self):
        """Show configuration management submenu."""
        choices = [
            self.translator.get("Modify specific settings"),
            self.translator.get("Run full configuration wizard"),
            self.translator.get("Delete configuration and start over"),
            self.translator.get("Refresh server configuration"),
            self.translator.get("Back to main menu")
        ]
        
        action = questionary.select(
            self.translator.get("Configuration Management"),
            choices=choices,
            style=custom_style
        ).ask()
        
        if action == self.translator.get("Modify specific settings"):
            self.show_modify_specific_settings_menu()
            return self.show_configuration_management_menu()
        elif action == self.translator.get("Run full configuration wizard"):
            self.run_wizard(is_modification=True)
            return True  # Return to main menu after modification
        elif action == self.translator.get("Delete configuration and start over"):
            if questionary.confirm(
                self.translator.get("Are you sure you want to delete the configuration and start over?"),
                default=False,
                style=custom_style
            ).ask():
                self.config_manager.delete()
                return self.run_wizard()
            return self.show_configuration_management_menu()  # Show submenu again
        elif action == self.translator.get("Refresh server configuration"):
            self.refresh_server_configuration()
            return self.show_configuration_management_menu()  # Show submenu again
        
        # Back to main menu or exit if no selection
        return False
    
    def show_modify_specific_settings_menu(self):
        """Show menu for modifying specific configuration settings."""
        current_config = self.config_manager.config
        current_mode = current_config["mode"]
        
        # Build choices based on the current configuration mode
        choices = []
        
        if current_mode == "direct":
            choices.extend([
                self.translator.get("Modify HTTP port"),
                self.translator.get("Modify HTTPS port"),
                self.translator.get("Modify TeddyCloud backend port")
            ])
        else:  # nginx mode
            choices.extend([
                self.translator.get("Modify domain name"),
                self.translator.get("Modify HTTPS mode"),
                self.translator.get("Modify security settings")
            ])
        
        choices.append(self.translator.get("Switch deployment mode (direct/nginx)"))
        choices.append(self.translator.get("Back to configuration menu"))
        
        action = questionary.select(
            self.translator.get("Select setting to modify:"),
            choices=choices,
            style=custom_style
        ).ask()
        
        if action == self.translator.get("Modify HTTP port"):
            self._modify_http_port()
        elif action == self.translator.get("Modify HTTPS port"):
            self._modify_https_port()
        elif action == self.translator.get("Modify TeddyCloud backend port"):
            self._modify_teddycloud_port()
        elif action == self.translator.get("Modify domain name"):
            self._modify_domain_name()
        elif action == self.translator.get("Modify HTTPS mode"):
            self._modify_https_mode()
        elif action == self.translator.get("Modify security settings"):
            self._modify_security_settings()
        elif action == self.translator.get("Switch deployment mode (direct/nginx)"):
            self._switch_deployment_mode()
        
        # If we're here, either we've made a change or chosen to go back
        # Save any changes that might have been made
        self.config_manager.save()
        
        # Return to configuration menu
        return
    
    def _modify_http_port(self):
        """Modify HTTP port for direct mode."""
        ports = self.config_manager.config["ports"]
        current_port = ports["admin_http"]
        
        console.print(f"[bold cyan]{self.translator.get('Current HTTP port')}: {current_port or self.translator.get('Not enabled')}[/]")
        
        use_http = questionary.confirm(
            self.translator.get("Would you like to expose the TeddyCloud Admin Web Interface on HTTP?"),
            default=current_port is not None,
            style=custom_style
        ).ask()
        
        if use_http:
            default_port = str(current_port) if current_port else "80"
            http_port = questionary.text(
                self.translator.get("Enter HTTP port:"),
                default=default_port,
                validate=lambda p: p.isdigit() and 1 <= int(p) <= 65535,
                style=custom_style
            ).ask()
            
            # If the port changed, check if it's available
            new_port = int(http_port)
            if new_port != current_port and not check_port_available(new_port):
                console.print(f"[bold yellow]{self.translator.get('Warning')}: {self.translator.get('Port')} {new_port} {self.translator.get('appears to be in use')}.[/]")
                proceed = questionary.confirm(
                    self.translator.get("Would you like to use this port anyway?"),
                    default=False,
                    style=custom_style
                ).ask()
                
                if not proceed:
                    return self._modify_http_port()
            
            ports["admin_http"] = new_port
            console.print(f"[bold green]{self.translator.get('HTTP port updated to')} {new_port}[/]")
        else:
            ports["admin_http"] = None
            console.print(f"[bold green]{self.translator.get('HTTP interface disabled')}[/]")
        
        self._generate_docker_compose()
    
    def _modify_https_port(self):
        """Modify HTTPS port for direct mode."""
        ports = self.config_manager.config["ports"]
        current_port = ports["admin_https"]
        
        console.print(f"[bold cyan]{self.translator.get('Current HTTPS port')}: {current_port or self.translator.get('Not enabled')}[/]")
        
        use_https = questionary.confirm(
            self.translator.get("Would you like to expose the TeddyCloud Admin Web Interface on HTTPS?"),
            default=current_port is not None,
            style=custom_style
        ).ask()
        
        if use_https:
            default_port = str(current_port) if current_port else "8443"
            https_port = questionary.text(
                self.translator.get("Enter HTTPS port:"),
                default=default_port,
                validate=lambda p: p.isdigit() and 1 <= int(p) <= 65535,
                style=custom_style
            ).ask()
            
            # If the port changed, check if it's available
            new_port = int(https_port)
            if new_port != current_port and not check_port_available(new_port):
                console.print(f"[bold yellow]{self.translator.get('Warning')}: {self.translator.get('Port')} {new_port} {self.translator.get('appears to be in use')}.[/]")
                proceed = questionary.confirm(
                    self.translator.get("Would you like to use this port anyway?"),
                    default=False,
                    style=custom_style
                ).ask()
                
                if not proceed:
                    return self._modify_https_port()
                    
            ports["admin_https"] = new_port
            console.print(f"[bold green]{self.translator.get('HTTPS port updated to')} {new_port}[/]")
        else:
            ports["admin_https"] = None
            console.print(f"[bold green]{self.translator.get('HTTPS interface disabled')}[/]")
        
        # Warn about admin interface accessibility
        if not ports["admin_http"] and not ports["admin_https"]:
            console.print(f"[bold red]{self.translator.get('Warning')}: {self.translator.get('You have not exposed any ports for the admin interface')}.[/]")
            confirm_no_admin = questionary.confirm(
                self.translator.get("Are you sure you want to continue without access to the admin interface?"),
                default=False,
                style=custom_style
            ).ask()
            
            if not confirm_no_admin:
                return self._modify_https_port()  # Try again
        
        self._generate_docker_compose()
    
    def _modify_teddycloud_port(self):
        """Modify TeddyCloud backend port for direct mode."""
        ports = self.config_manager.config["ports"]
        current_port = ports["teddycloud"]
        
        console.print(f"[bold cyan]{self.translator.get('Current TeddyCloud backend port')}: {current_port}[/]")
        
        default_port = str(current_port) if current_port else "443"
        tc_port = questionary.text(
            self.translator.get("Enter TeddyCloud backend port:"),
            default=default_port,
            validate=lambda p: p.isdigit() and 1 <= int(p) <= 65535,
            style=custom_style
        ).ask()
        
        # If the port changed, check if it's available
        new_port = int(tc_port)
        if new_port != current_port and not check_port_available(new_port):
            console.print(f"[bold yellow]{self.translator.get('Warning')}: {self.translator.get('Port')} {new_port} {self.translator.get('appears to be in use')}.[/]")
            proceed = questionary.confirm(
                self.translator.get("Would you like to use this port anyway?"),
                default=False,
                style=custom_style
            ).ask()
            
            if not proceed:
                return self._modify_teddycloud_port()
                
        ports["teddycloud"] = new_port
        console.print(f"[bold green]{self.translator.get('TeddyCloud backend port updated to')} {new_port}[/]")
        
        self._generate_docker_compose()
    
    def _modify_domain_name(self):
        """Modify domain name for nginx mode."""
        nginx_config = self.config_manager.config["nginx"]
        current_domain = nginx_config["domain"]
        
        console.print(f"[bold cyan]{self.translator.get('Current domain name')}: {current_domain}[/]")
        
        domain = questionary.text(
            self.translator.get("Enter the domain name for your TeddyCloud instance:"),
            default=current_domain,
            validate=lambda d: validate_domain_name(d),
            style=custom_style
        ).ask()
        
        nginx_config["domain"] = domain
        console.print(f"[bold green]{self.translator.get('Domain name updated to')} {domain}[/]")
        
        self._generate_docker_compose()
    
    def _modify_https_mode(self):
        """Modify HTTPS mode for nginx mode."""
        nginx_config = self.config_manager.config["nginx"]
        current_mode = nginx_config["https_mode"]
        
        console.print(f"[bold cyan]{self.translator.get('Current HTTPS mode')}: {current_mode}[/]")
        
        # Define the choices
        choices = [
            self.translator.get("Let's Encrypt (automatic certificates)"),
            self.translator.get("Custom certificates (provide your own)")
        ]
        
        # Determine the default choice based on current mode
        default_choice = choices[0] if current_mode == "letsencrypt" else choices[1]
        
        https_mode = questionary.select(
            self.translator.get("How would you like to handle HTTPS?"),
            choices=choices,
            default=default_choice,
            style=custom_style
        ).ask()
        
        new_mode = "letsencrypt" if https_mode.startswith(self.translator.get("Let's")) else "custom"
        
        if new_mode != current_mode:
            nginx_config["https_mode"] = new_mode
            console.print(f"[bold green]{self.translator.get('HTTPS mode updated to')} {new_mode}[/]")
            
            if new_mode == "letsencrypt":
                # Warn about Let's Encrypt requirements
                console.print(Panel(
                    f"[bold yellow]{self.translator.get('Let\'s Encrypt Requirements')}[/]\n\n"
                    f"{self.translator.get('To use Let\'s Encrypt, you need:')}\n"
                    f"1. {self.translator.get('A public domain name pointing to this server')}\n"
                    f"2. {self.translator.get('Public internet access on ports 80 and 443')}\n"
                    f"3. {self.translator.get('This server must be reachable from the internet')}",
                    box=box.ROUNDED,
                    border_style="yellow"
                ))
                
                confirm_letsencrypt = questionary.confirm(
                    self.translator.get("Do you meet these requirements?"),
                    default=True,
                    style=custom_style
                ).ask()
                
                if confirm_letsencrypt:
                    # Test if domain is properly set up
                    test_cert = questionary.confirm(
                        self.translator.get("Would you like to test if Let's Encrypt can issue a certificate for your domain?"),
                        default=True,
                        style=custom_style
                    ).ask()
                    
                    if test_cert:
                        self.cert_manager.request_letsencrypt_certificate(nginx_config["domain"])
                else:
                    # Switch back to custom mode
                    nginx_config["https_mode"] = "custom"
                    console.print(f"[bold cyan]{self.translator.get('Switching to custom certificates mode')}...[/]")
            
            if nginx_config["https_mode"] == "custom":
                console.print(Panel(
                    f"[bold cyan]{self.translator.get('Custom Certificate Instructions')}[/]\n\n"
                    f"{self.translator.get('You will need to provide your own SSL certificates.')}\n"
                    f"1. {self.translator.get('Create a directory')}: ./data/server_certs\n"
                    f"2. {self.translator.get('Place your certificate as')}: ./data/server_certs/server.crt\n"
                    f"3. {self.translator.get('Place your private key as')}: ./data/server_certs/server.key",
                    box=box.ROUNDED,
                    border_style="cyan"
                ))
                
                # Create server_certs directory if it doesn't exist
                Path("data/server_certs").mkdir(parents=True, exist_ok=True)
                
                # Check if certificates exist
                server_cert_exists = Path("data/server_certs/server.crt").exists()
                server_key_exists = Path("data/server_certs/server.key").exists()
                
                if not (server_cert_exists and server_key_exists):
                    console.print(f"[bold yellow]{self.translator.get('Certificates not found. You\'ll need to add them before starting services')}.[/]")
        
        self._generate_docker_compose()
    
    def _modify_security_settings(self):
        """Modify security settings for nginx mode."""
        nginx_config = self.config_manager.config["nginx"]
        current_security_type = nginx_config["security"]["type"]
        current_ip_restrictions = nginx_config["security"]["allowed_ips"]
        
        console.print(f"[bold cyan]{self.translator.get('Current security type')}: {current_security_type}[/]")
        if current_ip_restrictions:
            console.print(f"[bold cyan]{self.translator.get('Current allowed IPs')}: {', '.join(current_ip_restrictions)}[/]")
        
        # First, choose security type
        security_options = [
            self.translator.get("No additional security"),
            self.translator.get("Basic Authentication (.htpasswd)"),
            self.translator.get("Client Certificates"),
        ]
        
        default_idx = 0
        if current_security_type == "basic_auth":
            default_idx = 1
        elif current_security_type == "client_cert":
            default_idx = 2
        
        security_type = questionary.select(
            self.translator.get("How would you like to secure your TeddyCloud instance?"),
            choices=security_options,
            default=security_options[default_idx],
            style=custom_style
        ).ask()
        
        if security_type.startswith(self.translator.get("No")):
            new_security_type = "none"
        elif security_type.startswith(self.translator.get("Basic")):
            new_security_type = "basic_auth"
        else:  # Client Certificates
            new_security_type = "client_cert"
        
        # If security type changed, handle the new settings
        if new_security_type != current_security_type:
            nginx_config["security"]["type"] = new_security_type
            console.print(f"[bold green]{self.translator.get('Security type updated to')} {new_security_type}[/]")
            
            if new_security_type == "basic_auth":
                # Basic auth handling
                htpasswd_option = questionary.select(
                    self.translator.get("How would you like to handle the .htpasswd file?"),
                    choices=[
                        self.translator.get("I'll provide my own .htpasswd file"),
                        self.translator.get("Generate .htpasswd file with the wizard")
                    ],
                    style=custom_style
                ).ask()
                
                Path("data").mkdir(exist_ok=True)
                htpasswd_file = Path("data/.htpasswd")
                
                if htpasswd_option.startswith(self.translator.get("Generate")):
                    console.print(f"[bold cyan]{self.translator.get('Let\'s create a .htpasswd file with your users and passwords')}.[/]")
                    console.print(f"[yellow]{self.translator.get('You\'ll need to create the .htpasswd file manually at ./data/.htpasswd')}[/]")
                    console.print(f"[yellow]{self.translator.get('Please use an online .htpasswd generator or the htpasswd utility')}.[/]")
                else:
                    console.print(f"[bold cyan]{self.translator.get('Remember to place your .htpasswd file at ./data/.htpasswd')}[/]")
                
            elif new_security_type == "client_cert":
                # Client certificate handling
                cert_source = questionary.select(
                    self.translator.get("How would you like to handle client certificates?"),
                    choices=[
                        self.translator.get("I'll provide my own certificates"),
                        self.translator.get("Generate certificates for me")
                    ],
                    style=custom_style
                ).ask()
                
                if cert_source.startswith(self.translator.get("Generate")):
                    client_name = questionary.text(
                        self.translator.get("Enter a name for the client certificate:"),
                        default="TeddyCloudClient01",
                        style=custom_style
                    ).ask()
                    self.cert_manager.generate_client_certificate(client_name)
        
        # Handle IP restrictions
        modify_ip = questionary.confirm(
            self.translator.get("Would you like to modify IP address restrictions?"),
            default=bool(current_ip_restrictions),
            style=custom_style
        ).ask()
        
        if modify_ip:
            use_ip_restriction = questionary.confirm(
                self.translator.get("Would you like to restrict access by IP address?"),
                default=bool(current_ip_restrictions),
                style=custom_style
            ).ask()
            
            if use_ip_restriction:
                ip_addresses = []
                
                console.print(f"[bold cyan]{self.translator.get('Enter the IP addresses to allow (empty line to finish):')}[/]")
                console.print(f"[green]{self.translator.get('You can use individual IPs (e.g., 192.168.1.10) or CIDR notation (e.g., 192.168.1.0/24)')}[/]")
                
                # Show current IPs if any
                if current_ip_restrictions:
                    console.print(f"[bold cyan]{self.translator.get('Current allowed IPs')}:[/]")
                    for ip in current_ip_restrictions:
                        console.print(f"[cyan]{ip}[/]")
                
                # Allow adding new IPs
                while True:
                    ip = Prompt.ask(f"[bold cyan]{self.translator.get('IP address or CIDR')}[/]", default="")
                    
                    if not ip:
                        break
                    
                    if validate_ip_address(ip):
                        ip_addresses.append(ip)
                        console.print(f"[green]{self.translator.get('Added')}: {ip}[/]")
                    else:
                        console.print(f"[bold red]{self.translator.get('Invalid IP address or CIDR')}: {ip}[/]")
                
                nginx_config["security"]["allowed_ips"] = ip_addresses
                console.print(f"[bold green]{self.translator.get('IP restrictions updated')}[/]")
            else:
                nginx_config["security"]["allowed_ips"] = []
                console.print(f"[bold green]{self.translator.get('IP restrictions removed')}[/]")
        
        # Save configuration to file immediately after security settings are modified
        self.config_manager.save()
        
        self._generate_docker_compose()
    
    def _switch_deployment_mode(self):
        """Switch between direct and nginx deployment modes."""
        current_mode = self.config_manager.config["mode"]
        
        console.print(f"[bold cyan]{self.translator.get('Current deployment mode')}: {current_mode}[/]")
        
        deployment_mode = questionary.select(
            self.translator.get("Select new deployment mode:"),
            choices=[
                self.translator.get("Direct (For internal networks)"),
                self.translator.get("With Nginx (For internet-facing deployments)")
            ],
            default=0 if current_mode == "direct" else 1,
            style=custom_style
        ).ask()
        
        new_mode = "direct" if deployment_mode.startswith(self.translator.get("Direct")) else "nginx"
        
        if new_mode != current_mode:
            # Confirm the switch
            confirm = questionary.confirm(
                self.translator.get(f"Are you sure you want to switch from {current_mode} mode to {new_mode} mode? This requires reconfiguration."),
                default=False,
                style=custom_style
            ).ask()
            
            if confirm:
                self.config_manager.config["mode"] = new_mode
                console.print(f"[bold green]{self.translator.get('Deployment mode switched to')} {new_mode}[/]")
                
                # Configure based on the new mode
                if new_mode == "direct":
                    # Initialize direct mode configuration if not already present
                    if "ports" not in self.config_manager.config:
                        self.config_manager.config["ports"] = {
                            "admin_http": 80,
                            "admin_https": 8443,
                            "teddycloud": 443
                        }
                    self._configure_direct_mode()
                else:
                    # Initialize nginx mode configuration if not already present
                    if "nginx" not in self.config_manager.config:
                        self.config_manager.config["nginx"] = {
                            "domain": "",
                            "https_mode": "letsencrypt",
                            "security": {
                                "type": "none",
                                "allowed_ips": []
                            }
                        }
                    self._configure_nginx_mode()
            else:
                console.print(f"[yellow]{self.translator.get('Deployment mode switch cancelled')}[/]")
        else:
            console.print(f"[yellow]{self.translator.get('Deployment mode unchanged')}[/]")
    
    def show_backup_recovery_menu(self):
        """Show backup and recovery management submenu."""
        # Check if there are any backup files before showing the restore option
        backup_dir = os.path.join("data", "backup")
        has_backups = os.path.exists(backup_dir) and any(
            f.startswith('teddycloud-') and f.endswith('.tar.gz') 
            for f in os.listdir(backup_dir)
        ) if os.path.exists(backup_dir) else False
        
        choices = [
            self.translator.get("Backup TeddyCloudStarter Configuration"),
            self.translator.get("Backup Docker volumes")
        ]
        
        # Only show restore option if backups exist
        if has_backups:
            choices.append(self.translator.get("Restore Docker volumes"))
            
        choices.append(self.translator.get("Back to main menu"))
        
        action = questionary.select(
            self.translator.get("Backup / Recovery Management"),
            choices=choices,
            style=custom_style
        ).ask()
        
        if action == self.translator.get("Backup TeddyCloudStarter Configuration"):
            self.config_manager.backup()
            return self.show_backup_recovery_menu()  # Show submenu again
        elif action == self.translator.get("Backup Docker volumes"):
            self.show_backup_volumes_menu()
            return self.show_backup_recovery_menu()  # Show submenu again
        elif action == self.translator.get("Restore Docker volumes"):
            self.show_restore_volumes_menu()
            return self.show_backup_recovery_menu()  # Show submenu again
        
        # Back to main menu
        return
    
    def show_backup_volumes_menu(self):
        """Show menu for backing up Docker volumes."""
        # Get available Docker volumes
        volumes = self.docker_manager.get_volumes()
        
        if not volumes:
            console.print(f"[bold yellow]{self.translator.get('No Docker volumes found. Make sure Docker is running and volumes exist')}.[/]")
            return
        
        # Add option to backup all volumes
        choices = [self.translator.get("All volumes")] + volumes + [self.translator.get("Back")]
        
        selected = questionary.select(
            self.translator.get("Select a volume to backup:"),
            choices=choices,
            style=custom_style
        ).ask()
        
        if selected == self.translator.get("Back"):
            return
        
        if selected == self.translator.get("All volumes"):
            console.print(f"[bold cyan]{self.translator.get('Backing up all Docker volumes')}...[/]")
            for volume in volumes:
                self.docker_manager.backup_volume(volume)
        else:
            self.docker_manager.backup_volume(selected)
    
    def show_restore_volumes_menu(self):
        """Show menu for restoring Docker volumes."""
        # Get available Docker volumes and their backups
        volumes = self.docker_manager.get_volumes()
        all_backups = self.docker_manager.get_volume_backups()
        
        if not volumes:
            console.print(f"[bold yellow]{self.translator.get('No Docker volumes found. Make sure Docker is running and volumes exist')}.[/]")
            return
        
        if not all_backups:
            console.print(f"[bold yellow]{self.translator.get('No backup files found. Create backups first')}.[/]")
            return
        
        # Only show volumes that have backups
        volumes_with_backups = [vol for vol in volumes if vol in all_backups]
        
        if not volumes_with_backups:
            console.print(f"[bold yellow]{self.translator.get('No backups found for any of the existing volumes')}.[/]")
            return
        
        # Let user select a volume to restore
        volume_choices = volumes_with_backups + [self.translator.get("Back")]
        selected_volume = questionary.select(
            self.translator.get("Select a volume to restore:"),
            choices=volume_choices,
            style=custom_style
        ).ask()
        
        if selected_volume == self.translator.get("Back"):
            return
        
        while True:
            # Refresh the backup list to ensure we have the latest data
            all_backups = self.docker_manager.get_volume_backups()
            
            # Check if the selected volume still has backups
            if selected_volume not in all_backups or not all_backups[selected_volume]:
                console.print(f"[bold yellow]{self.translator.get('No more backups available for this volume')}.[/]")
                return self.show_restore_volumes_menu()
                
            # Get updated backup files list for the selected volume
            backup_files = all_backups[selected_volume]
            backup_choices = backup_files + [self.translator.get("Back")]
            
            # Add instructions about viewing or removing backup contents
            console.print(f"[bold cyan]{self.translator.get('Note: After selecting a backup file, you can')}:[/]")
            console.print(f"[bold cyan]- {self.translator.get('Press \'L\' to list its contents')}[/]")
            console.print(f"[bold cyan]- {self.translator.get('Press \'R\' to remove the backup file')}[/]")
            
            # Show the selection
            selected_backup = questionary.select(
                self.translator.get(f"Select a backup file for {selected_volume}:"),
                choices=backup_choices,
                style=custom_style
            ).ask()
            
            if selected_backup == self.translator.get("Back"):
                return self.show_restore_volumes_menu()
            
            # Handle key press for backup file actions
            import msvcrt
            while msvcrt.kbhit():
                msvcrt.getch()  # Clear any pending keypresses
                
            console.print(f"[bold cyan]{self.translator.get('Press \'L\' to list contents, \'R\' to remove backup, or any other key to continue')}...[/]")
            key = msvcrt.getch().decode('utf-8', errors='ignore').lower()
            
            if key == 'l':
                # Show backup contents
                self._show_backup_contents(selected_backup)
                continue  # Stay in the loop to allow another selection
            elif key == 'r':
                # Remove backup file
                if self._remove_backup_file(selected_backup):
                    # Don't need to refresh backups list here as we do it at the start of each loop iteration
                    continue  # Return to the backup selection
                else:
                    # If removal was cancelled or failed, continue loop
                    continue
            
            # Proceed with restore
            if questionary.confirm(
                self.translator.get(f"Are you sure you want to restore {selected_volume} from {selected_backup}?\n"
                f"{self.translator.get('This will overwrite current data and may require service restart')}"),
                default=False,
                style=custom_style
            ).ask():
                # Check if services are running that use this volume
                services_status = self.docker_manager.get_services_status()
                running_services = [svc for svc, info in services_status.items() if info["state"] == "Running"]
                
                if running_services:
                    console.print(f"[bold yellow]{self.translator.get('Warning: Some services are running. It\'s recommended to stop them before restoring volumes')}.[/]")
                    if questionary.confirm(
                        self.translator.get("Would you like to stop all Docker services before restoring?"),
                        default=True,
                        style=custom_style
                    ).ask():
                        self.docker_manager.stop_services()
                        console.print(f"[bold cyan]{self.translator.get('Waiting for services to stop')}...[/]")
                        time.sleep(2)
                
                # Perform the restore
                if self.docker_manager.restore_volume(selected_volume, selected_backup):
                    if questionary.confirm(
                        self.translator.get("Restore completed. Would you like to restart Docker services?"),
                        default=True,
                        style=custom_style
                    ).ask():
                        self.docker_manager.restart_services()
                break  # Exit the loop after restore is complete
            else:
                # User cancelled, ask if they want to select another backup
                if questionary.confirm(
                    self.translator.get("Would you like to select a different backup file?"),
                    default=True,
                    style=custom_style
                ).ask():
                    continue  # Stay in the loop to select another backup
                else:
                    break  # Exit the loop
    
    def _remove_backup_file(self, backup_file):
        """
        Remove a backup file after confirmation.
        
        Args:
            backup_file: Name of the backup file to remove
            
        Returns:
            bool: True if the file was removed, False otherwise
        """
        backup_path = os.path.join("data", "backup", backup_file)
        if not os.path.exists(backup_path):
            console.print(f"[bold red]{self.translator.get('Backup file')} {backup_file} {self.translator.get('not found')}.[/]")
            return False
            
        # Ask for confirmation
        if questionary.confirm(
            self.translator.get(f"Are you sure you want to permanently delete {backup_file}?"),
            default=False,
            style=custom_style
        ).ask():
            try:
                os.remove(backup_path)
                console.print(f"[bold green]{self.translator.get('Backup file')} {backup_file} {self.translator.get('removed successfully')}.[/]")
                return True
            except Exception as e:
                console.print(f"[bold red]{self.translator.get('Error removing backup file')}: {e}[/]")
                return False
        else:
            console.print(f"[yellow]{self.translator.get('Deletion cancelled')}.[/]")
            return False
    
    def _show_backup_contents(self, backup_file):
        """
        Show the contents of a backup file and wait for user to press a key.
        
        Args:
            backup_file: Name of the backup file to show contents of
        """
        console.print(f"\n[bold cyan]{self.translator.get('Showing contents of')} {backup_file}:[/]")
        self.docker_manager.show_backup_contents(backup_file)
        console.print(f"\n[bold yellow]{self.translator.get('Press Enter to continue')}...[/]")
        input()  # Wait for user to press Enter
    
    def show_docker_management_menu(self):
        """Show Docker management submenu with service status and control options."""
        # Get current status of services
        services = self.docker_manager.get_services_status()
        
        # Display service status
        if services:
            table = Table(title=self.translator.get("Docker Services Status"), box=box.ROUNDED)
            table.add_column(self.translator.get("Service"), style="cyan")
            table.add_column(self.translator.get("Status"), style="green")
            table.add_column(self.translator.get("Running For"), style="cyan")
            
            for service_name, info in services.items():
                status = info["state"]
                running_for = info["running_for"]
                status_color = "green" if status == "Running" else "yellow"
                table.add_row(service_name, f"[{status_color}]{status}[/]", running_for or "")
            
            console.print(table)
            
            # Determine which services are running and stopped
            running_services = [svc for svc, info in services.items() if info["state"] == "Running"]
            stopped_services = [svc for svc, info in services.items() if info["state"] == "Stopped"]
            
            # Determine menu options based on service status
            choices = []
            
            # Only show start all services if there are stopped services
            if stopped_services:
                if len(stopped_services) == len(services):
                    choices.append(self.translator.get("Start all services"))
                else:
                    choices.append(self.translator.get("Start stopped services"))
            
            # Only show restart all services if all services are running
            if len(running_services) == len(services) and running_services:
                choices.append(self.translator.get("Restart all services"))
            
            # Only show stop all services if all services are running
            if running_services and len(running_services) == len(services):
                choices.append(self.translator.get("Stop all services"))
            # Show stop specific service if any services are running
            elif running_services:
                choices.append(self.translator.get("Stop specific service"))
                
            # Show start specific service if any services are stopped
            if stopped_services:
                choices.append(self.translator.get("Start specific service"))
                
            # Show restart specific service if at least one service is running
            if running_services:
                choices.append(self.translator.get("Restart specific service"))

            # Log options - show only if at least one service is running
            if running_services:
                choices.append(self.translator.get("Live logs from all services"))
                choices.append(self.translator.get("Live logs from specific service"))
        else:
            console.print(f"[yellow]{self.translator.get('No Docker services found or Docker is not available')}.[/]")
            choices = []
            
        # Always include Refresh status and Back options
        choices.append(self.translator.get("Refresh status"))
        choices.append(self.translator.get("Back to main menu"))
        
        action = questionary.select(
            self.translator.get("Docker Management"),
            choices=choices,
            style=custom_style
        ).ask()
        
        if action == self.translator.get("Start all services") or action == self.translator.get("Start stopped services"):
            self.docker_manager.start_services()
            console.print(f"[bold cyan]{self.translator.get('Refreshing service status')}...[/]")
            # Wait a moment for Docker to start the services
            time.sleep(2)
            return self.show_docker_management_menu()  # Reload menu with fresh status
            
        elif action == self.translator.get("Restart all services"):
            self.docker_manager.restart_services()
            console.print(f"[bold cyan]{self.translator.get('Refreshing service status')}...[/]")
            # Wait a moment for Docker to restart the services
            time.sleep(2)
            return self.show_docker_management_menu()  # Reload menu with fresh status
        
        elif action == self.translator.get("Stop all services"):
            self.docker_manager.stop_services()
            console.print(f"[bold cyan]{self.translator.get('Refreshing service status')}...[/]")
            # Wait a moment for Docker to stop the services
            time.sleep(2)
            return self.show_docker_management_menu()  # Reload menu with fresh status
            
        elif action == self.translator.get("Start specific service"):
            if not stopped_services:
                console.print(f"[bold yellow]{self.translator.get('No stopped services available to start')}.[/]")
                return self.show_docker_management_menu()
            
            service_choices = stopped_services + [self.translator.get("Back")]
            
            selected_service = questionary.select(
                self.translator.get("Select a service to start:"),
                choices=service_choices,
                style=custom_style
            ).ask()
            
            if selected_service and selected_service != self.translator.get("Back"):
                self.docker_manager.start_service(selected_service)
                console.print(f"[bold cyan]{self.translator.get('Refreshing service status')}...[/]")
                # Wait a moment for Docker to start the service
                time.sleep(2)
            
            return self.show_docker_management_menu()  # Reload menu with fresh status
            
        elif action == self.translator.get("Restart specific service"):
            if not running_services:
                console.print(f"[bold yellow]{self.translator.get('No running services available to restart')}.[/]")
                return self.show_docker_management_menu()
            
            service_choices = running_services + [self.translator.get("Back")]
            
            selected_service = questionary.select(
                self.translator.get("Select a service to restart:"),
                choices=service_choices,
                style=custom_style
            ).ask()
            
            if selected_service and selected_service != self.translator.get("Back"):
                self.docker_manager.restart_service(selected_service)
                console.print(f"[bold cyan]{self.translator.get('Refreshing service status')}...[/]")
                # Wait a moment for Docker to restart the service
                time.sleep(2)
            
            return self.show_docker_management_menu()  # Reload menu with fresh status
            
        elif action == self.translator.get("Stop specific service"):
            if not running_services:
                console.print(f"[bold yellow]{self.translator.get('No running services available to stop')}.[/]")
                return self.show_docker_management_menu()
            
            service_choices = running_services + [self.translator.get("Back")]
            
            selected_service = questionary.select(
                self.translator.get("Select a service to stop:"),
                choices=service_choices,
                style=custom_style
            ).ask()
            
            if selected_service and selected_service != self.translator.get("Back"):
                self.docker_manager.stop_service(selected_service)
                console.print(f"[bold cyan]{self.translator.get('Refreshing service status')}...[/]")
                # Wait a moment for Docker to stop the service
                time.sleep(2)
            
            return self.show_docker_management_menu()  # Reload menu with fresh status

        elif action == self.translator.get("Live logs from all services"):
            # Use the new log_viewer module to show logs from all services
            show_live_logs(self.docker_manager)
            return self.show_docker_management_menu()  # Return to Docker management menu
            
        elif action == self.translator.get("Live logs from specific service"):
            if not running_services:
                console.print(f"[bold yellow]{self.translator.get('No running services available to view logs')}.[/]")
                return self.show_docker_management_menu()
            
            service_choices = running_services + [self.translator.get("Back")]
            
            selected_service = questionary.select(
                self.translator.get("Select a service to view logs:"),
                choices=service_choices,
                style=custom_style
            ).ask()
            
            if selected_service and selected_service != self.translator.get("Back"):
                # Use the new log_viewer module to show logs for the specific service
                show_live_logs(self.docker_manager, selected_service)
            
            return self.show_docker_management_menu()  # Return to Docker management menu
            
        elif action == self.translator.get("Refresh status"):
            console.print(f"[bold cyan]{self.translator.get('Refreshing service status')}...[/]")
            return self.show_docker_management_menu()  # Reload menu with fresh status
        
        # Back to main menu
        return
    
    def run_wizard(self, is_modification=False):
        """Run the main wizard."""
        # If it's a modification, we don't need to ask about everything again
        if not is_modification:
            # Choose deployment mode
            deployment_mode = questionary.select(
                self.translator.get("How would you like to deploy TeddyCloud?"),
                choices=[
                    self.translator.get("Direct (For internal networks)"),
                    self.translator.get("With Nginx (For internet-facing deployments)")
                ],
                style=custom_style
            ).ask()
            
            self.config_manager.config["mode"] = "direct" if deployment_mode.startswith(self.translator.get("Direct")) else "nginx"
        
        # Configure based on mode
        if self.config_manager.config["mode"] == "direct":
            self._configure_direct_mode()
        else:
            self._configure_nginx_mode()
        
        # Save configuration
        self.config_manager.save()
        
        # Generate Docker Compose and other files
        if self._generate_docker_compose():
            console.print(f"[bold green]{self.translator.get('Setup complete')}![/]")
            
            # Ask to start services
            if questionary.confirm(
                self.translator.get("Would you like to start the Docker services now?"),
                default=True,
                style=custom_style
            ).ask():
                self.docker_manager.restart_services()
        
        return True
    
    def _configure_direct_mode(self):
        """Configure direct deployment mode."""
        ports = self.config_manager.config["ports"]
        
        # Ask about HTTP port
        use_http = questionary.confirm(
            self.translator.get("Would you like to expose the TeddyCloud Admin Web Interface on HTTP (port 80)?"),
            default=True,
            style=custom_style
        ).ask()
        
        if use_http:
            port_80_available = check_port_available(80)
            if not port_80_available:
                console.print(f"[bold yellow]{self.translator.get('Warning')}: {self.translator.get('Port 80 appears to be in use')}.[/]")
                custom_port = questionary.confirm(
                    self.translator.get("Would you like to specify a different port?"),
                    default=True,
                    style=custom_style
                ).ask()
                
                if custom_port:
                    http_port = questionary.text(
                        self.translator.get("Enter HTTP port:"),
                        default="8080",
                        validate=lambda p: p.isdigit() and 1 <= int(p) <= 65535,
                        style=custom_style
                    ).ask()
                    ports["admin_http"] = int(http_port)
                else:
                    ports["admin_http"] = 80
            else:
                ports["admin_http"] = 80
        else:
            ports["admin_http"] = None
        
        # Ask about HTTPS port
        use_https = questionary.confirm(
            self.translator.get("Would you like to expose the TeddyCloud Admin Web Interface on HTTPS (port 8443)?"),
            default=True,
            style=custom_style
        ).ask()
        
        if use_https:
            port_8443_available = check_port_available(8443)
            if not port_8443_available:
                console.print(f"[bold yellow]{self.translator.get('Warning')}: {self.translator.get('Port 8443 appears to be in use')}.[/]")
                custom_port = questionary.confirm(
                    self.translator.get("Would you like to specify a different port?"),
                    default=True,
                    style=custom_style
                ).ask()
                
                if custom_port:
                    https_port = questionary.text(
                        self.translator.get("Enter HTTPS port:"),
                        default="8444",
                        validate=lambda p: p.isdigit() and 1 <= int(p) <= 65535,
                        style=custom_style
                    ).ask()
                    ports["admin_https"] = int(https_port)
                else:
                    ports["admin_https"] = 8443
            else:
                ports["admin_https"] = 8443
        else:
            ports["admin_https"] = None
        
        # Configure Toniebox port (443)
        port_443_available = check_port_available(443)
        if not port_443_available:
            console.print(f"[bold yellow]{self.translator.get('Warning')}: {self.translator.get('Port 443 appears to be in use')}.[/]")
            custom_port = questionary.confirm(
                self.translator.get("Would you like to specify a different port for TeddyCloud backend (normally 443)?"),
                default=True,
                style=custom_style
            ).ask()
            
            if custom_port:
                tc_port = questionary.text(
                    self.translator.get("Enter TeddyCloud backend port:"),
                    default="4443",
                    validate=lambda p: p.isdigit() and 1 <= int(p) <= 65535,
                    style=custom_style
                ).ask()
                ports["teddycloud"] = int(tc_port)
            else:
                ports["teddycloud"] = 443
        else:
            ports["teddycloud"] = 443
        
        # Warn about admin interface accessibility
        if not ports["admin_http"] and not ports["admin_https"]:
            console.print(f"[bold red]{self.translator.get('Warning')}: {self.translator.get('You have not exposed any ports for the admin interface')}.[/]")
            confirm_no_admin = questionary.confirm(
                self.translator.get("Are you sure you want to continue without access to the admin interface?"),
                default=False,
                style=custom_style
            ).ask()
            
            if not confirm_no_admin:
                return self._configure_direct_mode()  # Start over
    
    def _configure_nginx_mode(self):
        """Configure nginx deployment mode."""
        nginx_config = self.config_manager.config["nginx"]
        
        # Check if ports 80 and 443 are available
        port_80_available = check_port_available(80)
        port_443_available = check_port_available(443)
        
        if not port_80_available:
            console.print(f"[bold yellow]{self.translator.get('Warning')}: {self.translator.get('Port 80 appears to be in use. This is required for Nginx')}.[/]")
        
        if not port_443_available:
            console.print(f"[bold yellow]{self.translator.get('Warning')}: {self.translator.get('Port 443 appears to be in use. This is required for Nginx')}.[/]")
        
        if not port_80_available or not port_443_available:
            continue_anyway = questionary.confirm(
                self.translator.get("Do you want to continue anyway?"),
                default=False,
                style=custom_style
            ).ask()
            
            if not continue_anyway:
                return
        
        # Ask for domain
        domain = questionary.text(
            self.translator.get("Enter the domain name for your TeddyCloud instance:"),
            validate=lambda d: validate_domain_name(d),
            style=custom_style
        ).ask()
        
        nginx_config["domain"] = domain
        
        # Ask about HTTPS
        https_mode = questionary.select(
            self.translator.get("How would you like to handle HTTPS?"),
            choices=[
                self.translator.get("Let's Encrypt (automatic certificates)"),
                self.translator.get("Custom certificates (provide your own)")
            ],
            style=custom_style
        ).ask()
        
        nginx_config["https_mode"] = "letsencrypt" if https_mode.startswith(self.translator.get("Let's")) else "custom"
        
        if nginx_config["https_mode"] == "letsencrypt":
            # Warn about Let's Encrypt requirements
            console.print(Panel(
                f"[bold yellow]{self.translator.get('Let\'s Encrypt Requirements')}[/]\n\n"
                f"{self.translator.get('To use Let\'s Encrypt, you need:')}\n"
                f"1. {self.translator.get('A public domain name pointing to this server')}\n"
                f"2. {self.translator.get('Public internet access on ports 80 and 443')}\n"
                f"3. {self.translator.get('This server must be reachable from the internet')}",
                box=box.ROUNDED,
                border_style="yellow"
            ))
            
            confirm_letsencrypt = questionary.confirm(
                self.translator.get("Do you meet these requirements?"),
                default=True,
                style=custom_style
            ).ask()
            
            if confirm_letsencrypt:
                # Test if domain is properly set up
                test_cert = questionary.confirm(
                    self.translator.get("Would you like to test if Let's Encrypt can issue a certificate for your domain?"),
                    default=True,
                    style=custom_style
                ).ask()
                
                if test_cert:
                    self.cert_manager.request_letsencrypt_certificate(domain)
            else:
                # Switch to custom mode
                nginx_config["https_mode"] = "custom"
                console.print(f"[bold cyan]{self.translator.get('Switching to custom certificates mode')}...[/]")
        
        if nginx_config["https_mode"] == "custom":
            console.print(Panel(
                f"[bold cyan]{self.translator.get('Custom Certificate Instructions')}[/]\n\n"
                f"{self.translator.get('You will need to provide your own SSL certificates.')}\n"
                f"1. {self.translator.get('Create a directory')}: ./data/server_certs\n"
                f"2. {self.translator.get('Place your certificate as')}: ./data/server_certs/server.crt\n"
                f"3. {self.translator.get('Place your private key as')}: ./data/server_certs/server.key",
                box=box.ROUNDED,
                border_style="cyan"
            ))
            
            # Create server_certs directory if it doesn't exist
            Path("data/server_certs").mkdir(parents=True, exist_ok=True)
            
            # Check if certificates exist
            server_cert_exists = Path("data/server_certs/server.crt").exists()
            server_key_exists = Path("data/server_certs/server.key").exists()
            
            if not (server_cert_exists and server_key_exists):
                console.print(f"[bold yellow]{self.translator.get('Certificates not found. You\'ll need to add them before starting services')}.[/]")
        
        # Configure security
        security_type = questionary.select(
            self.translator.get("How would you like to secure your TeddyCloud instance?"),
            choices=[
                self.translator.get("No additional security"),
                self.translator.get("Basic Authentication (.htpasswd)"),
                self.translator.get("Client Certificates"),
            ],
            style=custom_style
        ).ask()
        
        if security_type.startswith(self.translator.get("No")):
            nginx_config["security"]["type"] = "none"
        elif security_type.startswith(self.translator.get("Basic")):
            nginx_config["security"]["type"] = "basic_auth"
            
            # Ask if user wants to provide their own .htpasswd or generate one
            htpasswd_option = questionary.select(
                self.translator.get("How would you like to handle the .htpasswd file?"),
                choices=[
                    self.translator.get("I'll provide my own .htpasswd file"),
                    self.translator.get("Generate .htpasswd file with the wizard")
                ],
                style=custom_style
            ).ask()
            
            Path("data").mkdir(exist_ok=True)
            htpasswd_file = Path("data/.htpasswd")
            
            # Handle htpasswd creation choice
            if htpasswd_option == self.translator.get("Generate .htpasswd file with the wizard"):
                console.print(f"[bold cyan]{self.translator.get('Let\'s create a .htpasswd file with your users and passwords')}.[/]")
                
                # Helper code for generating .htpasswd
                console.print(f"[yellow]{self.translator.get('You\'ll need to create the .htpasswd file manually at ./data/.htpasswd')}[/]")
                console.print(f"[yellow]{self.translator.get('Please use an online .htpasswd generator or the htpasswd utility')}.[/]")
            else:
                console.print(f"[bold cyan]{self.translator.get('Remember to place your .htpasswd file at ./data/.htpasswd')}[/]")
        else:  # Client Certificates
            nginx_config["security"]["type"] = "client_cert"
            
            cert_source = questionary.select(
                self.translator.get("How would you like to handle client certificates?"),
                choices=[
                    self.translator.get("I'll provide my own certificates"),
                    self.translator.get("Generate certificates for me")
                ],
                style=custom_style
            ).ask()
            
            if cert_source.startswith(self.translator.get("Generate")):
                client_name = questionary.text(
                    self.translator.get("Enter a name for the client certificate:"),
                    default="TeddyCloudClient01",
                    style=custom_style
                ).ask()
                self.cert_manager.generate_client_certificate(client_name)
        
        # Ask about IP restrictions
        use_ip_restriction = questionary.confirm(
            self.translator.get("Would you like to restrict access by IP address?"),
            default=False,
            style=custom_style
        ).ask()
        
        if use_ip_restriction:
            ip_addresses = []
            
            console.print(f"[bold cyan]{self.translator.get('Enter the IP addresses to allow (empty line to finish):')}[/]")
            console.print(f"[green]{self.translator.get('You can use individual IPs (e.g., 192.168.1.10) or CIDR notation (e.g., 192.168.1.0/24)')}[/]")
            
            while True:
                ip = Prompt.ask(f"[bold cyan]{self.translator.get('IP address or CIDR')}[/]", default="")
                
                if not ip:
                    break
                
                if validate_ip_address(ip):
                    ip_addresses.append(ip)
                    console.print(f"[green]{self.translator.get('Added')}: {ip}[/]")
                else:
                    console.print(f"[bold red]{self.translator.get('Invalid IP address or CIDR')}: {ip}[/]")
            
            nginx_config["security"]["allowed_ips"] = ip_addresses
            console.print(f"[bold green]{self.translator.get('IP restrictions updated')}[/]")
        
        self._generate_docker_compose()
