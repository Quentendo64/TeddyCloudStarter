#!/usr/bin/env python3
"""
Backup and recovery management UI for TeddyCloudStarter.
"""
import os
import time
import sys
import questionary
import shutil
from pathlib import Path
from ..wizard.ui_helpers import console, custom_style
from ..utilities.file_system import get_project_path

# Platform-specific imports
if sys.platform == 'win32':
    import msvcrt  # For Windows key input
else:
    # For non-Windows platforms
    msvcrt = None

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
    # Get the project path from config manager
    project_path = get_project_path(config_manager)
    if not project_path:
        console.print(f"[bold yellow]{translator.get('No project path configured. Please set up a project path first.')}[/]")
        return True
    
    # Check if there are any backup files before showing the restore option
    backup_dir = os.path.join(project_path, "data", "backup")
    has_backups = os.path.exists(backup_dir) and any(
        f.startswith('teddycloud-') and f.endswith('.tar.gz') 
        for f in os.listdir(backup_dir)
    ) if os.path.exists(backup_dir) else False
    
    # Check if there are any config backups
    has_config_backups = any(
        os.path.isfile(f) and os.path.basename(f).startswith('config.json.backup.') 
        for f in Path(os.path.dirname(config_manager.config_path)).glob('config.json.backup.*')
    )
    
    # Create backup directory if it doesn't exist
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir, exist_ok=True)
    
    choices = [
        translator.get("Backup TeddyCloudStarter Configuration"),
        translator.get("Backup Docker volumes")
    ]
    
    # Only show restore options if backups exist
    if has_backups:
        choices.append(translator.get("Restore Docker volumes"))
    
    if has_config_backups:
        choices.append(translator.get("Restore TeddyCloudStarter Configuration"))
        
    choices.append(translator.get("Back to main menu"))
    
    action = questionary.select(
        translator.get("Backup / Recovery Management"),
        choices=choices,
        style=custom_style
    ).ask()
    
    if action == translator.get("Backup TeddyCloudStarter Configuration"):
        config_manager.backup()
        return False  # Continue showing menu
        
    elif action == translator.get("Backup Docker volumes"):
        show_backup_volumes_menu(docker_manager, translator, project_path)
        return False  # Continue showing menu
        
    elif action == translator.get("Restore Docker volumes"):
        show_restore_volumes_menu(docker_manager, translator, project_path)
        return False  # Continue showing menu
        
    elif action == translator.get("Restore TeddyCloudStarter Configuration"):
        show_restore_config_menu(config_manager, translator)
        return False  # Continue showing menu
    
    # Back to main menu
    return True

def show_backup_volumes_menu(docker_manager, translator, project_path):
    """
    Show menu for backing up Docker volumes.
    
    Args:
        docker_manager: The docker manager instance
        translator: The translator instance for localization
        project_path: Path to the project directory
    """
    # Get available Docker volumes
    volumes = docker_manager.get_volumes()
    
    if not volumes:
        console.print(f"[bold yellow]{translator.get('No Docker volumes found. Make sure Docker is running and volumes exist')}.[/]")
        return
    
    # Add option to backup all volumes
    choices = [translator.get("All volumes")] + volumes + [translator.get("Back")]
    
    selected = questionary.select(
        translator.get("Select a volume to backup:"),
        choices=choices,
        style=custom_style
    ).ask()
    
    if selected == translator.get("Back"):
        return
    
    if selected == translator.get("All volumes"):
        console.print(f"[bold cyan]{translator.get('Backing up all Docker volumes')}...[/]")
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
    # Get available Docker volumes and their backups
    volumes = docker_manager.get_volumes()
    all_backups = docker_manager.get_volume_backups(project_path)
    
    if not volumes:
        console.print(f"[bold yellow]{translator.get('No Docker volumes found. Make sure Docker is running and volumes exist')}.[/]")
        return
    
    if not all_backups:
        console.print(f"[bold yellow]{translator.get('No backup files found. Create backups first')}.[/]")
        return
    
    # Only show volumes that have backups
    volumes_with_backups = [vol for vol in volumes if vol in all_backups]
    
    if not volumes_with_backups:
        console.print(f"[bold yellow]{translator.get('No backups found for any of the existing volumes')}.[/]")
        return
    
    # Let user select a volume to restore
    volume_choices = volumes_with_backups + [translator.get("Back")]
    selected_volume = questionary.select(
        translator.get("Select a volume to restore:"),
        choices=volume_choices,
        style=custom_style
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
    # Get available configuration backups
    config_backups = get_config_backups(config_manager.config_path)
    
    if not config_backups:
        console.print(f"[bold yellow]{translator.get('No configuration backups found. Create a backup first')}.[/]")
        return
    
    # Format backup options with readable dates
    backup_options = []
    for backup_path in config_backups:
        # Extract timestamp from backup filename
        try:
            timestamp = int(os.path.basename(backup_path).split('.')[-1])
            date_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
            backup_options.append((f"{date_str} ({os.path.basename(backup_path)})", backup_path))
        except (ValueError, IndexError):
            # If timestamp can't be parsed, just use the filename
            backup_options.append((os.path.basename(backup_path), backup_path))
    
    # Sort by timestamp (newest first)
    backup_options.sort(key=lambda x: x[1], reverse=True)
    
    choices = [option[0] for option in backup_options] + [translator.get("Back")]
    
    selected = questionary.select(
        translator.get("Select a configuration backup to restore:"),
        choices=choices,
        style=custom_style
    ).ask()
    
    if selected == translator.get("Back"):
        return
    
    # Find the selected backup path
    selected_backup_path = next((path for label, path in backup_options if label == selected), None)
    
    if selected_backup_path:
        if questionary.confirm(
            translator.get("Are you sure you want to restore this configuration backup? Current settings will be overwritten."),
            default=False,
            style=custom_style
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
    
    # Look for files matching the pattern config.json.backup.*
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
        # Create a backup of the current configuration before restoring
        console.print(f"[bold cyan]{translator.get('Creating backup of current configuration before restoring')}...[/]")
        config_manager.backup()
        
        # Restore the selected backup
        shutil.copy2(backup_path, config_manager.config_path)
        
        # Reload the configuration
        config_manager.config = config_manager._load_config()
        
        console.print(f"[bold green]{translator.get('Configuration successfully restored from backup')}.[/]")
        
        # Ask if user wants to restart the application
        if questionary.confirm(
            translator.get("It's recommended to restart the application for changes to take effect. Do you want to restart now?"),
            default=True,
            style=custom_style
        ).ask():
            console.print(f"[bold yellow]{translator.get('Please restart the application manually to apply the restored configuration')}.[/]")
            
    except Exception as e:
        error_msg = f"Error restoring configuration: {str(e)}"
        if translator:
            error_msg = translator.get("Error restoring configuration: {error}").format(error=str(e))
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
        # Refresh the backup list to ensure we have the latest data
        all_backups = docker_manager.get_volume_backups(project_path)
        
        # Check if the selected volume still has backups
        if selected_volume not in all_backups or not all_backups[selected_volume]:
            console.print(f"[bold yellow]{translator.get('No more backups available for this volume')}.[/]")
            return
            
        # Get updated backup files list for the selected volume
        backup_files = all_backups[selected_volume]
        backup_choices = backup_files + [translator.get("Back")]
        
        # Add instructions about viewing or removing backup contents
        console.print(f"[bold cyan]{translator.get('Note: After selecting a backup file, you can')}:[/]")
        console.print(f"[bold cyan]- {translator.get('Press \'L\' to list its contents')}[/]")
        console.print(f"[bold cyan]- {translator.get('Press \'R\' to remove the backup file')}[/]")
        
        # Show the selection
        selected_backup = questionary.select(
            translator.get(f"Select a backup file for {selected_volume}:"),
            choices=backup_choices,
            style=custom_style
        ).ask()
        
        if selected_backup == translator.get("Back"):
            return
        
        # Handle key press for backup file actions - cross-platform approach
        if sys.platform == 'win32' and msvcrt:
            # Windows approach
            while msvcrt.kbhit():
                msvcrt.getch()  # Clear any pending keypresses
                
            console.print(f"[bold cyan]{translator.get('Press \'L\' to list contents, \'R\' to remove backup, or any other key to continue')}...[/]")
            key = msvcrt.getch().decode('utf-8', errors='ignore').lower()
        else:
            # Non-Windows approach using input()
            console.print(f"[bold cyan]{translator.get('Enter \'L\' to list contents, \'R\' to remove backup, or press Enter to continue')}:[/]")
            key = input().lower()
        
        if key == 'l':
            # Show backup contents
            show_backup_contents(selected_backup, docker_manager, translator, project_path)
            continue  # Stay in the loop to allow another selection
        elif key == 'r':
            # Remove backup file
            if remove_backup_file(selected_backup, translator, project_path):
                continue  # Return to the backup selection
            else:
                # If removal was cancelled or failed, continue loop
                continue
        
        # Proceed with restore
        restore_from_backup(selected_volume, selected_backup, docker_manager, translator, project_path)
        break  # Exit the loop after restore attempt

def show_backup_contents(backup_file, docker_manager, translator, project_path):
    """
    Show the contents of a backup file and wait for user to press a key.
    
    Args:
        backup_file: Name of the backup file to show contents of
        docker_manager: The docker manager instance
        translator: The translator instance for localization
        project_path: Path to the project directory
    """
    console.print(f"\n[bold cyan]{translator.get('Showing contents of')} {backup_file}:[/]")
    docker_manager.show_backup_contents(backup_file, project_path)
    console.print(f"\n[bold yellow]{translator.get('Press Enter to continue')}...[/]")
    input()  # Wait for user to press Enter

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
        console.print(f"[bold red]{translator.get('Backup file')} {backup_file} {translator.get('not found')}.[/]")
        return False
        
    # Ask for confirmation
    if questionary.confirm(
        translator.get(f"Are you sure you want to permanently delete {backup_file}?"),
        default=False,
        style=custom_style
    ).ask():
        try:
            os.remove(backup_path)
            console.print(f"[bold green]{translator.get('Backup file')} {backup_file} {translator.get('removed successfully')}.[/]")
            return True
        except Exception as e:
            console.print(f"[bold red]{translator.get('Error removing backup file')}: {e}[/]")
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
        translator.get(f"Are you sure you want to restore {volume} from {backup_file}?\n"
        f"{translator.get('This will overwrite current data and may require service restart')}"),
        default=False,
        style=custom_style
    ).ask():
        # Check if services are running that use this volume
        services_status = docker_manager.get_services_status()
        running_services = [svc for svc, info in services_status.items() if info["state"] == "Running"]
        
        if running_services:
            console.print(f"[bold yellow]{translator.get('Warning: Some services are running. It\'s recommended to stop them before restoring volumes')}.[/]")
            if questionary.confirm(
                translator.get("Would you like to stop all Docker services before restoring?"),
                default=True,
                style=custom_style
            ).ask():
                docker_manager.stop_services()
                console.print(f"[bold cyan]{translator.get('Waiting for services to stop')}...[/]")
                time.sleep(2)
        
        # Perform the restore
        if docker_manager.restore_volume(volume, backup_file, project_path):
            if questionary.confirm(
                translator.get("Restore completed. Would you like to restart Docker services?"),
                default=True,
                style=custom_style
            ).ask():
                docker_manager.restart_services()
    else:
        # User cancelled
        pass