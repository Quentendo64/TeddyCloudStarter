#!/usr/bin/env python3
"""
Configuration management UI module for TeddyCloudStarter.
"""
import questionary
import os
from ..wizard.ui_helpers import console, custom_style
from ..configuration.direct_mode import modify_http_port, modify_https_port, modify_teddycloud_port
from ..configuration.nginx_mode import modify_domain_name, modify_https_mode, modify_security_settings, modify_ip_restrictions
from ..configuration.reset_operations import perform_reset_operations, get_docker_volumes

def show_configuration_management_menu(wizard, config_manager, translator, security_managers=None):
    """Show configuration management menu.
    
    Args:
        wizard: TeddyCloudWizard instance
        config_manager: ConfigManager instance
        translator: TranslationManager instance
        security_managers: Dictionary of security manager instances
        
    Returns:
        bool: True if configuration was modified, False otherwise
    """
    console.print(f"[bold cyan]{translator.get('Configuration Management')}[/]")
    
    current_config = config_manager.config
    current_mode = current_config.get("mode", "direct")
    
    # Check auto-update status to display appropriate menu option
    auto_update_enabled = current_config.get("app_settings", {}).get("auto_update", False)
    auto_update_option = translator.get("Disable auto-update") if auto_update_enabled else translator.get("Enable auto-update")
    
    # Build menu choices based on the current deployment mode
    choices = [
        translator.get("Change deployment mode"),
        translator.get("Change project path"),
        auto_update_option,
        translator.get("Reset TeddyCloudStarter"),  # New reset option
        translator.get("Refresh server configuration"),
        translator.get("Back to main menu")
    ]
    
    # Add mode-specific options
    if current_mode == "direct":
        choices.insert(3, translator.get("Modify HTTP port"))
        choices.insert(4, translator.get("Modify HTTPS port")) 
        #choices.insert(5, translator.get("Modify TeddyCloud port"))
    elif current_mode == "nginx":
        choices.insert(3, translator.get("Modify domain name"))
        choices.insert(4, translator.get("Modify HTTPS configuration"))
        choices.insert(5, translator.get("Modify security settings"))
        choices.insert(6, translator.get("Configure IP address filtering"))  # This restricts access by IP
        
        # Add basic auth bypass option if basic auth is configured
        if (current_config.get("nginx", {}).get("security", {}).get("type") == "basic_auth"):
            choices.insert(7, translator.get("Configure basic auth bypass IPs"))  # This allows IP-based auth bypass
        
    # Show configuration management menu
    action = questionary.select(
        translator.get("What would you like to do?"),
        choices=choices,
        style=custom_style
    ).ask()
    
    if action == translator.get("Change deployment mode"):
        wizard.select_deployment_mode()
        
        # After changing mode, check if we need to configure the new mode
        if config_manager.config["mode"] == "direct":
            wizard.configure_direct_mode()
        elif config_manager.config["mode"] == "nginx":
            wizard.configure_nginx_mode()
            
        # Save the configuration
        config_manager.save()
        return True
        
    elif action == translator.get("Change project path"):
        wizard.select_project_path()
        return True
        
    elif action == translator.get("Enable auto-update") or action == translator.get("Disable auto-update"):
        # Use the toggle_auto_update function we added
        config_manager.toggle_auto_update()
        return True
        
    elif action == translator.get("Reset TeddyCloudStarter"):
        reset_options = handle_reset_wizard(translator)
        if reset_options:
            perform_reset_operations(reset_options, config_manager, wizard, translator)
            return True
        return False
        
    elif action == translator.get("Refresh server configuration"):
        wizard.refresh_server_configuration()
        return True

    elif current_mode == "direct" and action == translator.get("Modify HTTP port"):
        modify_http_port(config_manager.config, translator)
        config_manager.save()
        return True
        
    elif current_mode == "direct" and action == translator.get("Modify HTTPS port"):
        modify_https_port(config_manager.config, translator)
        config_manager.save()
        return True
        
    elif current_mode == "direct" and action == translator.get("Modify TeddyCloud port"):
        modify_teddycloud_port(config_manager.config, translator)
        config_manager.save()
        return True
        
    elif current_mode == "nginx" and action == translator.get("Modify domain name"):
        modify_domain_name(config_manager.config, translator)
        config_manager.save()
        return True
        
    elif current_mode == "nginx" and action == translator.get("Modify HTTPS configuration"):
        modify_https_mode(config_manager.config, translator, security_managers)
        config_manager.save()
        return True
        
    elif current_mode == "nginx" and action == translator.get("Modify security settings"):
        modify_security_settings(config_manager.config, translator, security_managers)
        config_manager.save()
        return True
        
    elif current_mode == "nginx" and action == translator.get("Configure IP address filtering"):
        modify_ip_restrictions(config_manager.config, translator, security_managers)
        config_manager.save()
        return True
        
    elif current_mode == "nginx" and action == translator.get("Configure basic auth bypass IPs"):
        from ..configuration.nginx_mode import configure_auth_bypass_ips
        configure_auth_bypass_ips(config_manager.config, translator, security_managers)
        config_manager.save()
        return True
        
    return False  # Return to main menu

def handle_reset_wizard(translator):
    """Handle the reset wizard with multiple options and subcategories.
    
    Args:
        translator: TranslationManager instance
        
    Returns:
        dict: Dictionary of reset options or None if canceled
    """
    console.print(f"\n[bold yellow]{translator.get('Warning')}: {translator.get('This will reset selected TeddyCloudStarter settings')}[/]")
    
    # Define the main options
    main_options = [
        {'name': translator.get('Remove teddycloud.json'), 'value': 'config_file'},
        {'name': translator.get('Remove ProjectPath data'), 'value': 'project_path_menu'},
        {'name': translator.get('Remove Docker Volumes'), 'value': 'docker_volumes_menu'}
    ]
    
    selected_main_options = questionary.checkbox(
        translator.get("Select items to reset:"),
        choices=[option['name'] for option in main_options],
        style=custom_style
    ).ask()
    
    if not selected_main_options:
        return None
    
    # Convert selected option names to their values
    selected_values = []
    for selected in selected_main_options:
        for option in main_options:
            if option['name'] == selected:
                selected_values.append(option['value'])
    
    # Initialize reset options dictionary
    reset_options = {
        'config_file': False,
        'project_path': False,
        'project_folders': [],
        'docker_all_volumes': False,
        'docker_volumes': []
    }
    
    # Process each selected main option
    for value in selected_values:
        if value == 'config_file':
            reset_options['config_file'] = True
        elif value == 'project_path_menu':
            # Show project path submenu
            handle_project_path_reset(reset_options, translator)
        elif value == 'docker_volumes_menu':
            # Show Docker volumes submenu
            handle_docker_volumes_reset(reset_options, translator)
    
    # If no options were selected in the submenus, return None
    if (not reset_options['config_file'] and 
        not reset_options['project_path'] and 
        not reset_options['project_folders'] and
        not reset_options['docker_all_volumes'] and
        not reset_options['docker_volumes']):
        return None
    
    # Confirm the reset
    confirmed = questionary.confirm(
        translator.get("Are you sure you want to reset these settings? This cannot be undone."),
        default=False,
        style=custom_style
    ).ask()
    
    if confirmed:
        return reset_options
    
    return None

def handle_project_path_reset(reset_options, translator):
    """Handle the project path reset submenu.
    
    Args:
        reset_options: Dictionary to store reset options
        translator: TranslationManager instance
    """
    # Define project path options
    project_path_options = [
        {'name': translator.get('Reset entire ProjectPath'), 'value': 'entire_path'},
        {'name': translator.get('if exist (configurations)'), 'value': 'configurations'},
        {'name': translator.get('if exist (backup)'), 'value': 'backup'},
        {'name': translator.get('if exist (client_certs)'), 'value': 'client_certs'},
        {'name': translator.get('if exist (server_clients)'), 'value': 'server_clients'}
    ]
    
    selected_options = questionary.checkbox(
        translator.get("Select ProjectPath items to reset:"),
        choices=[option['name'] for option in project_path_options],
        style=custom_style
    ).ask()
    
    if not selected_options:
        return
    
    # Process selected project path options
    for selected in selected_options:
        for option in project_path_options:
            if option['name'] == selected:
                if option['value'] == 'entire_path':
                    reset_options['project_path'] = True
                else:
                    reset_options['project_folders'].append(option['value'])

def handle_docker_volumes_reset(reset_options, translator):
    """Handle the Docker volumes reset submenu.
    
    Args:
        reset_options: Dictionary to store reset options
        translator: TranslationManager instance
    """
    # Get the list of available Docker volumes
    volume_info = get_docker_volumes(translator)
    volume_names = list(volume_info.keys())
    
    # Define standard volume options to check for
    standard_volumes = [
        'teddycloudstarter_certs',
        'teddycloudstarter_config',
        'teddycloudstarter_content',
        'teddycloudstarter_library',
        'teddycloudstarter_custom_img',
        'teddycloudstarter_firmware',
        'teddycloudstarter_cache',
        'teddycloudstarter_certbot_conf',
        'teddycloudstarter_certbot_www'
    ]
    
    # Create options list with "if exist" for standard volumes
    docker_options = [
        {'name': translator.get('Remove all Docker volumes'), 'value': 'all_volumes'}
    ]
    
    # Add standard volumes that exist
    for vol in standard_volumes:
        if vol in volume_names:
            docker_options.append({'name': f"{translator.get('if exist')} ({vol})", 'value': vol})
    
    # Add any additional volumes found
    for vol in volume_names:
        if vol not in standard_volumes:
            docker_options.append({'name': vol, 'value': vol})
    
    # If no Docker volumes exist, show message and return
    if len(docker_options) == 1 and not volume_names:
        console.print(f"[yellow]{translator.get('No Docker volumes found')}[/]")
        return
    
    selected_options = questionary.checkbox(
        translator.get("Select Docker volumes to remove:"),
        choices=[option['name'] for option in docker_options],
        style=custom_style
    ).ask()
    
    if not selected_options:
        return
    
    # Process selected Docker volume options
    for selected in selected_options:
        for option in docker_options:
            if option['name'] == selected:
                if option['value'] == 'all_volumes':
                    reset_options['docker_all_volumes'] = True
                else:
                    reset_options['docker_volumes'].append(option['value'])