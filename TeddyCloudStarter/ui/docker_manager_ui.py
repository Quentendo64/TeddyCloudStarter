#!/usr/bin/env python3
"""
Docker management UI for TeddyCloudStarter.
"""
import time
import questionary
from rich.table import Table
from rich import box
from ..wizard.ui_helpers import console, custom_style
from ..utilities.log import display_live_logs

def show_docker_management_menu(translator, docker_manager, config_manager=None):
    """
    Show Docker management submenu with service status and control options.
    
    Args:
        translator: The translator instance for localization
        docker_manager: The docker manager instance
        config_manager: Optional config manager for getting project path
        
    Returns:
        bool: True if user chose to exit, False otherwise
    """
    # Get project path from config if available
    project_path = None
    if config_manager and config_manager.config:
        project_path = config_manager.config.get("environment", {}).get("path")
    
    # Get current status of services
    services = docker_manager.get_services_status(project_path=project_path)
    
    # Display service status if services exist
    if services:
        display_services_status(services, translator)
        
        # Determine which services are running and stopped
        running_services = [svc for svc, info in services.items() if info["state"] == "Running"]
        stopped_services = [svc for svc, info in services.items() if info["state"] == "Stopped"]
        
        # Determine menu options based on service status
        choices = create_menu_choices(running_services, stopped_services, services, translator)
    else:
        console.print(f"[yellow]{translator.get('No Docker services found or Docker is not available')}.[/]")
        choices = []
        
    # Always include Refresh status and Back options
    choices.append(translator.get("Refresh status"))
    choices.append(translator.get("Back to main menu"))
    
    action = questionary.select(
        translator.get("Docker Management"),
        choices=choices,
        style=custom_style
    ).ask()
    
    # Handle menu option selection
    return handle_docker_action(action, translator, docker_manager, running_services, stopped_services, project_path)

def display_services_status(services, translator):
    """
    Display the status of Docker services in a table.
    
    Args:
        services: Dictionary of services with their status
        translator: The translator instance for localization
    """
    table = Table(title=translator.get("Docker Services Status"), box=box.ROUNDED)
    table.add_column(translator.get("Service"), style="cyan")
    table.add_column(translator.get("Status"), style="green")
    table.add_column(translator.get("Running For"), style="cyan")
    
    for service_name, info in services.items():
        status = info["state"]
        running_for = info["running_for"]
        status_color = "green" if status == "Running" else "yellow"
        table.add_row(service_name, f"[{status_color}]{status}[/]", running_for or "")
    
    console.print(table)

def create_menu_choices(running_services, stopped_services, services, translator):
    """
    Create menu choices based on the status of services.
    
    Args:
        running_services: List of running service names
        stopped_services: List of stopped service names
        services: Dictionary of services with their status
        translator: The translator instance for localization
        
    Returns:
        list: Menu choices
    """
    choices = []
    
    # Only show start all services if there are stopped services
    if stopped_services:
        if len(stopped_services) == len(services):
            choices.append(translator.get("Start all services"))
        else:
            choices.append(translator.get("Start stopped services"))
    
    # Only show restart all services if all services are running
    if len(running_services) == len(services) and running_services:
        choices.append(translator.get("Restart all services"))
    
    # Only show stop all services if all services are running
    if running_services and len(running_services) == len(services):
        choices.append(translator.get("Stop all services"))
    # Show stop specific service if any services are running
    elif running_services:
        choices.append(translator.get("Stop specific service"))
        
    # Show start specific service if any services are stopped
    if stopped_services:
        choices.append(translator.get("Start specific service"))
        
    # Show restart specific service if at least one service is running
    if running_services:
        choices.append(translator.get("Restart specific service"))

    # Log options - show only if at least one service is running
    if running_services:
        choices.append(translator.get("Live logs from all services"))
        choices.append(translator.get("Live logs from specific service"))
        
    return choices

def handle_docker_action(action, translator, docker_manager, running_services, stopped_services, project_path=None):
    """
    Handle the selected Docker action.
    
    Args:
        action: The selected action
        translator: The translator instance for localization
        docker_manager: The docker manager instance
        running_services: List of running service names
        stopped_services: List of stopped service names
        project_path: Optional project path for Docker operations
        
    Returns:
        bool: True if user chose to exit, False otherwise
    """
    if action == translator.get("Start all services") or action == translator.get("Start stopped services"):
        docker_manager.start_services(project_path=project_path)
        console.print(f"[bold cyan]{translator.get('Refreshing service status')}...[/]")
        time.sleep(2)  # Wait a moment for Docker to start the services
        return False  # Show the menu again with refreshed status
        
    elif action == translator.get("Restart all services"):
        docker_manager.restart_services(project_path=project_path)
        console.print(f"[bold cyan]{translator.get('Refreshing service status')}...[/]")
        time.sleep(2)  # Wait a moment for Docker to restart the services
        return False  # Show the menu again with refreshed status
    
    elif action == translator.get("Stop all services"):
        docker_manager.stop_services(project_path=project_path)
        console.print(f"[bold cyan]{translator.get('Refreshing service status')}...[/]")
        time.sleep(2)  # Wait a moment for Docker to stop the services
        return False  # Show the menu again with refreshed status
        
    elif action == translator.get("Start specific service"):
        return handle_start_specific_service(translator, docker_manager, stopped_services, project_path)
        
    elif action == translator.get("Restart specific service"):
        return handle_restart_specific_service(translator, docker_manager, running_services, project_path)
        
    elif action == translator.get("Stop specific service"):
        return handle_stop_specific_service(translator, docker_manager, running_services, project_path)

    elif action == translator.get("Live logs from all services"):
        display_live_logs(docker_manager, project_path=project_path)
        return False  # Show the menu again
        
    elif action == translator.get("Live logs from specific service"):
        return handle_live_logs_specific_service(translator, docker_manager, running_services, project_path)
        
    elif action == translator.get("Refresh status"):
        console.print(f"[bold cyan]{translator.get('Refreshing service status')}...[/]")
        return False  # Show the menu again with refreshed status
    
    elif action == translator.get("Back to main menu"):
        console.print(f"[bold cyan]{translator.get('Returning to main menu')}...[/]")
        return True  # Return to main menu
    
    # Default case if none of the above match
    return False

def handle_start_specific_service(translator, docker_manager, stopped_services, project_path=None):
    """
    Handle starting a specific service.
    
    Args:
        translator: The translator instance for localization
        docker_manager: The docker manager instance
        stopped_services: List of stopped service names
        project_path: Optional project path for Docker operations
        
    Returns:
        bool: True if user chose to exit, False otherwise
    """
    if not stopped_services:
        console.print(f"[bold yellow]{translator.get('No stopped services available to start')}.[/]")
        return False  # Show the menu again
    
    service_choices = stopped_services + [translator.get("Back")]
    
    selected_service = questionary.select(
        translator.get("Select a service to start:"),
        choices=service_choices,
        style=custom_style
    ).ask()
    
    if selected_service and selected_service != translator.get("Back"):
        docker_manager.start_service(selected_service, project_path=project_path)
        console.print(f"[bold cyan]{translator.get('Refreshing service status')}...[/]")
        time.sleep(2)  # Wait a moment for Docker to start the service
    
    return False  # Show the menu again

def handle_restart_specific_service(translator, docker_manager, running_services, project_path=None):
    """
    Handle restarting a specific service.
    
    Args:
        translator: The translator instance for localization
        docker_manager: The docker manager instance
        running_services: List of running service names
        project_path: Optional project path for Docker operations
        
    Returns:
        bool: True if user chose to exit, False otherwise
    """
    if not running_services:
        console.print(f"[bold yellow]{translator.get('No running services available to restart')}.[/]")
        return False  # Show the menu again
    
    service_choices = running_services + [translator.get("Back")]
    
    selected_service = questionary.select(
        translator.get("Select a service to restart:"),
        choices=service_choices,
        style=custom_style
    ).ask()
    
    if selected_service and selected_service != translator.get("Back"):
        docker_manager.restart_service(selected_service, project_path=project_path)
        console.print(f"[bold cyan]{translator.get('Refreshing service status')}...[/]")
        time.sleep(2)  # Wait a moment for Docker to restart the service
    
    return False  # Show the menu again

def handle_stop_specific_service(translator, docker_manager, running_services, project_path=None):
    """
    Handle stopping a specific service.
    
    Args:
        translator: The translator instance for localization
        docker_manager: The docker manager instance
        running_services: List of running service names
        project_path: Optional project path for Docker operations
        
    Returns:
        bool: True if user chose to exit, False otherwise
    """
    if not running_services:
        console.print(f"[bold yellow]{translator.get('No running services available to stop')}.[/]")
        return False  # Show the menu again
    
    service_choices = running_services + [translator.get("Back")]
    
    selected_service = questionary.select(
        translator.get("Select a service to stop:"),
        choices=service_choices,
        style=custom_style
    ).ask()
    
    if selected_service and selected_service != translator.get("Back"):
        docker_manager.stop_service(selected_service, project_path=project_path)
        console.print(f"[bold cyan]{translator.get('Refreshing service status')}...[/]")
        time.sleep(2)  # Wait a moment for Docker to stop the service
    
    return False  # Show the menu again

def handle_live_logs_specific_service(translator, docker_manager, running_services, project_path=None):
    """
    Handle showing live logs for a specific service.
    
    Args:
        translator: The translator instance for localization
        docker_manager: The docker manager instance
        running_services: List of running service names
        project_path: Optional project path for Docker operations
        
    Returns:
        bool: True if user chose to exit, False otherwise
    """
    if not running_services:
        console.print(f"[bold yellow]{translator.get('No running services available to view logs')}.[/]")
        return False  # Show the menu again
    
    service_choices = running_services + [translator.get("Back")]
    
    selected_service = questionary.select(
        translator.get("Select a service to view logs:"),
        choices=service_choices,
        style=custom_style
    ).ask()
    
    if selected_service and selected_service != translator.get("Back"):
        display_live_logs(docker_manager, selected_service, project_path=project_path)
    
    return False  # Show the menu again