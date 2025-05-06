#!/usr/bin/env python3
"""
Setup wizard module for TeddyCloudStarter.
"""
import os
from pathlib import Path

import questionary

from .configuration.direct_mode import configure_direct_mode
from .configuration.generator import generate_docker_compose, generate_nginx_configs
from .configuration.nginx_mode import configure_nginx_mode
from .utilities.file_system import browse_directory
from .utilities.logger import logger

# Import our modules - use relative imports to avoid circular dependencies
from .wizard.base_wizard import BaseWizard
from .wizard.ui_helpers import (
    console,
    custom_style,
    show_development_message,
    show_welcome_message,
)


class SetupWizard(BaseWizard):
    """Setup wizard class for TeddyCloud configuration."""

    def __init__(self, locales_dir: Path):
        """Initialize the setup wizard with locales directory."""
        logger.debug(f"Initializing SetupWizard with locales_dir={locales_dir}")
        super().__init__(locales_dir)
        self.locales_dir = locales_dir
        logger.info("SetupWizard initialized.")

    def select_language(self):
        """Let the user select a language."""
        logger.debug("Entering select_language()")
        languages = {"en": "English", "de": "Deutsch"}
        available_langs = {
            k: v
            for k, v in languages.items()
            if k in self.translator.available_languages
        }
        logger.debug(f"Available languages: {available_langs}")
        if not available_langs:
            logger.warning("No available languages found, defaulting to English.")
            available_langs = {"en": "English"}
        choices = [f"{code}: {name}" for code, name in available_langs.items()]
        logger.debug(f"Language choices presented: {choices}")
        language_choice = questionary.select(
            self.translator.get("Select language / Sprache wählen:"),
            choices=choices,
            style=custom_style,
        ).ask()
        logger.debug(f"User selected language: {language_choice}")
        if language_choice:
            lang_code = language_choice.split(":")[0].strip()
            logger.info(f"Setting language to {lang_code}")
            self.translator.set_language(lang_code)
            self.config_manager.config["language"] = lang_code
            self.config_manager.save()
            logger.success(f"Language set to {lang_code} and saved to config.")
        else:
            logger.warning("No language selected by user.")

    def display_welcome_message(self):
        """Show welcome message."""
        logger.debug("Displaying welcome message.")
        show_welcome_message(self.translator)
        logger.info("Welcome message displayed.")

    def display_development_message(self):
        """Show developer message."""
        logger.debug("Displaying development message.")
        show_development_message(self.translator)
        logger.info("Development message displayed.")

    def run(self):
        """Run the main configuration wizard to set up TeddyCloud."""
        logger.info("Starting TeddyCloud setup wizard.")
        logger.debug(f"Current config: {self.config_manager.config}")
        console.print(
            f"[bold cyan]{self.translator.get('Starting TeddyCloud setup wizard')}...[/]"
        )
        # Step 1: Select project path if not already set
        if not self.config_manager.config.get("environment", {}).get("path"):
            logger.debug("Project path not set, invoking select_project_path().")
            self.select_project_path()
        else:
            logger.debug("Project path already set.")
        # Step 2: Select deployment mode (and configure it)
        logger.debug("Selecting deployment mode.")
        self.select_deployment_mode()
        # Save the configuration
        logger.debug("Saving configuration after deployment mode selection.")
        self.config_manager.save()
        logger.success("Configuration saved after deployment mode selection.")
        console.print(
            f"[bold green]{self.translator.get('Configuration completed successfully!')}[/]"
        )
        # Generate configuration files automatically
        logger.info("Generating configuration files.")
        console.print(
            f"[bold cyan]{self.translator.get('Generating configuration files')}...[/]"
        )
        # Generate docker-compose.yml file
        logger.debug("Generating docker-compose.yml file.")
        if generate_docker_compose(
            self.config_manager.config, self.translator, self.templates
        ):
            logger.success("Successfully generated docker-compose.yml.")
            console.print(
                f"[green]{self.translator.get('Successfully generated docker-compose.yml')}[/]"
            )
        else:
            logger.error("Failed to generate docker-compose.yml.")
            console.print(
                f"[bold red]{self.translator.get('Failed to generate docker-compose.yml')}[/]"
            )
        # Generate nginx configuration files if in nginx mode
        if self.config_manager.config["mode"] == "nginx":
            logger.debug("Mode is nginx, generating nginx configuration files.")
            if generate_nginx_configs(
                self.config_manager.config, self.translator, self.templates
            ):
                logger.success("Successfully generated nginx configuration files.")
                console.print(
                    f"[green]{self.translator.get('Successfully generated nginx configuration files')}[/]"
                )
            else:
                logger.error("Failed to generate nginx configuration files.")
                console.print(
                    f"[bold red]{self.translator.get('Failed to generate nginx configuration files')}[/]"
                )
        else:
            logger.debug("Mode is not nginx, skipping nginx config generation.")
        console.print(
            f"[bold green]{self.translator.get('Configuration files generated successfully!')}[/]"
        )
        # Ask if user wants to start services with the new configuration
        logger.info("Prompting user to start/restart services with new configuration.")
        if questionary.confirm(
            self.translator.get(
                "Want to start/restart services with the new configuration?"
            ),
            default=True,
            style=custom_style,
        ).ask():
            project_path = self.config_manager.config.get("environment", {}).get("path")
            logger.info(f"User chose to start/restart services. Project path: {project_path}")
            self.docker_manager.start_services(project_path=project_path)
            logger.success("Services started/restarted successfully.")
        else:
            logger.info("User declined to start/restart services.")
        logger.debug("Exiting run() method.")
        return True

    def select_project_path(self):
        """Let the user select a project path."""
        logger.debug("Entering select_project_path().")
        console.print(
            f"[bold cyan]{self.translator.get('Please select a directory for your TeddyCloud project')}[/]"
        )
        console.print(
            f"[cyan]{self.translator.get('This directory will be used to store all TeddyCloudStarter related data like certificates, and configuration files.')}[/]"
        )
        current_dir = Path(self.config_manager.config_path).parent
        old_project_path = self.config_manager.config.get("environment", {}).get("path")
        logger.debug(f"Current dir: {current_dir}, Old project path: {old_project_path}")
        selected_path = browse_directory(
            start_path=current_dir,
            title=self.translator.get("Select TeddyCloud Project Directory"),
            translator=self.translator,
        )
        logger.debug(f"User selected path: {selected_path}")
        if selected_path:
            if old_project_path and os.path.abspath(selected_path) != os.path.abspath(
                old_project_path
            ):
                logger.info(f"Project path changed from {old_project_path} to {selected_path}")
                old_data = os.path.join(old_project_path, "data")
                new_data = os.path.join(selected_path, "data")
                if os.path.exists(old_data):
                    logger.debug(f"Old data directory exists: {old_data}")
                    move_data = questionary.confirm(
                        self.translator.get(
                            "Move existing /data folder to the new project path?"
                        ),
                        default=True,
                        style=custom_style,
                    ).ask()
                    logger.debug(f"User chose to move data: {move_data}")
                    if move_data:
                        self.docker_manager.stop_services(project_path=old_project_path)
                        import shutil
                        try:
                            shutil.move(old_data, new_data)
                            logger.success(f"Moved /data folder from {old_data} to {new_data}.")
                            console.print(
                                f"[green]{self.translator.get('Moved /data folder to new project path.')}[/]"
                            )
                        except Exception as e:
                            logger.error(f"Failed to move /data folder: {e}")
                            console.print(
                                f"[bold red]{self.translator.get('Failed to move /data folder')}: {e}[/]"
                            )
                        if "environment" not in self.config_manager.config:
                            self.config_manager.config["environment"] = {}
                        self.config_manager.config["environment"]["path"] = selected_path
                        self.config_manager.save()
                        logger.info(f"Config updated with new project path: {selected_path}")
                        self.docker_manager.start_services(project_path=selected_path)
                        logger.success("Services started after moving data.")
                        return
                    else:
                        logger.info("User chose not to move data, asking about deleting old project path.")
                        delete_old = questionary.confirm(
                            self.translator.get(
                                "Delete old project path after switching?"
                            ),
                            default=False,
                            style=custom_style,
                        ).ask()
                        logger.debug(f"User chose to delete old project path: {delete_old}")
                        if delete_old:
                            self.docker_manager.stop_services(
                                project_path=old_project_path
                            )
                            import shutil
                            try:
                                shutil.rmtree(old_project_path)
                                logger.success(f"Old project path {old_project_path} deleted.")
                                console.print(
                                    f"[green]{self.translator.get('Old project path deleted.')}[/]"
                                )
                                console.print(
                                    f"[bold yellow]{self.translator.get('No project files found. Restarting setup wizard...')}[/]"
                                )
                                logger.info("Restarting setup wizard after deleting old project path.")
                                self.run()
                                return
                            except Exception as e:
                                logger.error(f"Failed to delete old project path: {e}")
                                console.print(
                                    f"[bold red]{self.translator.get('Failed to delete old project path')}: {e}[/]"
                                )
            if "environment" not in self.config_manager.config:
                self.config_manager.config["environment"] = {}
            self.config_manager.config["environment"]["path"] = selected_path
            logger.info(f"Project path set to {selected_path}")
            console.print(
                f"[green]{self.translator.get('Project path set to')}: {selected_path}[/]"
            )
            self.config_manager.save()
            logger.success("Configuration saved after setting project path.")
        else:
            logger.warning("No path selected by user, using current directory as fallback.")
            if "environment" not in self.config_manager.config:
                self.config_manager.config["environment"] = {}
            self.config_manager.config["environment"]["path"] = current_dir
            console.print(
                f"[yellow]{self.translator.get('No path selected. Using current directory')}: {current_dir}[/]"
            )
            self.config_manager.save()
            logger.success("Configuration saved with current directory as project path.")
        logger.debug("Exiting select_project_path().")

    def select_deployment_mode(self):
        """Let the user select a deployment mode."""
        logger.debug("Entering select_deployment_mode().")
        choices = [
            {
                "id": "direct",
                "text": self.translator.get(
                    "Direct mode (Simplest, all services on one container)"
                ),
            },
            {
                "id": "nginx",
                "text": self.translator.get(
                    "Nginx mode (Advanced, uses nginx for routing and security)"
                ),
            },
        ]
        choice_texts = [choice["text"] for choice in choices]
        logger.debug(f"Deployment mode choices: {choice_texts}")
        selected_text = questionary.select(
            self.translator.get("Select a deployment mode:"),
            choices=choice_texts,
            style=custom_style,
        ).ask()
        logger.debug(f"User selected deployment mode text: {selected_text}")
        selected_id = None
        for choice in choices:
            if choice["text"] == selected_text:
                selected_id = choice["id"]
                break
        logger.info(f"Deployment mode selected: {selected_id}")
        self.config_manager.config["mode"] = selected_id
        security_managers = {
            "ca_manager": self.ca_manager,
            "client_cert_manager": self.client_cert_manager,
            "lets_encrypt_manager": self.lets_encrypt_manager,
            "basic_auth_manager": self.basic_auth_manager,
            "ip_restrictions_manager": self.ip_restrictions_manager,
            "auth_bypass_manager": self.auth_bypass_manager,
        }
        if selected_id == "direct":
            logger.debug("Configuring direct mode.")
            self.config_manager.config = configure_direct_mode(
                self.config_manager.config, self.translator
            )
            logger.success("Direct mode configured.")
        else:
            logger.debug("Configuring nginx mode.")
            self.config_manager.config = configure_nginx_mode(
                self.config_manager.config, self.translator, security_managers
            )
            logger.success("Nginx mode configured.")
        console.print(
            f"[green]{self.translator.get('Deployment mode set to')}: {self.config_manager.config['mode']}[/]"
        )
        self.config_manager.save()
        logger.success("Configuration saved after deployment mode selection.")
        logger.debug("Exiting select_deployment_mode().")

    def configure_direct_mode(self):
        """Configure direct deployment mode settings."""
        logger.debug("Configuring direct deployment mode settings.")
        security_managers = {
            "ca_manager": self.ca_manager,
            "client_cert_manager": self.client_cert_manager,
            "lets_encrypt_manager": self.lets_encrypt_manager,
        }
        configure_direct_mode(self.config_manager.config, self.translator)
        self.config_manager.save()
        logger.success("Direct deployment mode configured and saved.")

    def configure_nginx_mode(self):
        """Configure Nginx deployment mode settings."""
        logger.debug("Configuring Nginx deployment mode settings.")
        security_managers = {
            "ca_manager": self.ca_manager,
            "client_cert_manager": self.client_cert_manager,
            "lets_encrypt_manager": self.lets_encrypt_manager,
            "basic_auth_manager": self.basic_auth_manager,
            "ip_restrictions_manager": self.ip_restrictions_manager,
            "auth_bypass_manager": self.auth_bypass_manager,
        }
        configure_nginx_mode(
            self.config_manager.config, self.translator, security_managers
        )
        self.config_manager.save()
        logger.success("Nginx deployment mode configured and saved.")
