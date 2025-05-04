#!/usr/bin/env python3
"""
Docker management UI for TeddyCloudStarter.
"""
import time

import questionary
from rich import box
from rich.table import Table

from ..utilities.log_viewer import display_live_logs
from ..wizard.ui_helpers import console, custom_style


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
    project_path = None
    if config_manager and config_manager.config:
        project_path = config_manager.config.get("environment", {}).get("path")

    running_services = []
    stopped_services = []

    services = docker_manager.get_services_status(project_path=project_path)

    choices = []
    if services:
        display_services_status(services, translator)

        running_services = [
            svc for svc, info in services.items() if info["state"] == "Running"
        ]
        stopped_services = [
            svc for svc, info in services.items() if info["state"] == "Stopped"
        ]

        choices = create_menu_choices(
            running_services, stopped_services, services, translator
        )
    else:
        console.print(
            f"[yellow]{translator.get('No Docker services found or Docker is not available')}.[/]"
        )
    choices.append({"id": "refresh", "text": translator.get("Refresh status")})
    choices.append({"id": "back", "text": translator.get("Back to main menu")})
    choice_texts = [choice["text"] for choice in choices]
    selected_text = questionary.select(
        translator.get("Docker Management"), choices=choice_texts, style=custom_style
    ).ask()
    selected_id = None
    for choice in choices:
        if choice["text"] == selected_text:
            selected_id = choice["id"]
            break

    return handle_docker_action(
        selected_id,
        translator,
        docker_manager,
        running_services,
        stopped_services,
        project_path,
    )


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
        list: Menu choices with IDs and translated text
    """
    choices = []

    if stopped_services:
        if len(stopped_services) == len(services):
            choices.append(
                {"id": "start_all", "text": translator.get("Start all services")}
            )
        else:
            choices.append(
                {
                    "id": "start_stopped",
                    "text": translator.get("Start stopped services"),
                }
            )

    if len(running_services) == len(services) and running_services:
        choices.append(
            {"id": "restart_all", "text": translator.get("Restart all services")}
        )

    if running_services:
        if len(running_services) == len(services):
            choices.append(
                {"id": "stop_all", "text": translator.get("Stop all services")}
            )
        else:
            choices.append(
                {
                    "id": "stop_running",
                    "text": translator.get("Stop all running services"),
                }
            )

        choices.append(
            {"id": "stop_specific", "text": translator.get("Stop specific service")}
        )

    if stopped_services:
        choices.append(
            {"id": "start_specific", "text": translator.get("Start specific service")}
        )

    if running_services:
        choices.append(
            {
                "id": "restart_specific",
                "text": translator.get("Restart specific service"),
            }
        )

    if running_services:
        choices.append(
            {"id": "logs_all", "text": translator.get("Live logs from all services")}
        )
        choices.append(
            {
                "id": "logs_specific",
                "text": translator.get("Live logs from specific service"),
            }
        )

    return choices


def handle_docker_action(
    action_id,
    translator,
    docker_manager,
    running_services=None,
    stopped_services=None,
    project_path=None,
):
    """
    Handle the selected Docker action.

    Args:
        action_id: The ID of the selected action
        translator: The translator instance for localization
        docker_manager: The docker manager instance
        running_services: List of running service names, defaults to empty list if None
        stopped_services: List of stopped service names, defaults to empty list if None
        project_path: Optional project path for Docker operations

    Returns:
        bool: True if user chose to exit, False otherwise
    """
    running_services = running_services or []
    stopped_services = stopped_services or []

    if action_id in ["start_all", "start_stopped"]:
        docker_manager.start_services(project_path=project_path)
        console.print(f"[bold cyan]{translator.get('Refreshing service status')}...[/]")
        time.sleep(2)
        return False

    elif action_id == "restart_all":
        docker_manager.restart_services(project_path=project_path)
        console.print(f"[bold cyan]{translator.get('Refreshing service status')}...[/]")
        time.sleep(2)
        return False

    elif action_id in ["stop_all", "stop_running"]:
        docker_manager.stop_services(project_path=project_path)
        console.print(f"[bold cyan]{translator.get('Refreshing service status')}...[/]")
        time.sleep(2)
        return False

    elif action_id == "start_specific":
        return handle_start_specific_service(
            translator, docker_manager, stopped_services, project_path
        )

    elif action_id == "restart_specific":
        return handle_restart_specific_service(
            translator, docker_manager, running_services, project_path
        )

    elif action_id == "stop_specific":
        return handle_stop_specific_service(
            translator, docker_manager, running_services, project_path
        )

    elif action_id == "logs_all":
        display_live_logs(docker_manager, project_path=project_path)
        return False

    elif action_id == "logs_specific":
        return handle_live_logs_specific_service(
            translator, docker_manager, running_services, project_path
        )

    elif action_id == "refresh":
        console.print(f"[bold cyan]{translator.get('Refreshing service status')}...[/]")
        return False

    elif action_id == "back":
        console.print(f"[bold cyan]{translator.get('Returning to main menu')}...[/]")
        return True

    return False


def handle_start_specific_service(
    translator, docker_manager, stopped_services=None, project_path=None
):
    """
    Handle starting a specific service.

    Args:
        translator: The translator instance for localization
        docker_manager: The docker manager instance
        stopped_services: List of stopped service names, defaults to empty list if None
        project_path: Optional project path for Docker operations

    Returns:
        bool: True if user chose to exit, False otherwise
    """
    stopped_services = stopped_services or []

    if not stopped_services:
        console.print(
            f"[bold yellow]{translator.get('No stopped services available to start')}.[/]"
        )
        return False
    choices = []
    for service in stopped_services:
        choices.append({"id": service, "text": service})
    choices.append({"id": "back", "text": translator.get("Back")})
    choice_texts = [choice["text"] for choice in choices]
    selected_text = questionary.select(
        translator.get("Select a service to start:"),
        choices=choice_texts,
        style=custom_style,
    ).ask()
    selected_id = "back"
    for choice in choices:
        if choice["text"] == selected_text:
            selected_id = choice["id"]
            break

    if selected_id != "back":
        docker_manager.start_service(selected_id, project_path=project_path)
        console.print(f"[bold cyan]{translator.get('Refreshing service status')}...[/]")
        time.sleep(2)

    return False


def handle_restart_specific_service(
    translator, docker_manager, running_services=None, project_path=None
):
    """
    Handle restarting a specific service.

    Args:
        translator: The translator instance for localization
        docker_manager: The docker manager instance
        running_services: List of running service names, defaults to empty list if None
        project_path: Optional project path for Docker operations

    Returns:
        bool: True if user chose to exit, False otherwise
    """
    running_services = running_services or []

    if not running_services:
        console.print(
            f"[bold yellow]{translator.get('No running services available to restart')}.[/]"
        )
        return False
    choices = []
    for service in running_services:
        choices.append({"id": service, "text": service})
    choices.append({"id": "back", "text": translator.get("Back")})
    choice_texts = [choice["text"] for choice in choices]
    selected_text = questionary.select(
        translator.get("Select a service to restart:"),
        choices=choice_texts,
        style=custom_style,
    ).ask()
    selected_id = "back"
    for choice in choices:
        if choice["text"] == selected_text:
            selected_id = choice["id"]
            break

    if selected_id != "back":
        docker_manager.restart_service(selected_id, project_path=project_path)
        console.print(f"[bold cyan]{translator.get('Refreshing service status')}...[/]")
        time.sleep(2)

    return False


def handle_stop_specific_service(
    translator, docker_manager, running_services=None, project_path=None
):
    """
    Handle stopping a specific service.

    Args:
        translator: The translator instance for localization
        docker_manager: The docker manager instance
        running_services: List of running service names, defaults to empty list if None
        project_path: Optional project path for Docker operations

    Returns:
        bool: True if user chose to exit, False otherwise
    """
    running_services = running_services or []

    if not running_services:
        console.print(
            f"[bold yellow]{translator.get('No running services available to stop')}.[/]"
        )
        return False
    choices = []
    for service in running_services:
        choices.append({"id": service, "text": service})
    choices.append({"id": "back", "text": translator.get("Back")})
    choice_texts = [choice["text"] for choice in choices]
    selected_text = questionary.select(
        translator.get("Select a service to stop:"),
        choices=choice_texts,
        style=custom_style,
    ).ask()
    selected_id = "back"
    for choice in choices:
        if choice["text"] == selected_text:
            selected_id = choice["id"]
            break

    if selected_id != "back":
        docker_manager.stop_service(selected_id, project_path=project_path)
        console.print(f"[bold cyan]{translator.get('Refreshing service status')}...[/]")
        time.sleep(2)

    return False


def handle_live_logs_specific_service(
    translator, docker_manager, running_services=None, project_path=None
):
    """
    Handle showing live logs for a specific service.

    Args:
        translator: The translator instance for localization
        docker_manager: The docker manager instance
        running_services: List of running service names, defaults to empty list if None
        project_path: Optional project path for Docker operations

    Returns:
        bool: True if user chose to exit, False otherwise
    """
    running_services = running_services or []

    if not running_services:
        console.print(
            f"[bold yellow]{translator.get('No running services available to view logs')}.[/]"
        )
        return False
    choices = []
    for service in running_services:
        choices.append({"id": service, "text": service})
    choices.append({"id": "back", "text": translator.get("Back")})
    choice_texts = [choice["text"] for choice in choices]
    selected_text = questionary.select(
        translator.get("Select a service to view logs:"),
        choices=choice_texts,
        style=custom_style,
    ).ask()
    selected_id = "back"
    for choice in choices:
        if choice["text"] == selected_text:
            selected_id = choice["id"]
            break

    if selected_id != "back":
        display_live_logs(docker_manager, selected_id, project_path=project_path)

    return False
