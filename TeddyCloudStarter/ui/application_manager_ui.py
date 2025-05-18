#!/usr/bin/env python3
"""
Application management UI for TeddyCloudStarter.
"""
import subprocess
from pathlib import Path

import questionary
from rich import box
from rich.panel import Panel

from ..wizard.ui_helpers import console, custom_style
from ..utilities.logger import logger
from .application_manager import inject_tonies_custom_json, extract_toniebox_information


def show_application_management_menu(config_manager, docker_manager, translator):
    """
    Show Application management submenu with options for managing TeddyCloud application.

    Args:
        config_manager: The configuration manager instance
        docker_manager: The docker manager instance
        translator: The translator instance for localization

    Returns:
        bool: True if user chose to exit, False otherwise
    """
    logger.debug("Entering Application Management menu.")
    choices = [
        translator.get("Inject tonies.custom.json file"),
    ]
    # Only show Extract Toniebox Information if nginx_type is 'extended'
    nginx_type = (
        config_manager.config.get("nginx", {}).get("nginx_type")
        if config_manager and hasattr(config_manager, "config")
        else None
    )
    logger.debug(f"nginx_type from config: {nginx_type}")
    if nginx_type == "extended":
        choices.append(translator.get("Extract Toniebox Information"))
    choices.append(translator.get("Back to main menu"))

    while True:
        logger.debug(f"Prompting user for Application Management action. Choices: {choices}")
        action = questionary.select(
            translator.get("Application Management"),
            choices=choices,
            style=custom_style,
        ).ask()
        logger.info(f"User selected action: {action}")

        if action == translator.get("Inject tonies.custom.json file"):
            logger.debug("User chose to inject tonies.custom.json file.")
            result = inject_tonies_custom_json_ui(config_manager, docker_manager, translator)
            if result == "cancel":
                logger.info("Injection cancelled or failed. Returning to Application Management menu.")
                continue  # Show the Application Management Menu again
            logger.success("Injection of tonies.custom.json completed.")
            return False
        elif action == translator.get("Extract Toniebox Information"):
            logger.debug("User chose to extract Toniebox Information.")
            extract_toniebox_information_ui(config_manager, docker_manager, translator)
            continue
        elif action == translator.get("Back to main menu"):
            logger.info("User chose to return to main menu.")
            console.print(
                f"[bold cyan]{translator.get('Returning to main menu')}...[/]"
            )
            return True
        logger.warning(f"Unknown action selected: {action}")
        return False


def inject_tonies_custom_json_ui(config_manager, docker_manager, translator):
    """
    UI function for injecting the tonies.custom.json file.

    Args:
        config_manager: The configuration manager instance
        docker_manager: The docker manager instance
        translator: The translator instance for localization
    """
    logger.debug("Starting UI for injecting tonies.custom.json.")
    logic_result = inject_tonies_custom_json(config_manager)
    logger.debug(f"inject_tonies_custom_json logic result: {logic_result}")
    if logic_result["status"] == "error":
        logger.error(f"Error injecting tonies.custom.json: {logic_result['message']}")
        console.print(f"[bold red]{translator.get('Error')}: {translator.get(logic_result['message'])}[/]")
        return "cancel"
    if logic_result["status"] == "missing_file":
        source_file = logic_result["source_file"]
        logger.warning(f"tonies.custom.json file missing at {source_file}")
        console.print(f"[bold red]{translator.get('Error')}: {translator.get('The file tonies.custom.json does not exist at')} {source_file}[/]")
        create_empty = questionary.confirm(
            translator.get("Would you like to create an empty tonies.custom.json file?"),
            default=True,
            style=custom_style,
        ).ask()
        logger.info(f"User chose to {'create' if create_empty else 'not create'} an empty tonies.custom.json file.")
        if create_empty:
            try:
                with open(source_file, "w") as f:
                    f.write("[]")
                logger.success(f"Created empty tonies.custom.json file at {source_file}")
                console.print(f"[bold green]{translator.get('Created empty tonies.custom.json file at')} {source_file}[/]")
            except Exception as e:
                logger.error(f"Error creating empty tonies.custom.json file: {e}")
                console.print(f"[bold red]{translator.get('Error creating file')}: {e}[/]")
                return "cancel"
        else:
            logger.info("User cancelled creation of empty tonies.custom.json file.")
            return "cancel"
        # Retry logic after creation
        return inject_tonies_custom_json_ui(config_manager, docker_manager, translator)
    if logic_result["status"] == "manual":
        source_file = logic_result["source_file"]
        logger.info("Manual injection required for tonies.custom.json.")
        console.print(
            Panel(
                f"[bold]{translator.get('Manual steps')}:[/]\n"
                f"1. {translator.get('Copy')} {source_file}\n"
                f"2. {translator.get('To the config volume of the TeddyCloud container')}\n"
                f"   {translator.get('Using command')}: docker cp {source_file} teddycloud-app:/teddycloud/config/tonies.custom.json\n"
                f"   {translator.get('Or')}: docker run --rm -v {source_file}:/src -v teddycloudstarter_config:/dest alpine cp /src /dest/tonies.custom.json\n",
                title=f"[bold cyan]{translator.get('Manual Injection Instructions')}[/]",
                box=box.ROUNDED,
            )
        )
        return "cancel"
    if logic_result["status"] == "success":
        is_temp = logic_result["is_temp"]
        teddycloud_container = logic_result["container"]
        logger.success("Successfully injected tonies.custom.json into config volume.")
        console.print(f"[bold green]{translator.get('Successfully injected tonies.custom.json into config volume')}![/]")
        if not is_temp:
            restart = questionary.confirm(
                translator.get("Would you like to restart the TeddyCloud container to apply changes?"),
                default=True,
                style=custom_style,
            ).ask()
            logger.info(f"User chose to {'restart' if restart else 'not restart'} the TeddyCloud container.")
            if restart:
                try:
                    logger.info(f"Restarting container {teddycloud_container}.")
                    console.print(f"[cyan]{translator.get('Restarting container')} {teddycloud_container}[/]")
                    subprocess.run([
                        "docker", "restart", teddycloud_container
                    ], check=True, capture_output=True, text=True)
                    logger.success(f"TeddyCloud container {teddycloud_container} restarted successfully.")
                    console.print(f"[bold green]{translator.get('TeddyCloud container restarted successfully')}![/]")
                except Exception as e:
                    logger.error(f"Error restarting TeddyCloud container: {e}")
                    console.print(f"[bold red]{translator.get('Error restarting container')}: {e}[/]")
                    console.print(f"[yellow]{translator.get('You may need to restart the container manually')}[/]")
        else:
            logger.info("Container is temporary. User should restart manually.")
            console.print(f"[bold yellow]{translator.get('You should restart your TeddyCloud container to apply changes')}.[/]")
            console.print(f"[green]{translator.get('Use command')}: docker restart teddycloud-app[/]")
    return


def extract_toniebox_information_ui(config_manager, docker_manager, translator):
    """
    UI function for extracting Toniebox information.

    Args:
        config_manager: The configuration manager instance
        docker_manager: The docker manager instance
        translator: The translator instance for localization
    """
    logger.debug("Starting UI for extracting Toniebox information.")
    logic_result = extract_toniebox_information(config_manager)
    logger.debug(f"extract_toniebox_information logic result: {logic_result}")
    if logic_result["status"] == "error":
        logger.error(f"Error extracting Toniebox information: {logic_result['message']}")
        console.print(f"[bold red]{translator.get(logic_result['message'])}[/]")
        return
    logger.success("Toniebox information extracted and saved to configuration.")
    console.print(f"[bold green]{translator.get('Toniebox information extracted and saved to configuration')}[/]")
