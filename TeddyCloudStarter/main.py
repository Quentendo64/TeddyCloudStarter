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
    import jinja2
    import dns.resolver
except ImportError:
    print("Required packages not found. Installing them...")
    try:
        # First check if pip is available
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError:
            print("\nError: pip is not installed for your Python installation.")
            print("Please install pip first using one of these methods:")
            print("- On Ubuntu/Debian: sudo apt update && sudo apt install python3-pip")
            print("- On Windows: python -m ensurepip")
            sys.exit(1)

        # If we got here, pip is available, so try to install the packages
        subprocess.check_call([sys.executable, "-m", "pip", "install", "rich", "questionary", "jinja2", "dnspython"])
    except Exception as e:
        print(f"\nFailed to install required packages: {e}")
        print("Please install them manually using:")
        print(f"{sys.executable} -m pip install rich questionary jinja2 dnspython\n")
        sys.exit(1)
        
    # Try importing again after installation
    from rich.console import Console
    from rich.panel import Panel
    import questionary
    import jinja2
    try:
        import dns.resolver
    except ImportError:
        print("\nFailed to import dnspython package after installation.")
        print("This package is required for domain validation.")
        sys.exit(1)

# Import our modules
from .main_wizard import TeddyCloudWizard
from .wizard.ui_helpers import console
from .config_manager import DEFAULT_CONFIG_PATH
from .utilities.version import check_for_updates
from .utilities.file_system import get_project_path, ensure_project_directories

# Determine if running as installed package or directly from source
package_path = os.path.dirname(__file__)

# Set up paths for resources
LOCALES_DIR = Path(package_path) / "locales"

def main():
    """Main entry point for the TeddyCloud Setup Wizard."""
    # Check for updates first
    check_for_updates()
    
    # Create the wizard instance with the correct locales directory
    wizard = TeddyCloudWizard(LOCALES_DIR)

    # Check if config exists
    config_exists = os.path.exists(DEFAULT_CONFIG_PATH)
    
    if config_exists:
        # Check if language is set and not empty
        if not wizard.config_manager.config.get("language"):
            wizard.select_language()
        else:
            # Set the language from config without showing selection
            wizard.translator.set_language(wizard.config_manager.config["language"])
    else:
        # If no config, select language
        wizard.select_language()
    
    wizard.display_welcome_message()
    wizard.display_development_message()
    # Project path selection - always show this page if path is not set
    if not wizard.config_manager.config.get("environment", {}).get("path"):
        wizard.select_project_path()
    
    # Get the project path from config and ensure directories exist
    project_path = get_project_path(wizard.config_manager)
    ensure_project_directories(project_path)
    
    if config_exists:
        # If config exists, show pre-wizard menu in a loop until user exits
        show_menu = True
        while show_menu:
            result = wizard.show_pre_wizard_menu()
            # If the result is False, it means the user chose to exit
            if result == False:
                show_menu = False
    else:
        # If no config, run the wizard
        wizard.execute_wizard()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
