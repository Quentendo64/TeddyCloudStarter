#!/usr/bin/env python3
"""
Main wizard module for TeddyCloudStarter.
"""
import os
import time
import shutil
from pathlib import Path
import questionary

# Import our modules - use relative imports to avoid circular dependencies
from .wizard.base_wizard import BaseWizard
from .wizard.ui_helpers import console, custom_style, show_welcome_message, show_development_message, display_configuration_table
from .configuration.generator import generate_docker_compose, generate_nginx_configs
from .configuration.direct_mode import configure_direct_mode, modify_http_port, modify_https_port, modify_teddycloud_port
from .configuration.nginx_mode import (configure_nginx_mode, modify_domain_name, modify_https_mode, 
                                      modify_security_settings)
from .ui.certificate_manager_ui import show_certificate_management_menu
from .ui.docker_manager_ui import show_docker_management_menu
from .ui.backup_manager_ui import show_backup_recovery_menu
from .ui.configuration_manager_ui import show_configuration_management_menu
from .utilities.file_system import browse_directory


class TeddyCloudWizard(BaseWizard):
    """Main wizard class for TeddyCloud setup."""
    
    def refresh_server_configuration(self):
        """Refresh server configuration by renewing docker-compose.yml and nginx*.conf."""
        console.print("[bold cyan]Refreshing server configuration...[/]")

        # Get the project path from config
        project_path = self.config_manager.config.get("environment", {}).get("path")
        if not project_path:
            console.print(f"[bold yellow]{self.translator.get('Warning')}: {self.translator.get('No project path set. Using current directory.')}[/]")
            project_path = os.getcwd()
        
        # Create base Path object for project
        base_path = Path(project_path)
        
        # Create backup directory with timestamp
        timestamp = time.strftime("%Y%m%d%H%M%S")
        backup_dir = Path("backup") / timestamp
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Define files to backup and refresh with absolute paths
        files_to_refresh = [
            base_path / "data" / "docker-compose.yml",
            base_path / "data" / "configurations" / "nginx-auth.conf",
            base_path / "data" / "configurations" / "nginx-edge.conf"
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
            if generate_docker_compose(self.config_manager.config, self.translator, self.templates):
                console.print(f"[green]Successfully refreshed docker-compose.yml[/]")
            else:
                console.print(f"[bold red]Failed to refresh docker-compose.yml[/]")
            
            # Generate nginx config files if in nginx mode
            if self.config_manager.config["mode"] == "nginx":
                if generate_nginx_configs(self.config_manager.config, self.translator, self.templates):
                    console.print(f"[green]Successfully refreshed nginx configuration files[/]")
                else:
                    console.print(f"[bold red]Failed to refresh nginx configuration files[/]")
            
            # Inform the user about next steps
            console.print("[bold green]Server configuration refreshed successfully![/]")
            console.print("[cyan]You may need to restart Docker services for changes to take effect.[/]")
            
            # Ask if user wants to restart services
            if questionary.confirm(
                self.translator.get("Would you like to restart Docker services now?"),
                default=True,
                style=custom_style
            ).ask():
                # Get the project path from config and pass it to the docker manager
                self.docker_manager.restart_services(project_path=project_path)
                
        except Exception as e:
            console.print(f"[bold red]Error during configuration refresh: {e}[/]")
            console.print("[yellow]Your configuration files may be incomplete. Restore from backup if needed.[/]")
            console.print(f"[yellow]Backups can be found in: {backup_dir}[/]")
    
    def show_application_management_menu(self):
        """Show application management submenu."""
        from .ui.application_manager_ui import show_application_management_menu
        
        # Pass config_manager to ensure project path is available
        exit_menu = show_application_management_menu(self.config_manager, self.docker_manager, self.translator)
        if not exit_menu:
            return self.show_pre_wizard_menu()  # Show menu again after application management
        else:
            return True  # Return to main menu
            
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
    
    def display_welcome_message(self):
        """Show welcome message."""
        show_welcome_message(self.translator)

    def display_development_message(self):
        """Show developer message."""
        show_development_message(self.translator)

    def show_pre_wizard_menu(self):
        """Show pre-wizard menu when config exists."""
        current_config = self.config_manager.config

        # Display current configuration - check if config is valid
        config_valid = display_configuration_table(current_config, self.translator)

        # If configuration is corrupt, offer only limited options
        if not config_valid:
            choices = [
                self.translator.get("Reset configuration and start over"),
                self.translator.get("Exit")
            ]
            
            action = questionary.select(
                self.translator.get("Configuration is corrupt. What would you like to do?"),
                choices=choices,
                style=custom_style
            ).ask()
            
            if action == self.translator.get("Reset configuration and start over"):
                self.config_manager.delete()
                return self.execute_wizard()
                
            return False  # Exit

        # Build menu choices
        choices = []

        # Add standard menu options
        menu_options = [
            self.translator.get("Application management"),
            self.translator.get("Backup / Recovery management"),
            self.translator.get("Configuration management"),
            self.translator.get("Docker management"),
            self.translator.get("Exit")
        ]
        
        # Add Certificate management option conditionally
        if (current_config.get("mode") == "nginx" and 
            "nginx" in current_config and
            ((current_config["nginx"].get("https_mode") == "letsencrypt") or 
             ("security" in current_config["nginx"] and 
              current_config["nginx"]["security"].get("type") == "client_cert"))
        ):
            menu_options.insert(0, self.translator.get("Certificate management"))

        # Sort menu options alphabetically (except "Exit" which should always be last)
        exit_option = self.translator.get("Exit")
        menu_options.remove(exit_option)
        menu_options.sort()  # Sort alphabetically
        menu_options.append(exit_option)  # Add Exit as the last option
        
        choices.extend(menu_options)

        # Show pre-wizard menu
        action = questionary.select(
            self.translator.get("What would you like to do?"),
            choices=choices,
            style=custom_style
        ).ask()

        if action == self.translator.get("Certificate management"):
            # Create a dictionary of security managers to pass to the certificate management menu
            security_managers = {
                "ca_manager": self.ca_manager,
                "client_cert_manager": self.client_cert_manager,
                "lets_encrypt_manager": self.lets_encrypt_manager
            }
            
            exit_menu = show_certificate_management_menu(self.config_manager.config, self.translator, security_managers)
            if not exit_menu:
                return self.show_pre_wizard_menu()  # Show menu again after certificate management
            else:
                return self.show_pre_wizard_menu()  # Return to the main menu when "Back to main menu" was selected
            
        elif action == self.translator.get("Configuration management"):
            # Create a dictionary of security managers to pass to the configuration management menu
            security_managers = {
                "ca_manager": self.ca_manager,
                "client_cert_manager": self.client_cert_manager,
                "lets_encrypt_manager": self.lets_encrypt_manager,
                "ip_restrictions_manager": self.ip_restrictions_manager
            }
            
            result = show_configuration_management_menu(self, self.config_manager, self.translator, security_managers)
            if result:  # If configuration was modified or wizard was run
                return True
            return self.show_pre_wizard_menu()  # Show menu again
            
        elif action == self.translator.get("Docker management"):
            # Pass config_manager to ensure project path is available for Docker operations
            exit_menu = show_docker_management_menu(self.translator, self.docker_manager, self.config_manager)
            if not exit_menu:
                return self.show_pre_wizard_menu()  # Show menu again
            else:
                return True  # Return to main menu
                
        elif action == self.translator.get("Application management"):
            return self.show_application_management_menu()
                
        elif action == self.translator.get("Backup / Recovery management"):
            exit_menu = show_backup_recovery_menu(self.config_manager, self.docker_manager, self.translator)
            if not exit_menu:
                return self.show_pre_wizard_menu()  # Show menu again
            else:
                return self.show_pre_wizard_menu()  # Return to the main menu when "Back to main menu" was selected

        return False  # Exit

    def execute_wizard(self):
        """Run the main configuration wizard to set up TeddyCloud."""
        console.print(f"[bold cyan]{self.translator.get('Starting TeddyCloud setup wizard')}...[/]")

        # Step 1: Select project path if not already set
        if not self.config_manager.config.get("environment", {}).get("path"):
            self.select_project_path()

        # Step 2: Select deployment mode
        self.select_deployment_mode()
        
        # Step 3: Configure selected deployment mode
        if self.config_manager.config["mode"] == "direct":
            self.configure_direct_mode()
        elif self.config_manager.config["mode"] == "nginx":
            self.configure_nginx_mode()
            
        # Save the configuration
        self.config_manager.save()
        
        console.print(f"[bold green]{self.translator.get('Configuration completed successfully!')}[/]")
        
        # Generate configuration files automatically
        console.print(f"[bold cyan]{self.translator.get('Generating configuration files')}...[/]")
        
        # Generate docker-compose.yml file
        if generate_docker_compose(self.config_manager.config, self.translator, self.templates):
            console.print(f"[green]{self.translator.get('Successfully generated docker-compose.yml')}[/]")
        else:
            console.print(f"[bold red]{self.translator.get('Failed to generate docker-compose.yml')}[/]")
        
        # Generate nginx configuration files if in nginx mode
        if self.config_manager.config["mode"] == "nginx":
            if generate_nginx_configs(self.config_manager.config, self.translator, self.templates):
                console.print(f"[green]{self.translator.get('Successfully generated nginx configuration files')}[/]")
            else:
                console.print(f"[bold red]{self.translator.get('Failed to generate nginx configuration files')}[/]")
        
        console.print(f"[bold green]{self.translator.get('Configuration files generated successfully!')}[/]")
        
        # Show the main menu after wizard completes
        return self.show_pre_wizard_menu()
        
    def select_project_path(self):
        """Let the user select a project path."""
        console.print(f"[bold cyan]{self.translator.get('Please select a directory for your TeddyCloud project')}[/]")
        console.print(f"[cyan]{self.translator.get('This directory will store all Docker volumes, certificates, and configuration files.')}[/]")
        
        # Start with current directory as default
        current_dir = os.getcwd()
        
        # Let user browse for a directory
        selected_path = browse_directory(
            start_path=current_dir,
            title=self.translator.get("Select TeddyCloud Project Directory"),
            translator=self.translator
        )
        
        if selected_path:
            # Update config with selected path
            if "environment" not in self.config_manager.config:
                self.config_manager.config["environment"] = {}
            
            self.config_manager.config["environment"]["path"] = selected_path
            console.print(f"[green]{self.translator.get('Project path set to')}: {selected_path}[/]")
            
            # Save configuration
            self.config_manager.save()
        else:
            # Use current directory as fallback
            if "environment" not in self.config_manager.config:
                self.config_manager.config["environment"] = {}
                
            self.config_manager.config["environment"]["path"] = current_dir
            console.print(f"[yellow]{self.translator.get('No path selected. Using current directory')}: {current_dir}[/]")
            
            # Save configuration
            self.config_manager.save()
    
    def select_deployment_mode(self):
        """Let the user select a deployment mode."""
        choices = [
            self.translator.get("Direct mode (Simplest, all services on one machine)"),
            self.translator.get("Nginx mode (Advanced, uses nginx for routing)")
        ]
        
        mode_choice = questionary.select(
            self.translator.get("Select a deployment mode:"),
            choices=choices,
            style=custom_style
        ).ask()
        
        if mode_choice.startswith(self.translator.get("Direct mode")):
            self.config_manager.config["mode"] = "direct"
        else:
            self.config_manager.config["mode"] = "nginx"
            
        console.print(f"[green]{self.translator.get('Deployment mode set to')}: {self.config_manager.config['mode']}[/]")
        
        # Save the configuration
        self.config_manager.save()
    
    def configure_direct_mode(self):
        """Configure direct deployment mode settings."""
        security_managers = {
            "ca_manager": self.ca_manager,
            "client_cert_manager": self.client_cert_manager,
            "lets_encrypt_manager": self.lets_encrypt_manager
        }
        configure_direct_mode(self.config_manager.config, self.translator)
        self.config_manager.save()
    
    def configure_nginx_mode(self):
        """Configure Nginx deployment mode settings."""
        security_managers = {
            "ca_manager": self.ca_manager,
            "client_cert_manager": self.client_cert_manager,
            "lets_encrypt_manager": self.lets_encrypt_manager,
            "basic_auth_manager": self.basic_auth_manager,
            "ip_restrictions_manager": self.ip_restrictions_manager,
            "auth_bypass_manager": self.auth_bypass_manager
        }
        configure_nginx_mode(self.config_manager.config, self.translator, security_managers)
        self.config_manager.save()
