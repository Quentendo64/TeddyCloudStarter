#!/usr/bin/env python3
"""
Reset operations module for TeddyCloudStarter configuration.
"""
import os
import subprocess
from ..wizard.ui_helpers import console

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
        # Get the config file path
        config_file_path = config_manager.config_path
        
        # Remove the file if it exists
        if os.path.exists(config_file_path):
            os.remove(config_file_path)
            console.print(f"[green]{translator.get('Removed configuration file')}: {config_file_path}[/]")
        
        # Reset the configuration in memory
        config_manager.reset_config()
        return True
    except Exception as e:
        console.print(f"[red]{translator.get('Error resetting configuration file')}: {str(e)}[/]")
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
        # Get current project path
        project_path = config_manager.config.get("project_path")
        
        if not project_path:
            console.print(f"[yellow]{translator.get('No project path configured')}")
            return True
        
        if not os.path.exists(project_path):
            console.print(f"[yellow]{translator.get('Project path does not exist')}: {project_path}")
            
            # Clear project path in configuration if we're resetting the path itself
            if folders is None:
                if "project_path" in config_manager.config:
                    config_manager.config["project_path"] = ""
                    config_manager.save()
            return True
        
        # If no specific folders were requested, reset the entire project path
        if folders is None:
            console.print(f"[green]{translator.get('Project path data reset')}")
            
            # Clear project path in configuration
            if "project_path" in config_manager.config:
                config_manager.config["project_path"] = ""
                config_manager.save()
            return True
        
        # Process each requested folder
        for folder in folders:
            folder_path = os.path.join(project_path, folder)
            if os.path.exists(folder_path):
                import shutil
                try:
                    shutil.rmtree(folder_path)
                    console.print(f"[green]{translator.get('Removed project folder')}: {folder}")
                except Exception as e:
                    console.print(f"[red]{translator.get('Error removing project folder')} {folder}: {str(e)}")
            else:
                console.print(f"[yellow]{translator.get('Project folder does not exist')}: {folder}")
                
        return True
    except Exception as e:
        console.print(f"[red]{translator.get('Error resetting project path')}: {str(e)}")
        return False

def get_docker_volumes(translator, filter_prefix="teddycloudstarter_"):
    """
    Get a list of Docker volumes with the specified prefix.
    
    Args:
        translator: TranslationManager instance
        filter_prefix: Prefix to filter volumes by
        
    Returns:
        dict: Dictionary mapping volume names to their labels
    """
    try:
        # Get list of Docker volumes with formatted output
        result = subprocess.run(
            ["docker", "volume", "ls", "--filter", f"name={filter_prefix}", "--format", "{{.Name}}"],
            capture_output=True, text=True, check=True
        )
        volumes = result.stdout.strip().split('\n')
        volumes = [v for v in volumes if v]  # Remove empty entries
        
        volume_info = {}
        
        # Get detailed info for each volume
        for volume in volumes:
            try:
                # Get labels for the volume
                inspect_result = subprocess.run(
                    ["docker", "volume", "inspect", volume],
                    capture_output=True, text=True, check=True
                )
                import json
                inspect_data = json.loads(inspect_result.stdout)
                if inspect_data and len(inspect_data) > 0:
                    labels = inspect_data[0].get("Labels", {}) or {}
                    volume_info[volume] = labels
            except (subprocess.SubprocessError, json.JSONDecodeError) as e:
                console.print(f"[yellow]{translator.get('Error inspecting volume')} {volume}: {str(e)}")
                volume_info[volume] = {}
                
        return volume_info
    except subprocess.SubprocessError as e:
        console.print(f"[yellow]{translator.get('Error listing Docker volumes')}: {str(e)}")
        return {}

def reset_docker_volumes(translator, volumes=None):
    """
    Reset Docker volumes by removing specified volumes or all with teddycloudstarter prefix.
    
    Args:
        translator: TranslationManager instance
        volumes: List of volume names to remove, or None to remove all with teddycloudstarter prefix
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        console.print(f"[bold yellow]{translator.get('Removing Docker volumes')}...[/]")
        
        if volumes is None:
            # Get all teddycloudstarter volumes
            volume_info = get_docker_volumes(translator)
            volumes = list(volume_info.keys())
        
        if volumes:
            # Remove each specified volume
            for volume in volumes:
                try:
                    subprocess.run(["docker", "volume", "rm", volume], check=True)
                    console.print(f"[green]{translator.get('Removed Docker volume')}: {volume}[/]")
                except subprocess.SubprocessError as e:
                    console.print(f"[red]{translator.get('Error removing Docker volume')} {volume}: {str(e)}")
        else:
            console.print(f"[yellow]{translator.get('No Docker volumes found to remove')}[/]")
        
        return True
    except subprocess.SubprocessError as e:
        console.print(f"[red]{translator.get('Error removing Docker volumes')}: {str(e)}[/]")
        return False
    except Exception as e:
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
    
    # Process config file reset
    if reset_options.get('config_file'):
        if not reset_config_file(config_manager, translator):
            success = False
    
    # Process project path folders reset
    project_folders = reset_options.get('project_folders', [])
    if project_folders:
        if not reset_project_path_data(config_manager, translator, project_folders):
            success = False
    elif reset_options.get('project_path'):
        # Reset the entire project path if selected
        if not reset_project_path_data(config_manager, translator):
            success = False
    
    # Process Docker volumes reset
    docker_volumes = reset_options.get('docker_volumes', [])
    if docker_volumes:
        if not reset_docker_volumes(translator, docker_volumes):
            success = False
    elif reset_options.get('docker_all_volumes'):
        # Reset all Docker volumes if selected
        if not reset_docker_volumes(translator):
            success = False
    
    if success:
        console.print(f"[bold green]{translator.get('Reset completed successfully')}[/]")
    else:
        console.print(f"[bold yellow]{translator.get('Reset completed with some errors')}[/]")
    
    # Reload configuration if needed
    if reset_options.get('config_file') or reset_options.get('project_path'):
        console.print(f"[yellow]{translator.get('Reloading configuration')}...[/]")
        wizard.reload_configuration()
    
    return success