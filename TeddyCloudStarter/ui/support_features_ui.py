#!/usr/bin/env python3
"""
Support features UI for TeddyCloudStarter.
"""
import os
import questionary
from pathlib import Path
from rich.panel import Panel
from rich import box

from ..wizard.ui_helpers import console, custom_style
from ..utilities.support_features import SupportPackageCreator
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
        create_support_package(config_manager, docker_manager, translator)
        return False  # Stay in support menu
    
    elif action == translator.get("Back to main menu"):
        return True  # Return to main menu
    
    return False  # Default case: stay in menu

def create_support_package(config_manager, docker_manager, translator):
    """
    Create a support package with relevant information for troubleshooting.
    
    Args:
        config_manager: The configuration manager instance
        docker_manager: The docker manager instance
        translator: The translator instance for localization
    """
    # Display information about what will be collected
    console.print(Panel(
        f"[bold cyan]{translator.get('Creating Support Package')}[/]\n\n"
        f"{translator.get('This will collect the following information:')}\n"
        f"• {translator.get('Log files from nginx-edge, nginx-auth, teddycloud-app')}\n"
        f"• {translator.get('Config from teddycloud-app')}\n"
        f"• {translator.get('Directory tree from ./data')}\n"
        f"• {translator.get('config.json of TeddyCloudStarter')}\n\n"
        f"{translator.get('The package will help diagnose issues with your TeddyCloud setup.')}",
        box=box.ROUNDED,
        border_style="blue"
    ))
    
    # Confirm before creating package
    confirm = questionary.confirm(
        translator.get("Do you want to create a support package?"),
        default=True,
        style=custom_style
    ).ask()
    
    if not confirm:
        console.print(f"[yellow]{translator.get('Operation cancelled')}.[/]")
        return
    
    # Ask for output location
    default_path = config_manager.config.get("environment", {}).get("path", os.getcwd())
    
    console.print(f"[cyan]{translator.get('Please select a location to save the support package:')}[/]")
    output_path = browse_directory(default_path, translator, translator.get("Select Output Directory"))
    
    if not output_path:
        console.print(f"[yellow]{translator.get('Operation cancelled')}.[/]")
        return
    
    try:
        # Create package
        console.print(f"[cyan]{translator.get('Creating support package, please wait...')}[/]")
        
        # Get project path from config
        project_path = config_manager.config.get("environment", {}).get("path")
        
        # Create package creator instance
        package_creator = SupportPackageCreator(
            project_path=project_path,
            docker_manager=docker_manager,
            config_manager=config_manager
        )
        
        # Create the package
        package_path = package_creator.create_support_package(output_path)
        
        console.print(f"[bold green]{translator.get('Support package created successfully!')}[/]")
        console.print(f"[green]{translator.get('Package location')}: {package_path}[/]")
        
        # Show what's included in the package
        console.print(Panel(
            f"[bold green]{translator.get('Support Package Contents')}[/]\n\n"
            f"• {translator.get('Logs')}: nginx-edge.log, nginx-auth.log, teddycloud-app.log\n"
            f"• {translator.get('Configs')}: config.json, config.yaml, tonies.custom.json\n"
            f"• {translator.get('Directory tree')}: directory_structure.txt",
            box=box.ROUNDED,
            border_style="green"
        ))
        
    except Exception as e:
        console.print(f"[bold red]{translator.get('Error creating support package')}: {str(e)}[/]")