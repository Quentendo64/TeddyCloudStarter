#!/usr/bin/env python3
"""
TeddyCloudStarter - The wizard for setting up TeddyCloud with Docker.
"""
import os
import sys
import subprocess
from pathlib import Path

# Ensure required packages are installed
try:
    from rich.console import Console
    from rich.panel import Panel
    import questionary
except ImportError:
    print("Required packages not found. Installing them...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich", "questionary", "jinja2"])
    from rich.console import Console
    from rich.panel import Panel
    import questionary

# Import our modules
from .wizard import TeddyCloudWizard
from .config_manager import ConfigManager
from .docker_manager import DockerManager
from .translator import Translator
from .certificates import CertificateManager
from .configurations import TEMPLATES
from .version_handler import check_for_updates

# Constants
DEFAULT_CONFIG_PATH = "config.json"

# Global console instance for rich output
console = Console()

# Determine if running as installed package or directly from source
try:
    # When running as an installed package
    package_path = os.path.dirname(__file__)
    is_installed_package = True
except NameError:
    # When running directly from source
    package_path = os.path.dirname(os.path.abspath(__file__))
    is_installed_package = False

# Set up paths for resources
if is_installed_package:
    # When installed as a package, locales are included as package data
    LOCALES_DIR = Path(package_path) / "locales"
else:
    # When running from source directory
    LOCALES_DIR = Path("locales")

# Ensure directories exist in working directory
Path("data").mkdir(exist_ok=True)
Path("data/configurations").mkdir(exist_ok=True)


def main():
    """Main entry point for the TeddyCloud Setup Wizard."""
    # Check for updates first
    check_for_updates()
    
    # Create the wizard instance with the correct locales directory
    wizard = TeddyCloudWizard(LOCALES_DIR)
    wizard.show_welcome()
    wizard.show_develmsg()
    
    # Check if config exists
    config_exists = os.path.exists(DEFAULT_CONFIG_PATH)
    
    if config_exists:
        # Check if language is set
        if "language" not in wizard.config_manager.config or not wizard.config_manager.config["language"]:
            wizard.select_language()
        else:
            # Set the language from config without showing selection
            wizard.translator.set_language(wizard.config_manager.config["language"])
    else:
        # If no config, select language
        wizard.select_language()
    
    if config_exists:
        # If config exists, show pre-wizard menu
        wizard.show_pre_wizard()
    else:
        # If no config, run the wizard
        wizard.run_wizard()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
