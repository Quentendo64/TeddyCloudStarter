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
from .utilities.logger import logger

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
        logger.debug(f"Initializing MainMenu with locales_dir={locales_dir}")
        super().__init__(locales_dir)
        self.locales_dir = locales_dir
        logger.info("MainMenu initialized.")

    def display_welcome_message(self):
        logger.debug("Displaying welcome message.")
        show_welcome_message(self.translator)
        logger.info("Welcome message displayed.")

    def display_development_message(self):
        logger.debug("Displaying development message.")
        show_development_message(self.translator)
        logger.info("Development message displayed.")

    def refresh_server_configuration(self):
        logger.debug("Starting server configuration refresh.")
        console.print("[bold cyan]Refreshing server configuration...[/]")
        project_path = self.config_manager.config.get("environment", {}).get("path")
        logger.debug(f"Project path from config: {project_path}")
        if not project_path:
            logger.warning("No project path set. Using current directory.")
            console.print(
                f"[bold yellow]{self.translator.get('Warning')}: {self.translator.get('No project path set. Using current directory.')}[/]"
            )
            project_path = os.getcwd()
        base_path = Path(project_path)
        logger.debug(f"Base path for project: {base_path}")
        timestamp = time.strftime("%Y%m%d%H%M%S")
        backup_dir = Path("backup") / timestamp
        backup_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Backup directory created at {backup_dir}")
        files_to_refresh = [
            base_path / "data" / "docker-compose.yml",
            base_path / "data" / "configurations" / "nginx-auth.conf",
            base_path / "data" / "configurations" / "nginx-edge.conf",
        ]
        for file_path in files_to_refresh:
            logger.debug(f"Checking if file exists for backup: {file_path}")
            if file_path.exists():
                backup_path = backup_dir / file_path.name
                shutil.copy2(file_path, backup_path)
                logger.info(f"Backed up {file_path} to {backup_path}")
                console.print(f"[green]Backed up {file_path} to {backup_path}[/]")
            else:
                logger.warning(f"File {file_path} does not exist, skipping backup.")
                console.print(
                    f"[yellow]File {file_path} does not exist, skipping backup...[/]"
                )
        try:
            logger.debug("Generating docker-compose.yml...")
            if generate_docker_compose(
                self.config_manager.config, self.translator, self.templates
            ):
                logger.info("Successfully refreshed docker-compose.yml.")
                console.print("[green]Successfully refreshed docker-compose.yml[/]")
            else:
                logger.error("Failed to refresh docker-compose.yml.")
                console.print("[bold red]Failed to refresh docker-compose.yml[/]")
            logger.debug("Checking if nginx mode for nginx config generation.")
            if self.config_manager.config["mode"] == "nginx":
                logger.debug("Generating nginx configuration files...")
                if generate_nginx_configs(
                    self.config_manager.config, self.translator, self.templates
                ):
                    logger.info("Successfully refreshed nginx configuration files.")
                    console.print(
                        "[green]Successfully refreshed nginx configuration files[/]"
                    )
                else:
                    logger.error("Failed to refresh nginx configuration files.")
                    console.print(
                        "[bold red]Failed to refresh nginx configuration files[/]"
                    )
            logger.info("Server configuration refreshed successfully.")
            console.print("[bold green]Server configuration refreshed successfully![/]")
            console.print(
                "[cyan]You may need to restart Docker services for changes to take effect.[/]"
            )
            logger.debug("Prompting user to restart Docker services.")
            if questionary.confirm(
                self.translator.get("Would you like to restart Docker services now?"),
                default=True,
                style=custom_style,
            ).ask():
                logger.info("User chose to restart Docker services.")
                self.docker_manager.restart_services(project_path=project_path)
            else:
                logger.info("User chose not to restart Docker services.")
        except Exception as e:
            logger.error(f"Error during configuration refresh: {e}")
            console.print(f"[bold red]Error during configuration refresh: {e}[/]")
            console.print(
                "[yellow]Your configuration files may be incomplete. Restore from backup if needed.[/]"
            )
            console.print(f"[yellow]Backups can be found in: {backup_dir}[/]")

    def reload_configuration(self):
        logger.debug("Reloading configuration after reset operation.")
        self.config_manager.recreate_config(translator=self.translator)
        logger.info("Configuration manager re-initialized.")
        if not self.config_manager.config.get("language"):
            logger.debug("No language set in config. Running language selection wizard.")
            setup_wizard = SetupWizard(self.locales_dir)
            setup_wizard.select_language()
            self.config_manager = setup_wizard.config_manager
            logger.info("Language selected and config updated.")
        if not self.config_manager.config.get("environment", {}).get("path"):
            logger.debug("No project path set in config. Running project path selection wizard.")
            setup_wizard = SetupWizard(self.locales_dir)
            setup_wizard.select_project_path()
            self.config_manager = setup_wizard.config_manager
            logger.info("Project path selected and config updated.")
        else:
            self.project_path = self.config_manager.config.get("environment", {}).get(
                "path"
            )
            logger.debug(f"Project path set to {self.project_path}")
        if self.project_path:
            logger.debug("Setting project path for security managers.")
            self.set_project_path(self.project_path)
        console.print(
            f"[green]{self.translator.get('Configuration reloaded successfully')}[/]"
        )
        logger.info("Configuration reloaded successfully.")

    def show_application_management_menu(self):
        logger.debug("Showing application management submenu.")
        exit_menu = show_application_management_menu(
            self.config_manager, self.docker_manager, self.translator
        )
        logger.info(f"Application management menu exited: {exit_menu}")
        if not exit_menu:
            return self.show_main_menu()
        else:
            return True

    def show_support_features_menu(self):
        logger.debug("Showing support features submenu.")
        exit_menu = show_support_features_menu(
            self.config_manager, self.docker_manager, self.translator
        )
        logger.info(f"Support features menu exited: {exit_menu}")
        if not exit_menu:
            return self.show_main_menu()
        else:
            return True

    def show_main_menu(self):
        logger.debug("Showing main menu.")
        current_config = self.config_manager.config
        config_valid = display_configuration_table(current_config, self.translator)
        logger.debug(f"Configuration valid: {config_valid}")
        if not config_valid:
            logger.warning("Configuration is corrupt. Offering limited options.")
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
            selected_id = "exit"
            for choice in choices:
                if choice["text"] == selected_text:
                    selected_id = choice["id"]
                    break
            logger.info(f"User selected: {selected_id}")
            if selected_id == "reset":
                logger.debug("Deleting config and running setup wizard.")
                self.config_manager.delete()
                setup_wizard = SetupWizard(self.locales_dir)
                setup_wizard.run()
                return True
            return False
        choices = []
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
        exit_option = next(opt for opt in menu_options if opt["id"] == "exit")
        menu_options.remove(exit_option)
        menu_options.sort(
            key=lambda x: x["text"]
        )
        menu_options.append(exit_option)
        choices.extend(menu_options)
        choice_texts = [choice["text"] for choice in choices]
        selected_text = questionary.select(
            self.translator.get("What would you like to do?"),
            choices=choice_texts,
            style=custom_style,
        ).ask()
        selected_id = "exit"
        for choice in choices:
            if choice["text"] == selected_text:
                selected_id = choice["id"]
                break
        logger.info(f"User selected main menu option: {selected_id}")
        if selected_id == "cert_management":
            logger.debug("Showing certificate management menu.")
            security_managers = {
                "ca_manager": self.ca_manager,
                "client_cert_manager": self.client_cert_manager,
                "lets_encrypt_manager": self.lets_encrypt_manager,
            }
            exit_menu = show_certificate_management_menu(
                self.config_manager.config, self.translator, security_managers
            )
            logger.info(f"Certificate management menu exited: {exit_menu}")
            if not exit_menu:
                return self.show_main_menu()
            else:
                return self.show_main_menu()
        elif selected_id == "config_management":
            logger.debug("Showing configuration management menu.")
            security_managers = {
                "ca_manager": self.ca_manager,
                "client_cert_manager": self.client_cert_manager,
                "lets_encrypt_manager": self.lets_encrypt_manager,
                "ip_restrictions_manager": self.ip_restrictions_manager,
                "basic_auth_manager": self.basic_auth_manager,
                "auth_bypass_manager": self.auth_bypass_manager
            }
            setup_wizard = SetupWizard(self.locales_dir)
            setup_wizard.config_manager = self.config_manager
            setup_wizard.translator = self.translator
            result = show_configuration_management_menu(
                setup_wizard, self.config_manager, self.translator, security_managers
            )
            logger.info(f"Configuration management menu result: {result}")
            if result:
                return True
            return self.show_main_menu()
        elif selected_id == "docker_management":
            logger.debug("Showing docker management menu loop.")
            while True:
                exit_menu = show_docker_management_menu(
                    self.translator, self.docker_manager, self.config_manager
                )
                logger.info(f"Docker management menu exited: {exit_menu}")
                if exit_menu:
                    break
            return self.show_main_menu()
        elif selected_id == "app_management":
            logger.debug("Showing application management menu.")
            return self.show_application_management_menu()
        elif selected_id == "backup_recovery":
            logger.debug("Showing backup/recovery menu.")
            exit_menu = show_backup_recovery_menu(
                self.config_manager, self.docker_manager, self.translator
            )
            logger.info(f"Backup/recovery menu exited: {exit_menu}")
            if not exit_menu:
                return self.show_main_menu()
            else:
                return self.show_main_menu()
        elif selected_id == "support_features":
            logger.debug("Showing support features menu.")
            return self.show_support_features_menu()
        logger.info("Exiting main menu.")
        return False

    def set_project_path(self, project_path: str) -> None:
        logger.debug(f"Setting project path for certificate-related operations: {project_path}")
        self.project_path = project_path
        self.ca_manager = CertificateAuthority(
            base_dir=project_path, translator=self.translator
        )
        self.client_cert_manager = ClientCertificateManager(
            base_dir=project_path, translator=self.translator
        )
        self.lets_encrypt_manager = LetsEncryptManager(
            base_dir=project_path, translator=self.translator
        )
        # Initialize the basic auth manager and IP restrictions managers
        from .security.basic_auth import BasicAuthManager
        from .security.ip_restrictions import IPRestrictionsManager, AuthBypassIPManager
        
        self.basic_auth_manager = BasicAuthManager(
            base_dir=project_path, translator=self.translator
        )
        self.ip_restrictions_manager = IPRestrictionsManager(
            translator=self.translator
        )
        self.auth_bypass_manager = AuthBypassIPManager(
            translator=self.translator
        )
        
        if "environment" not in self.config_manager.config:
            logger.debug("Adding 'environment' section to config.")
            self.config_manager.config["environment"] = {}
        self.config_manager.config["environment"]["path"] = project_path
        self.config_manager.save()
        logger.info(f"Project path set and config saved: {project_path}")
