#!/usr/bin/env python3
"""
TeddyCloudStarter - The wizard for setting up TeddyCloud with Docker.
"""
import os
import subprocess
import sys
from pathlib import Path

# Ensure required packages are installed
try:
    import dns.resolver
    import jinja2
    import questionary
    from rich.console import Console
    from rich.panel import Panel
except ImportError:
    print("Required packages not found. Installing them...")
    try:
        # First check if pip is available
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError:
            print("\nError: pip is not installed for your Python installation.")
            print("Please install pip first using one of these methods:")
            print("- On Ubuntu/Debian: sudo apt update && sudo apt install python3-pip")
            print("- On Windows: python -m ensurepip")
            sys.exit(1)

        # If we got here, pip is available, so try to install the packages
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "rich",
                "questionary",
                "jinja2",
                "dnspython",
            ]
        )
    except Exception as e:
        print(f"\nFailed to install required packages: {e}")
        print("Please install them manually using:")
        print(f"{sys.executable} -m pip install rich questionary jinja2 dnspython\n")
        sys.exit(1)

    # Try importing again after installation

    try:
        import dns.resolver
    except ImportError:
        print("\nFailed to import dnspython package after installation.")
        print("This package is required for domain validation.")
        sys.exit(1)

from .config_manager import DEFAULT_CONFIG_PATH
from .docker.manager import DockerManager
from .main_menu import MainMenu

# Import our modules
from .setup_wizard import SetupWizard
from .utilities.file_system import ensure_project_directories, get_project_path
from .utilities.version import check_for_updates
from .wizard.ui_helpers import console

# Determine if running as installed package or directly from source
package_path = os.path.dirname(__file__)

# Set up paths for resources
LOCALES_DIR = Path(package_path) / "locales"


def check_docker_prerequisites():
    """
    Check if Docker and Docker Compose are installed and available.
    Display an error message and exit if they are not.
    """
    all_met, prerequisites, error_message = DockerManager.check_docker_prerequisites()

    if not all_met:
        console.print("[bold red]ERROR: Docker prerequisites not met![/]")
        console.print(f"[bold yellow]{error_message}[/]")
        console.print(
            "[bold red]TeddyCloudStarter requires Docker and Docker Compose to function.[/]"
        )
        console.print(
            "[bold red]Please install the missing components and try again.[/]"
        )
        sys.exit(1)

    return True


def main():
    """Main entry point for the TeddyCloud Setup Wizard."""
    # Check for updates
    check_for_updates()
    # Check for Docker prerequisites first
    check_docker_prerequisites()

    # Import logger setup here to avoid circular import issues
    from .utilities.logger import get_logger

    # Check if config exists
    config_exists = os.path.exists(DEFAULT_CONFIG_PATH)

    if config_exists:
        # If config exists, initialize the MainMenu and show it
        menu = MainMenu(LOCALES_DIR)

        # Initialize logger with config_manager from menu
        logger = get_logger(name=__name__,config_manager=menu.config_manager)

        # Set the language from config without showing selection
        if menu.config_manager.config.get("language"):
            menu.translator.set_language(menu.config_manager.config["language"])
        else:
            # If no language setting, select language
            menu.select_language()

        # Display welcome messages
        menu.display_welcome_message()
        menu.display_development_message()

        # Get the project path from config and ensure directories exist
        project_path = get_project_path(menu.config_manager)
        ensure_project_directories(project_path)

        # Properly set the project path and reinitialize security managers
        menu.set_project_path(project_path)

        # Show the main menu in a loop until user exits
        show_menu = True
        while show_menu:
            result = menu.show_main_menu()
            # If the result is False, it means the user chose to exit
            if result == False:
                show_menu = False
    else:
        # If no config, run the setup wizard
        wizard = SetupWizard(LOCALES_DIR)

        # Initialize logger with config_manager from wizard
        logger = get_logger(name=__name__,config_manager=wizard.config_manager)

        # Select language first
        wizard.select_language()

        # Display welcome messages
        wizard.display_welcome_message()
        wizard.display_development_message()

        # Run the wizard
        wizard.run()

        # After wizard completes, show the main menu
        menu = MainMenu(LOCALES_DIR)
        # Set the project path from the wizard's config
        if (
            "environment" in wizard.config_manager.config
            and "path" in wizard.config_manager.config["environment"]
        ):
            project_path = wizard.config_manager.config["environment"]["path"]
            menu.set_project_path(project_path)

        # Show the main menu in a loop until user exits
        show_menu = True
        while show_menu:
            result = menu.show_main_menu()
            # If the result is False, it means the user chose to exit
            if result == False:
                show_menu = False

    return 0


if __name__ == "__main__":
    sys.exit(main())
