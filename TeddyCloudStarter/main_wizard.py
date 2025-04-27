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
from .management.certificate_manager_ui import show_certificate_management_menu
from .management.docker_manager_ui import show_docker_management_menu
from .management.backup_manager_ui import show_backup_recovery_menu
from .file_browser import browse_directory


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
        from .management.application_manager_ui import show_application_management_menu
        
        # Pass config_manager to ensure project path is available
        exit_menu = show_application_management_menu(self.config_manager, self.docker_manager, self.translator)
        if not exit_menu:
            return self.show_pre_wizard()  # Show menu again after application management
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
    
    def show_welcome(self):
        """Show welcome message."""
        show_welcome_message(self.translator)

    def show_develmsg(self):
        """Show developer message."""
        show_development_message(self.translator)

    def show_pre_wizard(self):
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
                return self.run_wizard()
                
            return False  # Exit

        # Build choices based on config
        choices = []

        if (current_config.get("mode") == "nginx" and 
            "nginx" in current_config and
            ((current_config["nginx"].get("https_mode") == "letsencrypt") or 
             ("security" in current_config["nginx"] and 
              current_config["nginx"]["security"].get("type") == "client_cert"))
        ):
            choices.append(self.translator.get("Certificate management"))

        # Add standard menu options with restructured items
        choices.extend([
            self.translator.get("Configuration management"),
            self.translator.get("Docker management"),
            self.translator.get("Application management"),
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
            exit_menu = show_certificate_management_menu(self.config_manager.config, self.translator, self.cert_manager)
            if not exit_menu:
                return self.show_pre_wizard()  # Show menu again after certificate management
            
        elif action == self.translator.get("Configuration management"):
            result = self.show_configuration_management_menu()
            if result:  # If configuration was modified or wizard was run
                return True
            return self.show_pre_wizard()  # Show menu again
            
        elif action == self.translator.get("Docker management"):
            # Pass config_manager to ensure project path is available for Docker operations
            exit_menu = show_docker_management_menu(self.translator, self.docker_manager, self.config_manager)
            if not exit_menu:
                return self.show_pre_wizard()  # Show menu again
            else:
                return True  # Return to main menu
                
        elif action == self.translator.get("Application management"):
            return self.show_application_management_menu()
                
        elif action == self.translator.get("Backup / Recovery management"):
            exit_menu = show_backup_recovery_menu(self.config_manager, self.docker_manager, self.translator)
            if not exit_menu:
                return self.show_pre_wizard()  # Show menu again
            else:
                return self.show_pre_wizard()  # Return to the main menu when "Back to main menu" was selected

        return False  # Exit
    
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
            self.config_manager.config = modify_http_port(self.config_manager.config, self.translator)
            generate_docker_compose(self.config_manager.config, self.translator, self.templates)
            
        elif action == self.translator.get("Modify HTTPS port"):
            self.config_manager.config = modify_https_port(self.config_manager.config, self.translator)
            generate_docker_compose(self.config_manager.config, self.translator, self.templates)
            
        elif action == self.translator.get("Modify TeddyCloud backend port"):
            self.config_manager.config = modify_teddycloud_port(self.config_manager.config, self.translator)
            generate_docker_compose(self.config_manager.config, self.translator, self.templates)
            
        elif action == self.translator.get("Modify domain name"):
            self.config_manager.config = modify_domain_name(self.config_manager.config, self.translator)
            generate_docker_compose(self.config_manager.config, self.translator, self.templates)
            generate_nginx_configs(self.config_manager.config, self.translator, self.templates)
            
        elif action == self.translator.get("Modify HTTPS mode"):
            self.config_manager.config = modify_https_mode(self.config_manager.config, self.translator, self.cert_manager)
            generate_docker_compose(self.config_manager.config, self.translator, self.templates)
            generate_nginx_configs(self.config_manager.config, self.translator, self.templates)
            
        elif action == self.translator.get("Modify security settings"):
            self.config_manager.config = modify_security_settings(self.config_manager.config, self.translator, self.cert_manager)
            generate_docker_compose(self.config_manager.config, self.translator, self.templates)
            generate_nginx_configs(self.config_manager.config, self.translator, self.templates)
            
        elif action == self.translator.get("Switch deployment mode (direct/nginx)"):
            self._switch_deployment_mode()
        
        # If we're here, either we've made a change or chosen to go back
        # Save any changes that might have been made
        self.config_manager.save()
        
        # Return to configuration menu
        return
    
    def _switch_deployment_mode(self):
        """Switch between direct and nginx deployment modes."""
        current_mode = self.config_manager.config["mode"]
        
        console.print(f"[bold cyan]{self.translator.get('Current deployment mode')}: {current_mode}[/]")
        
        direct_choice = self.translator.get("Direct (For internal networks)")
        nginx_choice = self.translator.get("With Nginx (For internet-facing deployments)")
        
        deployment_mode = questionary.select(
            self.translator.get("Select new deployment mode:"),
            choices=[
                direct_choice,
                nginx_choice
            ],
            default=direct_choice if current_mode == "direct" else nginx_choice,
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
                    self.config_manager.config = configure_direct_mode(self.config_manager.config, self.translator)
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
                    self.config_manager.config = configure_nginx_mode(self.config_manager.config, self.translator, self.cert_manager)
                
                # Generate new configuration files
                generate_docker_compose(self.config_manager.config, self.translator, self.templates)
                
                # Generate nginx config files if switching to nginx mode
                if new_mode == "nginx":
                    generate_nginx_configs(self.config_manager.config, self.translator, self.templates)
            else:
                console.print(f"[yellow]{self.translator.get('Deployment mode switch cancelled')}[/]")
        else:
            console.print(f"[yellow]{self.translator.get('Deployment mode unchanged')}[/]")
    
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
            
            # Add project path selection after language and deployment mode
            self.select_project_path()
        
        # Configure based on mode
        if self.config_manager.config["mode"] == "direct":
            self.config_manager.config = configure_direct_mode(self.config_manager.config, self.translator)
        else:
            self.config_manager.config = configure_nginx_mode(self.config_manager.config, self.translator, self.cert_manager)
        
        # Save configuration
        self.config_manager.save()
        
        # Generate Docker Compose and other files
        if generate_docker_compose(self.config_manager.config, self.translator, self.templates):
            # Generate nginx config files if in nginx mode
            if self.config_manager.config["mode"] == "nginx":
                generate_nginx_configs(self.config_manager.config, self.translator, self.templates)
            
            console.print(f"[bold green]{self.translator.get('Setup complete')}![/]")
            
            # Ask to start services
            if questionary.confirm(
                self.translator.get("Would you like to start the Docker services now?"),
                default=True,
                style=custom_style
            ).ask():
                # Get the project path from config and pass it to the docker manager
                project_path = self.config_manager.config.get("environment", {}).get("path")
                self.docker_manager.restart_services(project_path=project_path)
        
        return True
    
    def select_project_path(self):
        """Let the user select a project path for data storage."""
        current_path = self.config_manager.config.get("environment", {}).get("path", "")
        
        console.print("[bold blue]Project Path Selection[/]")
        console.print("Please select a directory where TeddyCloud data will be stored.")
        console.print("This directory will contain the /data folder with all TeddyCloud files.")

        # Display current path if it exists
        if current_path:
            console.print(f"[bold cyan]Current project path: {current_path}[/]")
        
        # Ask if user wants to keep current path, browse for a new path, or enter manually
        if current_path:
            path_action = questionary.select(
                self.translator.get("What would you like to do?"),
                choices=[
                    self.translator.get("Keep current path"),
                    self.translator.get("Browse for a new path"),
                    self.translator.get("Enter path manually")
                ],
                style=custom_style
            ).ask()
            
            if path_action == self.translator.get("Keep current path"):
                return
        
        # Choose a path
        if not current_path or path_action == self.translator.get("Browse for a new path"):
            # Use the file_browser module to browse for a directory
            selected_path = browse_directory(
                start_path=current_path if current_path else None,
                translator=self.translator,
                title=self.translator.get("Select project directory")
            )
            
            if selected_path:
                # Update the path in the configuration
                if "environment" not in self.config_manager.config:
                    self.config_manager.config["environment"] = {}
                
                self.config_manager.config["environment"]["path"] = selected_path
                console.print(f"[bold green]{self.translator.get('Project path set to')}: {selected_path}[/]")
                
                # Create data directory if it doesn't exist
                data_dir = os.path.join(selected_path, "data")
                if not os.path.exists(data_dir):
                    os.makedirs(data_dir, exist_ok=True)
                    console.print(f"[green]{self.translator.get('Created data directory at')}: {data_dir}[/]")
                    
                # Save the configuration
                self.config_manager.save()
                return
                
        elif path_action == self.translator.get("Enter path manually"):
            # Allow manual path entry
            path = questionary.text(
                self.translator.get("Enter project path:"),
                default=current_path,
                style=custom_style
            ).ask()
            
            if path:
                # Normalize the path
                path = os.path.normpath(path)
                
                # Check if path exists
                if not os.path.exists(path):
                    # Ask to create it
                    create_it = questionary.confirm(
                        self.translator.get("Path doesn't exist. Create it?"),
                        default=True,
                        style=custom_style
                    ).ask()
                    
                    if create_it:
                        try:
                            os.makedirs(path, exist_ok=True)
                        except Exception as e:
                            console.print(f"[bold red]{self.translator.get('Error creating directory')}: {e}[/]")
                            return self.select_project_path()  # Try again
                    else:
                        return self.select_project_path()  # Try again
                
                # Check if path is accessible (write permissions)
                if not os.access(path, os.W_OK):
                    console.print(f"[bold red]{self.translator.get('Warning')}: {self.translator.get('The selected directory may not be writable.')}[/]")
                    proceed = questionary.confirm(
                        self.translator.get("Do you want to use this path anyway?"),
                        default=False,
                        style=custom_style
                    ).ask()
                    
                    if not proceed:
                        return self.select_project_path()  # Try again
                
                # Update the path in the configuration
                if "environment" not in self.config_manager.config:
                    self.config_manager.config["environment"] = {}
                
                self.config_manager.config["environment"]["path"] = path
                console.print(f"[bold green]{self.translator.get('Project path set to')}: {path}[/]")
                
                # Create data directory if it doesn't exist
                data_dir = os.path.join(path, "data")
                if not os.path.exists(data_dir):
                    os.makedirs(data_dir, exist_ok=True)
                    console.print(f"[green]{self.translator.get('Created data directory at')}: {data_dir}[/]")
                    
                # Save the configuration
                self.config_manager.save()
