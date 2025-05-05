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
from ..utilities.logger import logger


def show_docker_management_menu(translator, docker_manager, config_manager=None):
    logger.debug("Entering show_docker_management_menu.")
    project_path = None
    if config_manager and config_manager.config:
        project_path = config_manager.config.get("environment", {}).get("path")
        logger.debug(f"Project path from config: {project_path}")

    running_services = []
    stopped_services = []
    logger.debug("Getting Docker services status.")
    services = docker_manager.get_services_status(project_path=project_path)
    logger.debug(f"Services status: {services}")

    choices = []
    if services:
        logger.debug("Displaying services status table.")
        display_services_status(services, translator)

        running_services = [
            svc for svc, info in services.items() if info["state"] == "Running"
        ]
        stopped_services = [
            svc for svc, info in services.items() if info["state"] == "Stopped"
        ]
        logger.debug(f"Running services: {running_services}")
        logger.debug(f"Stopped services: {stopped_services}")

        choices = create_menu_choices(
            running_services, stopped_services, services, translator
        )
        logger.debug(f"Menu choices: {choices}")
    else:
        logger.warning("No Docker services found or Docker is not available.")
        console.print(
            f"[yellow]{translator.get('No Docker services found or Docker is not available')}.[/]"
        )
    choices.append({"id": "refresh", "text": translator.get("Refresh status")})
    choices.append({"id": "back", "text": translator.get("Back to main menu")})
    choice_texts = [choice["text"] for choice in choices]
    logger.debug(f"Prompting user for Docker management action. Choices: {choice_texts}")
    selected_text = questionary.select(
        translator.get("Docker Management"), choices=choice_texts, style=custom_style
    ).ask()
    logger.info(f"User selected: {selected_text}")
    selected_id = None
    for choice in choices:
        if choice["text"] == selected_text:
            selected_id = choice["id"]
            break
    logger.debug(f"Selected action id: {selected_id}")

    return handle_docker_action(
        selected_id,
        translator,
        docker_manager,
        running_services,
        stopped_services,
        project_path,
    )


def display_services_status(services, translator):
    logger.debug("Displaying Docker services status table.")
    table = Table(title=translator.get("Docker Services Status"), box=box.ROUNDED)
    table.add_column(translator.get("Service"), style="cyan")
    table.add_column(translator.get("Status"), style="green")
    table.add_column(translator.get("Running For"), style="cyan")

    for service_name, info in services.items():
        status = info["state"]
        running_for = info["running_for"]
        status_color = "green" if status == "Running" else "yellow"
        table.add_row(service_name, f"[{status_color}]{status}[/]", running_for or "")
    logger.debug("Printing services status table to console.")
    console.print(table)


def create_menu_choices(running_services, stopped_services, services, translator):
    logger.debug("Creating menu choices for Docker management.")
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
    logger.debug(f"Final menu choices: {choices}")
    return choices


def handle_docker_action(
    action_id,
    translator,
    docker_manager,
    running_services=None,
    stopped_services=None,
    project_path=None,
):
    logger.debug(f"Handling Docker action: {action_id}")
    running_services = running_services or []
    stopped_services = stopped_services or []

    if action_id in ["start_all", "start_stopped"]:
        logger.info(f"Starting services: {action_id}")
        docker_manager.start_services(project_path=project_path)
        console.print(f"[bold cyan]{translator.get('Refreshing service status')}...[/]")
        time.sleep(2)
        return False

    elif action_id == "restart_all":
        logger.info("Restarting all services.")
        docker_manager.restart_services(project_path=project_path)
        console.print(f"[bold cyan]{translator.get('Refreshing service status')}...[/]")
        time.sleep(2)
        return False

    elif action_id in ["stop_all", "stop_running"]:
        logger.info(f"Stopping services: {action_id}")
        docker_manager.stop_services(project_path=project_path)
        console.print(f"[bold cyan]{translator.get('Refreshing service status')}...[/]")
        time.sleep(2)
        return False

    elif action_id == "start_specific":
        logger.debug("User chose to start a specific service.")
        return handle_start_specific_service(
            translator, docker_manager, stopped_services, project_path
        )

    elif action_id == "restart_specific":
        logger.debug("User chose to restart a specific service.")
        return handle_restart_specific_service(
            translator, docker_manager, running_services, project_path
        )

    elif action_id == "stop_specific":
        logger.debug("User chose to stop a specific service.")
        return handle_stop_specific_service(
            translator, docker_manager, running_services, project_path
        )

    elif action_id == "logs_all":
        logger.info("Displaying live logs from all services.")
        display_live_logs(docker_manager, project_path=project_path)
        return False

    elif action_id == "logs_specific":
        logger.debug("User chose to view live logs from a specific service.")
        return handle_live_logs_specific_service(
            translator, docker_manager, running_services, project_path
        )

    elif action_id == "refresh":
        logger.info("Refreshing Docker service status.")
        console.print(f"[bold cyan]{translator.get('Refreshing service status')}...[/]")
        return False

    elif action_id == "back":
        logger.info("Returning to main menu from Docker management.")
        console.print(f"[bold cyan]{translator.get('Returning to main menu')}...[/]")
        return True

    logger.warning(f"Unknown Docker action id: {action_id}")
    return False


def handle_start_specific_service(
    translator, docker_manager, stopped_services=None, project_path=None
):
    logger.debug("Handling start of a specific Docker service.")
    stopped_services = stopped_services or []

    if not stopped_services:
        logger.warning("No stopped services available to start.")
        console.print(
            f"[bold yellow]{translator.get('No stopped services available to start')}.[/]"
        )
        return False
    choices = [{"id": service, "text": service} for service in stopped_services]
    choices.append({"id": "back", "text": translator.get("Back")})
    choice_texts = [choice["text"] for choice in choices]
    logger.debug(f"Prompting user to select service to start. Choices: {choice_texts}")
    selected_text = questionary.select(
        translator.get("Select a service to start:"),
        choices=choice_texts,
        style=custom_style,
    ).ask()
    logger.info(f"User selected to start: {selected_text}")
    selected_id = "back"
    for choice in choices:
        if choice["text"] == selected_text:
            selected_id = choice["id"]
            break
    logger.debug(f"Selected service to start: {selected_id}")

    if selected_id != "back":
        docker_manager.start_service(selected_id, project_path=project_path)
        console.print(f"[bold cyan]{translator.get('Refreshing service status')}...[/]")
        time.sleep(2)

    return False


def handle_restart_specific_service(
    translator, docker_manager, running_services=None, project_path=None
):
    logger.debug("Handling restart of a specific Docker service.")
    running_services = running_services or []

    if not running_services:
        logger.warning("No running services available to restart.")
        console.print(
            f"[bold yellow]{translator.get('No running services available to restart')}.[/]"
        )
        return False
    choices = [{"id": service, "text": service} for service in running_services]
    choices.append({"id": "back", "text": translator.get("Back")})
    choice_texts = [choice["text"] for choice in choices]
    logger.debug(f"Prompting user to select service to restart. Choices: {choice_texts}")
    selected_text = questionary.select(
        translator.get("Select a service to restart:"),
        choices=choice_texts,
        style=custom_style,
    ).ask()
    logger.info(f"User selected to restart: {selected_text}")
    selected_id = "back"
    for choice in choices:
        if choice["text"] == selected_text:
            selected_id = choice["id"]
            break
    logger.debug(f"Selected service to restart: {selected_id}")

    if selected_id != "back":
        docker_manager.restart_service(selected_id, project_path=project_path)
        console.print(f"[bold cyan]{translator.get('Refreshing service status')}...[/]")
        time.sleep(2)

    return False


def handle_stop_specific_service(
    translator, docker_manager, running_services=None, project_path=None
):
    logger.debug("Handling stop of a specific Docker service.")
    running_services = running_services or []

    if not running_services:
        logger.warning("No running services available to stop.")
        console.print(
            f"[bold yellow]{translator.get('No running services available to stop')}.[/]"
        )
        return False
    choices = [{"id": service, "text": service} for service in running_services]
    choices.append({"id": "back", "text": translator.get("Back")})
    choice_texts = [choice["text"] for choice in choices]
    logger.debug(f"Prompting user to select service to stop. Choices: {choice_texts}")
    selected_text = questionary.select(
        translator.get("Select a service to stop:"),
        choices=choice_texts,
        style=custom_style,
    ).ask()
    logger.info(f"User selected to stop: {selected_text}")
    selected_id = "back"
    for choice in choices:
        if choice["text"] == selected_text:
            selected_id = choice["id"]
            break
    logger.debug(f"Selected service to stop: {selected_id}")

    if selected_id != "back":
        docker_manager.stop_service(selected_id, project_path=project_path)
        console.print(f"[bold cyan]{translator.get('Refreshing service status')}...[/]")
        time.sleep(2)

    return False


def handle_live_logs_specific_service(
    translator, docker_manager, running_services=None, project_path=None
):
    logger.debug("Handling live logs for a specific Docker service.")
    running_services = running_services or []

    if not running_services:
        logger.warning("No running services available to view logs.")
        console.print(
            f"[bold yellow]{translator.get('No running services available to view logs')}.[/]"
        )
        return False
    choices = [{"id": service, "text": service} for service in running_services]
    choices.append({"id": "back", "text": translator.get("Back")})
    choice_texts = [choice["text"] for choice in choices]
    logger.debug(f"Prompting user to select service to view logs. Choices: {choice_texts}")
    selected_text = questionary.select(
        translator.get("Select a service to view logs:"),
        choices=choice_texts,
        style=custom_style,
    ).ask()
    logger.info(f"User selected to view logs: {selected_text}")
    selected_id = "back"
    for choice in choices:
        if choice["text"] == selected_text:
            selected_id = choice["id"]
            break
    logger.debug(f"Selected service to view logs: {selected_id}")

    if selected_id != "back":
        display_live_logs(docker_manager, selected_id, project_path=project_path)

    return False
