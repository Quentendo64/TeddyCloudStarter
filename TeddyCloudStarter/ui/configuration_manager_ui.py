#!/usr/bin/env python3
"""
Configuration management UI module for TeddyCloudStarter.
"""
import questionary
from ..wizard.ui_helpers import console, custom_style
from ..configuration.direct_mode import modify_http_port, modify_https_port, modify_teddycloud_port
from ..configuration.nginx_mode import modify_domain_name, modify_https_mode, modify_security_settings

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
    
    # Build menu choices based on the current deployment mode
    choices = [
        translator.get("Change deployment mode"),
        translator.get("Change project path"),
        translator.get("Refresh server configuration"),
        translator.get("Back to main menu")
    ]
    
    # Add mode-specific options
    if current_mode == "direct":
        choices.insert(2, translator.get("Modify HTTP port"))
        choices.insert(3, translator.get("Modify HTTPS port")) 
        choices.insert(4, translator.get("Modify TeddyCloud port"))
    elif current_mode == "nginx":
        choices.insert(2, translator.get("Modify domain name"))
        choices.insert(3, translator.get("Modify HTTPS configuration"))
        choices.insert(4, translator.get("Modify security settings"))
        
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
        if security_managers:
            modify_https_mode(config_manager.config, translator, security_managers)
        else:
            console.print(f"[yellow]{translator.get('Warning')}: {translator.get('No security managers provided.')}[/]")
            modify_https_mode(config_manager.config, translator)
        config_manager.save()
        return True
        
    elif current_mode == "nginx" and action == translator.get("Modify security settings"):
        # Make sure basic_auth_manager is available in security_managers
        if security_managers and "basic_auth_manager" not in security_managers and hasattr(wizard, "basic_auth_manager"):
            security_managers["basic_auth_manager"] = wizard.basic_auth_manager
            
        if security_managers:
            modify_security_settings(config_manager.config, translator, security_managers)
        else:
            console.print(f"[yellow]{translator.get('Warning')}: {translator.get('No security managers provided.')}[/]")
            # Initialize security managers as empty dict if none provided
            empty_security_managers = {}
            if hasattr(wizard, "basic_auth_manager"):
                empty_security_managers["basic_auth_manager"] = wizard.basic_auth_manager
            modify_security_settings(config_manager.config, translator, empty_security_managers)
        config_manager.save()
        return True
        
    return False  # Return to main menu