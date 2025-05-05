#!/usr/bin/env python3
"""
Backup and recovery management UI for TeddyCloudStarter.
"""
import os
import sys
import time
import shutil
from pathlib import Path

import questionary

from ..utilities.file_system import get_project_path
from ..utilities.log_viewer import capture_keypress
from ..wizard.ui_helpers import console, custom_style
from ..utilities.logger import logger


def show_backup_recovery_menu(config_manager, docker_manager, translator):
    """
    Show backup and recovery management submenu.

    Args:
        config_manager: The configuration manager instance
        docker_manager: The docker manager instance
        translator: The translator instance for localization

    Returns:
        bool: True if user chose to exit, False otherwise
    """
    logger.debug("Entering Backup/Recovery Management menu.")
    while True:
        project_path = get_project_path(config_manager)
        logger.debug(f"Project path: {project_path}")
        if not project_path:
            logger.warning("No project path configured. Prompting user to set up project path.")
            console.print(
                f"[bold yellow]{translator.get('No project path configured. Please set up a project path first.')}[/]"
            )
            return True

        backup_dir = os.path.join(project_path, "data", "backup")
        logger.debug(f"Backup directory: {backup_dir}")
        has_backups = (
            os.path.exists(backup_dir)
            and any(
                f.startswith("teddycloud-") and f.endswith(".tar.gz")
                for f in os.listdir(backup_dir)
            )
            if os.path.exists(backup_dir)
            else False
        )
        logger.debug(f"Has Docker volume backups: {has_backups}")

        has_config_backups = any(
            os.path.isfile(f) and os.path.basename(f).startswith("config.json.backup.")
            for f in Path(os.path.dirname(config_manager.config_path)).glob(
                "config.json.backup.*"
            )
        )
        logger.debug(f"Has configuration backups: {has_config_backups}")

        if not os.path.exists(backup_dir):
            logger.info(f"Backup directory does not exist. Creating: {backup_dir}")
            os.makedirs(backup_dir, exist_ok=True)

        choices = [
            translator.get("Backup TeddyCloudStarter Configuration"),
            translator.get("Backup Docker volumes"),
        ]

        if has_backups:
            choices.append(translator.get("Restore Docker volumes"))

        if has_config_backups:
            choices.append(translator.get("Restore TeddyCloudStarter Configuration"))

        choices.append(translator.get("Back to main menu"))

        logger.debug(f"Backup/Recovery menu choices: {choices}")
        action = questionary.select(
            translator.get("Backup / Recovery Management"),
            choices=choices,
            style=custom_style,
        ).ask()
        logger.info(f"User selected backup/recovery action: {action}")

        if action == translator.get("Backup TeddyCloudStarter Configuration"):
            logger.debug("User chose to backup TeddyCloudStarter configuration.")
            config_manager.backup()
            continue
        elif action == translator.get("Backup Docker volumes"):
            logger.debug("User chose to backup Docker volumes.")
            show_backup_volumes_menu(docker_manager, translator, project_path)
            continue
        elif action == translator.get("Restore Docker volumes"):
            logger.debug("User chose to restore Docker volumes.")
            show_restore_volumes_menu(docker_manager, translator, project_path)
            continue
        elif action == translator.get("Restore TeddyCloudStarter Configuration"):
            logger.debug("User chose to restore TeddyCloudStarter configuration.")
            show_restore_config_menu(config_manager, translator)
            continue
        elif action == translator.get("Back to main menu"):
            logger.info("User chose to return to main menu from backup/recovery menu.")
            return True
        else:
            logger.warning(f"Unknown action selected in backup/recovery menu: {action}")
            return True


def show_backup_volumes_menu(docker_manager, translator, project_path):
    """
    Show menu for backing up Docker volumes.

    Args:
        docker_manager: The docker manager instance
        translator: The translator instance for localization
        project_path: Path to the project directory
    """
    volumes = docker_manager.get_volumes()

    if not volumes:
        console.print(
            f"[bold yellow]{translator.get('No Docker volumes found. Make sure Docker is running and volumes exist')}.[/]"
        )
        return

    choices = [translator.get("All volumes")] + volumes + [translator.get("Back")]

    selected = questionary.select(
        translator.get("Select a volume to backup:"),
        choices=choices,
        style=custom_style,
    ).ask()

    if selected == translator.get("Back"):
        return

    if selected == translator.get("All volumes"):
        console.print(
            f"[bold cyan]{translator.get('Backing up all Docker volumes')}...[/]"
        )
        for volume in volumes:
            docker_manager.backup_volume(volume, project_path)
    else:
        docker_manager.backup_volume(selected, project_path)


def show_restore_volumes_menu(docker_manager, translator, project_path):
    """
    Show menu for restoring Docker volumes.

    Args:
        docker_manager: The docker manager instance
        translator: The translator instance for localization
        project_path: Path to the project directory
    """
    volumes = docker_manager.get_volumes()
    all_backups = docker_manager.get_volume_backups(project_path)

    if not volumes:
        console.print(
            f"[bold yellow]{translator.get('No Docker volumes found. Make sure Docker is running and volumes exist')}.[/]"
        )
        return

    if not all_backups:
        console.print(
            f"[bold yellow]{translator.get('No backup files found. Create backups first')}.[/]"
        )
        return

    volumes_with_backups = [vol for vol in volumes if vol in all_backups]

    if not volumes_with_backups:
        console.print(
            f"[bold yellow]{translator.get('No backups found for any of the existing volumes')}.[/]"
        )
        return

    volume_choices = volumes_with_backups + [translator.get("Back")]
    selected_volume = questionary.select(
        translator.get("Select a volume to restore:"),
        choices=volume_choices,
        style=custom_style,
    ).ask()

    if selected_volume == translator.get("Back"):
        return

    handle_backup_selection(selected_volume, docker_manager, translator, project_path)


def show_restore_config_menu(config_manager, translator):
    """
    Show menu for restoring TeddyCloudStarter configuration from backups.

    Args:
        config_manager: The configuration manager instance
        translator: The translator instance for localization
    """
    config_backups = get_config_backups(config_manager.config_path)

    if not config_backups:
        console.print(
            f"[bold yellow]{translator.get('No configuration backups found. Create a backup first')}.[/]"
        )
        return

    backup_options = []
    for backup_path in config_backups:
        try:
            timestamp = int(os.path.basename(backup_path).split(".")[-1])
            date_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
            backup_options.append(
                (f"{date_str} ({os.path.basename(backup_path)})", backup_path)
            )
        except (ValueError, IndexError):
            backup_options.append((os.path.basename(backup_path), backup_path))

    backup_options.sort(key=lambda x: x[1], reverse=True)

    choices = [option[0] for option in backup_options] + [translator.get("Back")]

    selected = questionary.select(
        translator.get("Select a configuration backup to restore:"),
        choices=choices,
        style=custom_style,
    ).ask()

    if selected == translator.get("Back"):
        return

    selected_backup_path = next(
        (path for label, path in backup_options if label == selected), None
    )

    if selected_backup_path:
        if questionary.confirm(
            translator.get(
                "Are you sure you want to restore this configuration backup? Current settings will be overwritten."
            ),
            default=False,
            style=custom_style,
        ).ask():
            restore_config_backup(selected_backup_path, config_manager, translator)


def get_config_backups(config_path):
    """
    Get list of available configuration backup files.

    Args:
        config_path: Path to the configuration file

    Returns:
        list: List of backup file paths
    """
    config_dir = os.path.dirname(config_path)
    config_name = os.path.basename(config_path)

    backup_pattern = f"{config_name}.backup.*"
    backup_files = list(Path(config_dir).glob(backup_pattern))

    return [str(path) for path in backup_files if path.is_file()]


def restore_config_backup(backup_path, config_manager, translator):
    """
    Restore configuration from backup file.

    Args:
        backup_path: Path to the backup file
        config_manager: The configuration manager instance
        translator: The translator instance for localization
    """
    try:
        console.print(
            f"[bold cyan]{translator.get('Creating backup of current configuration before restoring')}...[/]"
        )
        config_manager.backup()
        shutil.copy2(backup_path, config_manager.config_path)
        config_manager.config = config_manager._load_config()
        console.print(
            f"[bold green]{translator.get('Configuration successfully restored from backup')}.[/]"
        )
        if questionary.confirm(
            translator.get(
                "It's recommended to restart the application for changes to take effect. Do you want to restart now?"
            ),
            default=True,
            style=custom_style,
        ).ask():
            console.print(
                f"[bold yellow]{translator.get('Restarting application...')}[/]"
            )
            sys.stdout.flush()
            sys.stderr.flush()
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            console.print(
                f"[bold yellow]{translator.get('Please restart the application manually to apply the restored configuration')}.[/]"
            )
    except Exception as e:
        error_msg = f"Error restoring configuration: {str(e)}"
        if translator:
            error_msg = translator.get("Error restoring configuration: {error}").format(
                error=str(e)
            )
        console.print(f"[bold red]{error_msg}[/]")


def handle_backup_selection(selected_volume, docker_manager, translator, project_path):
    """
    Handle backup file selection and restoration.

    Args:
        selected_volume: The name of the selected volume
        docker_manager: The docker manager instance
        translator: The translator instance for localization
        project_path: Path to the project directory
    """
    while True:
        all_backups = docker_manager.get_volume_backups(project_path)

        if selected_volume not in all_backups or not all_backups[selected_volume]:
            console.print(
                f"[bold yellow]{translator.get('No more backups available for this volume')}.[/]"
            )
            return

        backup_files = all_backups[selected_volume]
        backup_choices = backup_files + [translator.get("Back")]

        console.print(
            f"[bold cyan]{translator.get('Note: After selecting a backup file, you can')}:[/]"
        )
        console.print(
            f"[bold cyan]- {translator.get('Press \'L\' to list its contents')}[/]"
        )
        console.print(
            f"[bold cyan]- {translator.get('Press \'R\' to remove the backup file')}[/]"
        )

        selected_backup = questionary.select(
            translator.get(f"Select a backup file for {selected_volume}:"),
            choices=backup_choices,
            style=custom_style,
        ).ask()

        if selected_backup == translator.get("Back"):
            return

        console.print(
            f"[bold cyan]{translator.get('Press \'L\' to list contents, \'R\' to remove backup, or any other key to continue')}...[/]"
        )

        key = None
        while key is None:
            key = capture_keypress()
            if key is None:
                time.sleep(0.1)

        if key == "l":
            show_backup_contents(
                selected_backup, docker_manager, translator, project_path
            )
            continue
        elif key == "r":
            if remove_backup_file(selected_backup, translator, project_path):
                continue
            else:
                continue

        restore_from_backup(
            selected_volume, selected_backup, docker_manager, translator, project_path
        )
        break


def show_backup_contents(backup_file, docker_manager, translator, project_path):
    """
    Show the contents of a backup file and wait for user to press a key.

    Args:
        backup_file: Name of the backup file to show contents of
        docker_manager: The docker manager instance
        translator: The translator instance for localization
        project_path: Path to the project directory
    """
    console.print(
        f"\n[bold cyan]{translator.get('Showing contents of')} {backup_file}:[/]"
    )
    docker_manager.show_backup_contents(backup_file, project_path)
    console.print(f"\n[bold yellow]{translator.get('Press Enter to continue')}...[/]")
    input()


def remove_backup_file(backup_file, translator, project_path):
    """
    Remove a backup file after confirmation.

    Args:
        backup_file: Name of the backup file to remove
        translator: The translator instance for localization
        project_path: Path to the project directory

    Returns:
        bool: True if the file was removed, False otherwise
    """
    backup_path = os.path.join(project_path, "data", "backup", backup_file)
    if not os.path.exists(backup_path):
        console.print(
            f"[bold red]{translator.get('Backup file')} {backup_file} {translator.get('not found')}.[/]"
        )
        return False

    if questionary.confirm(
        translator.get(f"Are you sure you want to permanently delete {backup_file}?"),
        default=False,
        style=custom_style,
    ).ask():
        try:
            os.remove(backup_path)
            console.print(
                f"[bold green]{translator.get('Backup file')} {backup_file} {translator.get('removed successfully')}.[/]"
            )
            return True
        except Exception as e:
            console.print(
                f"[bold red]{translator.get('Error removing backup file')}: {e}[/]"
            )
            return False
    else:
        console.print(f"[yellow]{translator.get('Deletion cancelled')}.[/]")
        return False


def restore_from_backup(volume, backup_file, docker_manager, translator, project_path):
    """
    Restore a volume from a backup file.

    Args:
        volume: The name of the volume to restore
        backup_file: The name of the backup file to restore from
        docker_manager: The docker manager instance
        translator: The translator instance for localization
        project_path: Path to the project directory
    """
    if questionary.confirm(
        translator.get(
            f"Are you sure you want to restore {volume} from {backup_file}?\n"
            f"{translator.get('This will overwrite current data and may require service restart')}"
        ),
        default=False,
        style=custom_style,
    ).ask():
        services_status = docker_manager.get_services_status()
        running_services = [
            svc for svc, info in services_status.items() if info["state"] == "Running"
        ]

        if running_services:
            console.print(
                f"[bold yellow]{translator.get('Warning: Some services are running. It\'s recommended to stop them before restoring volumes')}.[/]"
            )
            if questionary.confirm(
                translator.get(
                    "Would you like to stop all Docker services before restoring?"
                ),
                default=True,
                style=custom_style,
            ).ask():
                docker_manager.stop_services()
                console.print(
                    f"[bold cyan]{translator.get('Waiting for services to stop')}...[/]"
                )
                time.sleep(2)

        if docker_manager.restore_volume(volume, backup_file, project_path):
            if questionary.confirm(
                translator.get(
                    "Restore completed. Would you like to restart Docker services?"
                ),
                default=True,
                style=custom_style,
            ).ask():
                docker_manager.restart_services()
    else:
        pass
