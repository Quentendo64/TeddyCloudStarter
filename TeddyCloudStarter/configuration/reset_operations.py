#!/usr/bin/env python3
"""
Reset operations module for TeddyCloudStarter configuration.
"""
import os
import subprocess
import shutil

from rich import box
from rich.panel import Panel

from ..utilities.file_system import (
    normalize_path,
    validate_path,
)
from ..wizard.ui_helpers import console
from ..utilities.logger import logger


def reset_config_file(config_manager, translator):
    """
    Reset the configuration file by removing it and loading defaults.

    Args:
        config_manager: ConfigManager instance
        translator: TranslationManager instance

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        config_file_path = config_manager.config_path
        logger.info(f"Attempting to reset configuration file: {config_file_path}")

        if os.path.exists(config_file_path):
            os.remove(config_file_path)
            logger.success(f"Removed configuration file: {config_file_path}")
            console.print(
                f"[green]{translator.get('Removed configuration file')}: {config_file_path}[/]"
            )

        config_manager.reset_config()
        logger.success("Configuration reset to defaults.")
        return True
    except Exception as e:
        logger.error(f"Error resetting configuration file: {str(e)}")
        console.print(
            f"[red]{translator.get('Error resetting configuration file')}: {str(e)}[/]"
        )
        return False


def reset_project_path_data(config_manager, translator, folders=None):
    """
    Reset specific folders in the project path.

    Args:
        config_manager: ConfigManager instance
        translator: TranslationManager instance
        folders: List of folder names to reset, or None to reset the project path itself

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        project_path = config_manager.config.get("project_path")
        logger.info(f"Resetting project path data. Project path: {project_path}")

        if not project_path:
            logger.warning("No project path configured.")
            console.print(f"[yellow]{translator.get('No project path configured')}")
            return True

        if not validate_path(project_path):
            logger.warning(f"Project path does not exist: {project_path}")
            console.print(
                f"[yellow]{translator.get('Project path does not exist')}: {project_path}"
            )

            if folders is None:
                if "project_path" in config_manager.config:
                    config_manager.config["project_path"] = ""
                    config_manager.save()
            return True

        if folders is None:
            # Remove the data folder inside the project path if it exists
            data_folder = normalize_path(os.path.join(project_path, "data"))
            if validate_path(data_folder):
                try:
                    shutil.rmtree(data_folder)
                    logger.success(f"Removed project data folder: {data_folder}")
                    console.print(
                        f"[green]{translator.get('Removed project data folder')}: {data_folder}[/]"
                    )
                except Exception as e:
                    logger.error(f"Error removing project data folder: {str(e)}")
                    console.print(
                        f"[red]{translator.get('Error removing project data folder')}: {str(e)}[/]"
                    )
            logger.success("Project path data reset.")
            console.print(f"[green]{translator.get('Project path data reset')}")

            if "project_path" in config_manager.config:
                config_manager.config["project_path"] = ""
                config_manager.save()
            return True

        for folder in folders:
            folder_path = normalize_path(os.path.join(project_path, folder))
            logger.info(f"Resetting project folder: {folder}")
            if validate_path(folder_path):
                try:
                    shutil.rmtree(folder_path)
                    logger.success(f"Removed project folder: {folder}")
                    console.print(
                        f"[green]{translator.get('Removed project folder')}: {folder}"
                    )
                except Exception as e:
                    logger.error(f"Error removing project folder {folder}: {str(e)}")
                    console.print(
                        f"[red]{translator.get('Error removing project folder')} {folder}: {str(e)}"
                    )
            else:
                logger.warning(f"Project folder does not exist: {folder}")
                console.print(
                    f"[yellow]{translator.get('Project folder does not exist')}: {folder}"
                )

        logger.success("Project folders reset completed.")
        return True
    except Exception as e:
        logger.error(f"Error resetting project path: {str(e)}")
        console.print(
            f"[red]{translator.get('Error resetting project path')}: {str(e)}[/]"
        )
        return False


def reset_docker_volumes(translator, volumes=None, docker_manager=None):
    """
    Reset Docker volumes by removing specified volumes or all with teddycloudstarter prefix.

    Args:
        translator: TranslationManager instance
        volumes: List of volume names to remove, or None to remove all with teddycloudstarter prefix
        docker_manager: DockerManager instance (required for dynamic volume listing)

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info("Removing Docker volumes...")
        console.print(f"[bold yellow]{translator.get('Removing Docker volumes')}...[/]")

        if volumes is None:
            if docker_manager is not None:
                volumes = docker_manager.get_volumes()
            else:
                logger.error("Docker manager instance required for dynamic volume listing.")
                console.print(
                    f"[red]{translator.get('Docker manager instance required for dynamic volume listing')}[/]"
                )
                return False

        if volumes:
            for volume in volumes:
                try:
                    subprocess.run(["docker", "volume", "rm", volume], check=True)
                    logger.success(f"Removed Docker volume: {volume}")
                    console.print(
                        f"[green]{translator.get('Removed Docker volume')}: {volume}[/]"
                    )
                except subprocess.SubprocessError as e:
                    logger.error(f"Error removing Docker volume {volume}: {str(e)}")
                    console.print(
                        f"[red]{translator.get('Error removing Docker volume')} {volume}: {str(e)}[/]"
                    )
        else:
            logger.warning("No Docker volumes found to remove.")
            console.print(
                f"[yellow]{translator.get('No Docker volumes found to remove')}[/]"
            )

        logger.success("Docker volumes reset completed.")
        return True
    except subprocess.SubprocessError as e:
        logger.error(f"Error removing Docker volumes: {str(e)}")
        console.print(
            f"[red]{translator.get('Error removing Docker volumes')}: {str(e)}[/]"
        )
        return False
    except Exception as e:
        logger.error(f"Unexpected error during Docker volumes reset: {str(e)}")
        console.print(f"[red]{translator.get('Unexpected error')}: {str(e)}[/]")
        return False


def perform_reset_operations(reset_options, config_manager, wizard, translator):
    """
    Perform selected reset operations.

    Args:
        reset_options: Dictionary of reset options to perform
        config_manager: ConfigManager instance
        wizard: TeddyCloudWizard instance
        translator: TranslationManager instance

    Returns:
        bool: True if all operations were successful, False otherwise
    """
    success = True

    # Determine if we need to bring down Docker services first
    need_docker_down = (
        reset_options.get("docker_volumes")
        or reset_options.get("docker_all_volumes")
        or reset_options.get("project_folders")
        or reset_options.get("project_path")
    )
    project_path = config_manager.config.get("project_path")
    if not project_path:
        project_path = config_manager.config.get("environment", {}).get("path")
    if need_docker_down and project_path:
        logger.info("Bringing down Docker Compose services before reset operations.")
        wizard.docker_manager.down_services(project_path)

    # 1. Docker volumes first (after services are down)
    docker_volumes = reset_options.get("docker_volumes", [])
    if docker_volumes:
        logger.info(f"Resetting specific Docker volumes: {docker_volumes}")
        if not reset_docker_volumes(
            translator, docker_volumes, docker_manager=wizard.docker_manager
        ):
            logger.warning("Some Docker volumes failed to reset.")
            success = False
    elif reset_options.get("docker_all_volumes"):
        logger.info("Resetting all Docker volumes.")
        if not reset_docker_volumes(translator, docker_manager=wizard.docker_manager):
            logger.warning("Some Docker volumes failed to reset.")
            success = False

    # 2. Project path (folders or entire path)
    project_folders = reset_options.get("project_folders", [])
    if project_folders:
        logger.info(f"Resetting project folders: {project_folders}")
        if not reset_project_path_data(config_manager, translator, project_folders):
            logger.warning("Some project folders failed to reset.")
            success = False
    elif reset_options.get("project_path"):
        # Remove the data folder inside the project path as well
        project_path = config_manager.config.get("project_path")
        if not project_path:
            project_path = config_manager.config.get("environment", {}).get("path")
        if project_path:
            data_folder = normalize_path(os.path.join(project_path, "data"))
            if validate_path(data_folder):
                try:
                    shutil.rmtree(data_folder)
                    logger.success(f"Removed project data folder: {data_folder}")
                    console.print(
                        f"[green]{translator.get('Removed project data folder')}: {data_folder}[/]"
                    )
                except Exception as e:
                    logger.error(f"Error removing project data folder: {str(e)}")
                    console.print(
                        f"[red]{translator.get('Error removing project data folder')}: {str(e)}[/]"
                    )
        logger.info("Resetting entire project path data.")
        if not reset_project_path_data(config_manager, translator):
            logger.warning("Failed to reset project path data.")
            success = False

    # 3. Config file last
    if reset_options.get("config_file"):
        logger.info("Resetting configuration file.")
        if not reset_config_file(config_manager, translator):
            logger.warning("Failed to reset configuration file.")
            success = False

    # No need to bring down Docker services again here

    if success:
        logger.success("Reset completed successfully.")
        console.print(
            f"[bold green]{translator.get('Reset completed successfully')}[/]"
        )
    else:
        logger.warning("Reset completed with some errors.")
        console.print(
            f"[bold yellow]{translator.get('Reset completed with some errors')}[/]"
        )

    if reset_options.get("config_file") or reset_options.get("project_path"):
        logger.info("Reset completed. Starting setup wizard.")
        console.print(
            Panel(
                f"[bold green]{translator.get('Reset completed!')}[/]\n\n"
                f"{translator.get('TeddyCloudStarter has been reset to defaults.')}\n\n"
                f"[bold cyan]{translator.get('The setup wizard will start now for new initialization.')}[/]",
                box=box.ROUNDED,
                border_style="green",
            )
        )
        # Start the setup wizard instead of reloading configuration
        if hasattr(wizard, "run"):
            wizard.run()
        else:
            logger.error("Unable to restart setup wizard. Please restart the application manually.")
            console.print(
                f"[red]{translator.get('Unable to restart setup wizard. Please restart the application manually.')}[/]"
            )

    return success
