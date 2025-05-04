#!/usr/bin/env python3
"""
Main menu module for TeddyCloudStarter.
"""
import os
import shutil
import time
from pathlib import Path

import questionary

from .configuration.generator import generate_docker_compose, generate_nginx_configs
from .security.certificate_authority import CertificateAuthority
from .security.client_certificates import ClientCertificateManager
from .security.lets_encrypt import LetsEncryptManager
from .setup_wizard import SetupWizard
from .ui.application_manager_ui import show_application_management_menu
from .ui.backup_manager_ui import show_backup_recovery_menu
from .ui.certificate_manager_ui import show_certificate_management_menu
from .ui.configuration_manager_ui import show_configuration_management_menu
from .ui.docker_manager_ui import show_docker_management_menu
from .ui.support_features_ui import show_support_features_menu

# Import our modules - use relative imports to avoid circular dependencies
from .wizard.base_wizard import BaseWizard
from .wizard.ui_helpers import (
    console,
    custom_style,
    display_configuration_table,
    show_development_message,
    show_welcome_message,
)


class MainMenu(BaseWizard):
    """Main menu class for TeddyCloud management."""

    def __init__(self, locales_dir: Path):
        """Initialize the main menu with locales directory."""
        super().__init__(locales_dir)
        self.locales_dir = locales_dir

    def display_welcome_message(self):
        """Show welcome message."""
        show_welcome_message(self.translator)

    def display_development_message(self):
        """Show developer message."""
        show_development_message(self.translator)

    def refresh_server_configuration(self):
        """Refresh server configuration by renewing docker-compose.yml and nginx*.conf."""
        console.print("[bold cyan]Refreshing server configuration...[/]")

        # Get the project path from config
        project_path = self.config_manager.config.get("environment", {}).get("path")
        if not project_path:
            console.print(
                f"[bold yellow]{self.translator.get('Warning')}: {self.translator.get('No project path set. Using current directory.')}[/]"
            )
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
            base_path / "data" / "configurations" / "nginx-edge.conf",
        ]

        for file_path in files_to_refresh:
            if file_path.exists():
                # Backup the file
                backup_path = backup_dir / file_path.name
                shutil.copy2(file_path, backup_path)
                console.print(f"[green]Backed up {file_path} to {backup_path}[/]")
            else:
                console.print(
                    f"[yellow]File {file_path} does not exist, skipping backup...[/]"
                )

        # Now regenerate the configuration files based on current config
        try:
            # Generate docker-compose.yml
            if generate_docker_compose(
                self.config_manager.config, self.translator, self.templates
            ):
                console.print("[green]Successfully refreshed docker-compose.yml[/]")
            else:
                console.print("[bold red]Failed to refresh docker-compose.yml[/]")

            # Generate nginx config files if in nginx mode
            if self.config_manager.config["mode"] == "nginx":
                if generate_nginx_configs(
                    self.config_manager.config, self.translator, self.templates
                ):
                    console.print(
                        "[green]Successfully refreshed nginx configuration files[/]"
                    )
                else:
                    console.print(
                        "[bold red]Failed to refresh nginx configuration files[/]"
                    )

            # Inform the user about next steps
            console.print("[bold green]Server configuration refreshed successfully![/]")
            console.print(
                "[cyan]You may need to restart Docker services for changes to take effect.[/]"
            )

            # Ask if user wants to restart services
            if questionary.confirm(
                self.translator.get("Would you like to restart Docker services now?"),
                default=True,
                style=custom_style,
            ).ask():
                # Get the project path from config and pass it to the docker manager
                self.docker_manager.restart_services(project_path=project_path)

        except Exception as e:
            console.print(f"[bold red]Error during configuration refresh: {e}[/]")
            console.print(
                "[yellow]Your configuration files may be incomplete. Restore from backup if needed.[/]"
            )
            console.print(f"[yellow]Backups can be found in: {backup_dir}[/]")

    def reload_configuration(self):
        """Reload the configuration after a reset operation."""
        # Re-initialize the configuration manager with the same translator
        self.config_manager.recreate_config(translator=self.translator)

        # Check if the language is set in the new config
        if not self.config_manager.config.get("language"):
            # Get the setup wizard for language selection
            setup_wizard = SetupWizard(self.locales_dir)
            setup_wizard.select_language()
            # Update our config from the wizard
            self.config_manager = setup_wizard.config_manager

        # Reset project path if it doesn't exist in config
        if not self.config_manager.config.get("environment", {}).get("path"):
            # Get the setup wizard for project path selection
            setup_wizard = SetupWizard(self.locales_dir)
            setup_wizard.select_project_path()
            # Update our config from the wizard
            self.config_manager = setup_wizard.config_manager
        else:
            # Update the project path for the wizard
            self.project_path = self.config_manager.config.get("environment", {}).get(
                "path"
            )

        # Re-initialize security managers with the new project path
        if self.project_path:
            self.set_project_path(self.project_path)

        # Display confirmation
        console.print(
            f"[green]{self.translator.get('Configuration reloaded successfully')}[/]"
        )

    def show_application_management_menu(self):
        """Show application management submenu."""
        # Pass config_manager to ensure project path is available
        exit_menu = show_application_management_menu(
            self.config_manager, self.docker_manager, self.translator
        )
        if not exit_menu:
            return self.show_main_menu()  # Show menu again after application management
        else:
            return True  # Return to main menu

    def show_support_features_menu(self):
        """Show support features submenu."""
        exit_menu = show_support_features_menu(
            self.config_manager, self.docker_manager, self.translator
        )
        if not exit_menu:
            return self.show_main_menu()  # Show menu again after support features
        else:
            return True  # Return to main menu

    def show_main_menu(self):
        """Show main menu when config exists."""
        current_config = self.config_manager.config

        # Display current configuration - check if config is valid
        config_valid = display_configuration_table(current_config, self.translator)

        # If configuration is corrupt, offer only limited options
        if not config_valid:
            choices = [
                {
                    "id": "reset",
                    "text": self.translator.get("Reset configuration and start over"),
                },
                {"id": "exit", "text": self.translator.get("Exit")},
            ]

            choice_texts = [choice["text"] for choice in choices]
            selected_text = questionary.select(
                self.translator.get(
                    "Configuration is corrupt. What would you like to do?"
                ),
                choices=choice_texts,
                style=custom_style,
            ).ask()

            # Find the selected ID
            selected_id = "exit"  # Default
            for choice in choices:
                if choice["text"] == selected_text:
                    selected_id = choice["id"]
                    break

            if selected_id == "reset":
                self.config_manager.delete()
                setup_wizard = SetupWizard(self.locales_dir)
                setup_wizard.run()
                return True

            return False  # Exit

        # Build menu choices with IDs
        choices = []

        # Define menu options with identifiers
        menu_options = [
            {
                "id": "app_management",
                "text": self.translator.get("Application management"),
            },
            {
                "id": "backup_recovery",
                "text": self.translator.get("Backup / Recovery management"),
            },
            {
                "id": "config_management",
                "text": self.translator.get("Configuration management"),
            },
            {
                "id": "docker_management",
                "text": self.translator.get("Docker management"),
            },
            {"id": "support_features", "text": self.translator.get("Support features")},
            {"id": "exit", "text": self.translator.get("Exit")},
        ]

        # Add Certificate management option conditionally
        if (
            current_config.get("mode") == "nginx"
            and "nginx" in current_config
            and (
                (current_config["nginx"].get("https_mode") == "letsencrypt")
                or (
                    "security" in current_config["nginx"]
                    and current_config["nginx"]["security"].get("type") == "client_cert"
                )
            )
        ):
            menu_options.insert(
                0,
                {
                    "id": "cert_management",
                    "text": self.translator.get("Certificate management"),
                },
            )

        # Sort menu options alphabetically by text (except "Exit" which should always be last)
        exit_option = next(opt for opt in menu_options if opt["id"] == "exit")
        menu_options.remove(exit_option)
        menu_options.sort(
            key=lambda x: x["text"]
        )  # Sort alphabetically by display text
        menu_options.append(exit_option)  # Add Exit as the last option

        choices.extend(menu_options)

        # Show main menu
        choice_texts = [choice["text"] for choice in choices]
        selected_text = questionary.select(
            self.translator.get("What would you like to do?"),
            choices=choice_texts,
            style=custom_style,
        ).ask()

        # Find the selected ID
        selected_id = "exit"  # Default to exit
        for choice in choices:
            if choice["text"] == selected_text:
                selected_id = choice["id"]
                break

        # Handle the selection based on the ID
        if selected_id == "cert_management":
            # Create a dictionary of security managers to pass to the certificate management menu
            security_managers = {
                "ca_manager": self.ca_manager,
                "client_cert_manager": self.client_cert_manager,
                "lets_encrypt_manager": self.lets_encrypt_manager,
            }

            exit_menu = show_certificate_management_menu(
                self.config_manager.config, self.translator, security_managers
            )
            if not exit_menu:
                return (
                    self.show_main_menu()
                )  # Show menu again after certificate management
            else:
                return (
                    self.show_main_menu()
                )  # Return to the main menu when "Back to main menu" was selected

        elif selected_id == "config_management":
            # Create a dictionary of security managers to pass to the configuration management menu
            security_managers = {
                "ca_manager": self.ca_manager,
                "client_cert_manager": self.client_cert_manager,
                "lets_encrypt_manager": self.lets_encrypt_manager,
                "ip_restrictions_manager": self.ip_restrictions_manager,
            }
            # Use SetupWizard for configuration management menu to ensure select_deployment_mode is available
            setup_wizard = SetupWizard(self.locales_dir)
            setup_wizard.config_manager = self.config_manager  # Share current config
            setup_wizard.translator = self.translator  # Share current translator
            result = show_configuration_management_menu(
                setup_wizard, self.config_manager, self.translator, security_managers
            )
            if result:  # If configuration was modified or wizard was run
                return True
            return self.show_main_menu()  # Show menu again

        elif selected_id == "docker_management":
            # Stay in Docker management menu until explicitly returning to main menu
            while True:
                # Pass config_manager to ensure project path is available for Docker operations
                exit_menu = show_docker_management_menu(
                    self.translator, self.docker_manager, self.config_manager
                )
                if exit_menu:
                    break  # Exit the Docker menu loop and return to main menu

            return self.show_main_menu()  # Return to the main menu

        elif selected_id == "app_management":
            return self.show_application_management_menu()

        elif selected_id == "backup_recovery":
            exit_menu = show_backup_recovery_menu(
                self.config_manager, self.docker_manager, self.translator
            )
            if not exit_menu:
                return self.show_main_menu()  # Show menu again
            else:
                return (
                    self.show_main_menu()
                )  # Return to the main menu when "Back to main menu" was selected

        elif selected_id == "support_features":
            return self.show_support_features_menu()

        return False  # Exit (default for 'exit' action)

    def set_project_path(self, project_path: str) -> None:
        """
        Set the project path for all certificate-related operations.

        Args:
            project_path: The path to the project directory
        """
        # Store the validated project path
        self.project_path = project_path

        # Create instances with the project path
        self.ca_manager = CertificateAuthority(
            base_dir=project_path, translator=self.translator
        )
        self.client_cert_manager = ClientCertificateManager(
            base_dir=project_path, translator=self.translator
        )
        self.lets_encrypt_manager = LetsEncryptManager(
            base_dir=project_path, translator=self.translator
        )

        # Update the project path in the config if needed
        if "environment" not in self.config_manager.config:
            self.config_manager.config["environment"] = {}
        self.config_manager.config["environment"]["path"] = project_path
        self.config_manager.save()
