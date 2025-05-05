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
        super().__init__(locales_dir)
        self.locales_dir = locales_dir

    def select_language(self):
        """Let the user select a language."""
        languages = {"en": "English", "de": "Deutsch"}

        available_langs = {
            k: v
            for k, v in languages.items()
            if k in self.translator.available_languages
        }

        if not available_langs:
            available_langs = {"en": "English"}

        choices = [f"{code}: {name}" for code, name in available_langs.items()]

        language_choice = questionary.select(
            self.translator.get("Select language / Sprache wählen:"),
            choices=choices,
            style=custom_style,
        ).ask()

        if language_choice:
            lang_code = language_choice.split(":")[0].strip()
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

    def run(self):
        """Run the main configuration wizard to set up TeddyCloud."""
        console.print(
            f"[bold cyan]{self.translator.get('Starting TeddyCloud setup wizard')}...[/]"
        )

        # Step 1: Select project path if not already set
        if not self.config_manager.config.get("environment", {}).get("path"):
            self.select_project_path()

        # Step 2: Select deployment mode (and configure it)
        self.select_deployment_mode()
        # Removed redundant calls to configure_direct_mode/configure_nginx_mode
        # as select_deployment_mode already performs configuration

        # Save the configuration
        self.config_manager.save()

        console.print(
            f"[bold green]{self.translator.get('Configuration completed successfully!')}[/]"
        )

        # Generate configuration files automatically
        console.print(
            f"[bold cyan]{self.translator.get('Generating configuration files')}...[/]"
        )

        # Generate docker-compose.yml file
        if generate_docker_compose(
            self.config_manager.config, self.translator, self.templates
        ):
            console.print(
                f"[green]{self.translator.get('Successfully generated docker-compose.yml')}[/]"
            )
        else:
            console.print(
                f"[bold red]{self.translator.get('Failed to generate docker-compose.yml')}[/]"
            )

        # Generate nginx configuration files if in nginx mode
        if self.config_manager.config["mode"] == "nginx":
            if generate_nginx_configs(
                self.config_manager.config, self.translator, self.templates
            ):
                console.print(
                    f"[green]{self.translator.get('Successfully generated nginx configuration files')}[/]"
                )
            else:
                console.print(
                    f"[bold red]{self.translator.get('Failed to generate nginx configuration files')}[/]"
                )

        console.print(
            f"[bold green]{self.translator.get('Configuration files generated successfully!')}[/]"
        )

        # Ask if user wants to start services with the new configuration
        if questionary.confirm(
            self.translator.get(
                "Want to start/restart services with the new configuration?"
            ),
            default=True,
            style=custom_style,
        ).ask():
            # Get the project path from config and pass it to the docker manager
            project_path = self.config_manager.config.get("environment", {}).get("path")
            self.docker_manager.start_services(project_path=project_path)

        return True

    def select_project_path(self):
        """Let the user select a project path."""
        console.print(
            f"[bold cyan]{self.translator.get('Please select a directory for your TeddyCloud project')}[/]"
        )
        console.print(
            f"[cyan]{self.translator.get('This directory will be used to store all TeddyCloudStarter related data like certificates, and configuration files.')}[/]"
        )
        current_dir = Path(self.config_manager.config_path).parent
        old_project_path = self.config_manager.config.get("environment", {}).get("path")
        selected_path = browse_directory(
            start_path=current_dir,
            title=self.translator.get("Select TeddyCloud Project Directory"),
            translator=self.translator,
        )

        if selected_path:
            # If changing project path, handle data migration
            if old_project_path and os.path.abspath(selected_path) != os.path.abspath(
                old_project_path
            ):
                old_data = os.path.join(old_project_path, "data")
                new_data = os.path.join(selected_path, "data")
                if os.path.exists(old_data):
                    move_data = questionary.confirm(
                        self.translator.get(
                            "Move existing /data folder to the new project path?"
                        ),
                        default=True,
                        style=custom_style,
                    ).ask()
                    if move_data:
                        # Stop Docker services before moving
                        self.docker_manager.stop_services(project_path=old_project_path)
                        import shutil

                        try:
                            shutil.move(old_data, new_data)
                            console.print(
                                f"[green]{self.translator.get('Moved /data folder to new project path.')}[/]"
                            )
                        except Exception as e:
                            console.print(
                                f"[bold red]{self.translator.get('Failed to move /data folder')}: {e}[/]"
                            )
                        # Update config and restart services in new location
                        if "environment" not in self.config_manager.config:
                            self.config_manager.config["environment"] = {}
                        self.config_manager.config["environment"][
                            "path"
                        ] = selected_path
                        self.config_manager.save()
                        self.docker_manager.start_services(project_path=selected_path)
                        return
                    else:
                        delete_old = questionary.confirm(
                            self.translator.get(
                                "Delete old project path after switching?"
                            ),
                            default=False,
                            style=custom_style,
                        ).ask()
                        if delete_old:
                            self.docker_manager.stop_services(
                                project_path=old_project_path
                            )
                            import shutil

                            try:
                                shutil.rmtree(old_project_path)
                                console.print(
                                    f"[green]{self.translator.get('Old project path deleted.')}[/]"
                                )
                                # Restart the setup wizard since there are no project files anymore
                                console.print(
                                    f"[bold yellow]{self.translator.get('No project files found. Restarting setup wizard...')}[/]"
                                )
                                self.run()
                                return
                            except Exception as e:
                                console.print(
                                    f"[bold red]{self.translator.get('Failed to delete old project path')}: {e}[/]"
                                )
            # Update config with selected path
            if "environment" not in self.config_manager.config:
                self.config_manager.config["environment"] = {}
            self.config_manager.config["environment"]["path"] = selected_path
            console.print(
                f"[green]{self.translator.get('Project path set to')}: {selected_path}[/]"
            )
            # Save configuration
            self.config_manager.save()
        else:
            # Use current directory as fallback
            if "environment" not in self.config_manager.config:
                self.config_manager.config["environment"] = {}
            self.config_manager.config["environment"]["path"] = current_dir
            console.print(
                f"[yellow]{self.translator.get('No path selected. Using current directory')}: {current_dir}[/]"
            )
            # Save configuration
            self.config_manager.save()

    def select_deployment_mode(self):
        """Let the user select a deployment mode."""
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
        selected_text = questionary.select(
            self.translator.get("Select a deployment mode:"),
            choices=choice_texts,
            style=custom_style,
        ).ask()
        selected_id = None
        for choice in choices:
            if choice["text"] == selected_text:
                selected_id = choice["id"]
                break
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
            self.config_manager.config = configure_direct_mode(
                self.config_manager.config, self.translator
            )
        else:
            self.config_manager.config = configure_nginx_mode(
                self.config_manager.config, self.translator, security_managers
            )

        console.print(
            f"[green]{self.translator.get('Deployment mode set to')}: {self.config_manager.config['mode']}[/]"
        )
        self.config_manager.save()

    def configure_direct_mode(self):
        """Configure direct deployment mode settings."""
        security_managers = {
            "ca_manager": self.ca_manager,
            "client_cert_manager": self.client_cert_manager,
            "lets_encrypt_manager": self.lets_encrypt_manager,
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
            "auth_bypass_manager": self.auth_bypass_manager,
        }
        configure_nginx_mode(
            self.config_manager.config, self.translator, security_managers
        )
        self.config_manager.save()
