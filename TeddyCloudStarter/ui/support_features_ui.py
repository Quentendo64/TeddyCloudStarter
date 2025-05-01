#!/usr/bin/env python3
"""
Support features UI for TeddyCloudStarter.
"""
import os
import sys
import subprocess
import questionary
from pathlib import Path
from rich.panel import Panel
from rich import box

from ..wizard.ui_helpers import console, custom_style
from ..utilities.file_system import browse_directory

def show_support_features_menu(config_manager, docker_manager, translator):
    """
    Display the support features menu.
    
    Args:
        config_manager: The configuration manager instance
        docker_manager: The docker manager instance
        translator: The translator instance for localization
        
    Returns:
        bool: True if user wants to return to main menu, False otherwise
    """
    choices = [
        translator.get("Create support package"),
        translator.get("Back to main menu")
    ]
    
    action = questionary.select(
        translator.get("Support Features"),
        choices=choices,
        style=custom_style
    ).ask()
    
    if action == translator.get("Create support package"):
        project_path = config_manager.config.get("environment", {}).get("path") if config_manager else None
        create_support_package(docker_manager, config_manager, translator, project_path)
        return False  # Stay in support menu
    
    elif action == translator.get("Back to main menu"):
        return True  # Return to main menu
    
    return False  # Default case: stay in menu

def create_support_package(docker_manager, config_manager, translator, project_path=None):
    """
    Create a support package for troubleshooting.
    
    Args:
        docker_manager: DockerManager instance
        config_manager: ConfigManager instance
        translator: Translator instance
        project_path: Path to the project directory
    """
    console.print(f"[bold cyan]{translator.get('Creating support package')}...[/]")
    
    # Show information about what's included in the package
    console.print(Panel(
        f"[bold]{translator.get('Support Package Contents')}:[/]\n\n"
        f"[cyan]• {translator.get('Log files')}[/]: Docker container logs (nginx-edge, nginx-auth, teddycloud-app)\n"
        f"[cyan]• {translator.get('Configuration files')}[/]: config.json, config.ini, docker-compose.yml, nginx-configurations\n"
        f"[cyan]• {translator.get('Directory structure')}[/]: Overview of the project directory layout\n\n"
        f"[bold yellow]{translator.get('Note')}:[/] {translator.get('No private keys or credentials will be included in unencrypted form.')}",
        title=f"[bold green]{translator.get('Information')}[/]",
        border_style="blue",
        expand=False
    ))
    
    # Ask user if they want to anonymize sensitive information
    anonymize = questionary.confirm(
        translator.get("Would you like to anonymize sensitive information in logs and configuration files?"),
        default=True,
        style=custom_style
    ).ask()
    
    if anonymize:
        console.print(f"[cyan]{translator.get('Anonymization enabled. Sensitive information will be concealed.')}[/]")
        # Show details about what gets anonymized
        console.print(Panel(
            f"[bold]{translator.get('Anonymization Details')}:[/]\n\n"
            f"[green]• {translator.get('In logs')}:[/] IP addresses, email addresses, domains, MAC addresses, UUIDs, serial numbers\n"
            f"[green]• {translator.get('In config.ini')}:[/] MQTT settings (hostname, username, password), server IPs, URLs, domain names, certificates\n"
            f"[green]• {translator.get('In config.json')}:[/] Domain names, user information, hostnames",
            border_style="green",
            expand=False
        ))
        
        # Show disclaimer in a separate red styled box for better visibility
        console.print(Panel(
            f"[bold]{translator.get('Important')}:[/]\n\n"
            f"{translator.get('Anonymization is pattern-based and may not catch all sensitive data.')}\n"
            f"{translator.get('Patterns may change over time. Please review the package contents before sharing to ensure no personal information is leaked.')}",
            border_style="red",
            expand=False
        ))
    
    # Create support package
    from ..utilities.support_features import SupportPackageCreator
    
    creator = SupportPackageCreator(
        project_path=project_path, 
        docker_manager=docker_manager, 
        config_manager=config_manager,
        anonymize=anonymize
    )
    
    try:
        # Determine the default path (project_path + support subdirectory)
        if project_path:
            default_path = os.path.join(project_path, "support")
            # Create the support directory if it doesn't exist
            os.makedirs(default_path, exist_ok=True)
        else:
            # Fallback to user's Downloads folder if no project path is available
            default_path = str(Path.home() / "Downloads")
        
        # Ask user where to save the package
        output_dir = browse_directory(
            start_path=default_path,
            translator=translator,
            title=translator.get("Select where to save the support package")
        )
        
        if not output_dir:
            console.print(f"[yellow]{translator.get('Operation cancelled.')}[/]")
            return
            
        # Create the package
        output_file = creator.create_support_package(output_dir)
        
        if output_file and os.path.exists(output_file):
            console.print(f"[bold green]{translator.get('Support package created successfully')}:[/]")
            console.print(f"[cyan]{output_file}[/]")
            
            # Open file explorer to show the file on supported platforms
            try:
                if sys.platform.startswith('win'):
                    subprocess.Popen(f'explorer /select,"{output_file}"')
                elif sys.platform.startswith('darwin'):  # macOS
                    subprocess.Popen(['open', '-R', output_file])
                elif sys.platform.startswith('linux'):
                    # Try xdg-open for Linux
                    try:
                        subprocess.Popen(['xdg-open', os.path.dirname(output_file)])
                    except FileNotFoundError:
                        pass  # xdg-open not available, skip opening
            except Exception:
                # Ignore errors when trying to open file explorer
                pass
        else:
            console.print(f"[bold red]{translator.get('Failed to create support package')}[/]")
    except Exception as e:
        console.print(f"[bold red]{translator.get('Error creating support package')}: {e}[/]")