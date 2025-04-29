#!/usr/bin/env python3
"""
Direct mode configuration for TeddyCloudStarter.
"""
from ..wizard.ui_helpers import console
from ..utilities.network import check_port_available
from ..ui.direct_mode_ui import (
    confirm_use_http,
    confirm_custom_http_port,
    prompt_for_http_port,
    confirm_use_https,
    confirm_custom_https_port,
    prompt_for_https_port,
    confirm_custom_teddycloud_port,
    prompt_for_teddycloud_port,
    confirm_port_usage_anyway,
    confirm_no_admin_interface
)

def configure_direct_mode(config, translator):
    """
    Configure direct deployment mode settings.
    
    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        
    Returns:
        dict: The updated configuration dictionary
    """
    # Initialize ports dictionary if it doesn't exist
    if "ports" not in config:
        config["ports"] = {
            "admin_http": None,
            "admin_https": None,
            "teddycloud": None
        }
        
    ports = config["ports"]
    
    # Configure HTTP port
    _configure_http_port(ports, translator)
    
    # Configure HTTPS port
    _configure_https_port(ports, translator)
    
    # Configure TeddyCloud backend port
    _configure_teddycloud_port(ports, translator)
    
    # Warn about admin interface accessibility
    if not ports["admin_http"] and not ports["admin_https"]:
        if not confirm_no_admin_interface(translator):
            return configure_direct_mode(config, translator)  # Start over
            
    return config

def _configure_http_port(ports, translator):
    """
    Configure HTTP port for direct mode.
    
    Args:
        ports: The ports configuration dictionary
        translator: The translator instance for localization
    """
    current_port = ports["admin_http"]
    
    use_http = confirm_use_http(True, translator)
    
    if use_http:
        port_80_available = check_port_available(80)
        if not port_80_available:
            console.print(f"[bold yellow]{translator.get('Warning')}: {translator.get('Port 80 appears to be in use')}.[/]")
            custom_port = confirm_custom_http_port(translator)
            
            if custom_port:
                http_port = prompt_for_http_port("8080", translator)
                ports["admin_http"] = int(http_port)
            else:
                ports["admin_http"] = 80
        else:
            ports["admin_http"] = 80
    else:
        ports["admin_http"] = None

def _configure_https_port(ports, translator):
    """
    Configure HTTPS port for direct mode.
    
    Args:
        ports: The ports configuration dictionary
        translator: The translator instance for localization
    """
    use_https = confirm_use_https(True, translator)
    
    if use_https:
        port_8443_available = check_port_available(8443)
        if not port_8443_available:
            console.print(f"[bold yellow]{translator.get('Warning')}: {translator.get('Port 8443 appears to be in use')}.[/]")
            custom_port = confirm_custom_https_port(translator)
            
            if custom_port:
                https_port = prompt_for_https_port("8444", translator)
                ports["admin_https"] = int(https_port)
            else:
                ports["admin_https"] = 8443
        else:
            ports["admin_https"] = 8443
    else:
        ports["admin_https"] = None

def _configure_teddycloud_port(ports, translator):
    """
    Configure TeddyCloud backend port for direct mode.
    
    Args:
        ports: The ports configuration dictionary
        translator: The translator instance for localization
    """
    port_443_available = check_port_available(443)
    if not port_443_available:
        console.print(f"[bold yellow]{translator.get('Warning')}: {translator.get('Port 443 appears to be in use')}.[/]")
        custom_port = confirm_custom_teddycloud_port(translator)
        
        if custom_port:
            tc_port = prompt_for_teddycloud_port("4443", translator)
            ports["teddycloud"] = int(tc_port)
        else:
            ports["teddycloud"] = 443
    else:
        ports["teddycloud"] = 443

def modify_http_port(config, translator):
    """
    Modify HTTP port for direct mode.
    
    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
    """
    ports = config["ports"]
    current_port = ports["admin_http"]
    
    console.print(f"[bold cyan]{translator.get('Current HTTP port')}: {current_port or translator.get('Not enabled')}[/]")
    
    use_http = confirm_use_http(current_port is not None, translator)
    
    if use_http:
        default_port = str(current_port) if current_port else "80"
        http_port = prompt_for_http_port(default_port, translator)
        
        # If the port changed, check if it's available
        new_port = int(http_port)
        if new_port != current_port and not check_port_available(new_port):
            if not confirm_port_usage_anyway(new_port, translator):
                return modify_http_port(config, translator)
        
        ports["admin_http"] = new_port
        console.print(f"[bold green]{translator.get('HTTP port updated to')} {new_port}[/]")
    else:
        ports["admin_http"] = None
        console.print(f"[bold green]{translator.get('HTTP interface disabled')}[/]")
    
    return config

def modify_https_port(config, translator):
    """
    Modify HTTPS port for direct mode.
    
    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
    """
    ports = config["ports"]
    current_port = ports["admin_https"]
    
    console.print(f"[bold cyan]{translator.get('Current HTTPS port')}: {current_port or translator.get('Not enabled')}[/]")
    
    use_https = confirm_use_https(current_port is not None, translator)
    
    if use_https:
        default_port = str(current_port) if current_port else "8443"
        https_port = prompt_for_https_port(default_port, translator)
        
        # If the port changed, check if it's available
        new_port = int(https_port)
        if new_port != current_port and not check_port_available(new_port):
            if not confirm_port_usage_anyway(new_port, translator):
                return modify_https_port(config, translator)
                
        ports["admin_https"] = new_port
        console.print(f"[bold green]{translator.get('HTTPS port updated to')} {new_port}[/]")
    else:
        ports["admin_https"] = None
        console.print(f"[bold green]{translator.get('HTTPS interface disabled')}[/]")
    
    # Warn about admin interface accessibility
    if not ports["admin_http"] and not ports["admin_https"]:
        if not confirm_no_admin_interface(translator):
            return modify_https_port(config, translator)  # Try again
    
    return config

def modify_teddycloud_port(config, translator):
    """
    Modify TeddyCloud backend port for direct mode.
    
    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
    """
    ports = config["ports"]
    current_port = ports["teddycloud"]
    
    console.print(f"[bold cyan]{translator.get('Current TeddyCloud backend port')}: {current_port}[/]")
    
    default_port = str(current_port) if current_port else "443"
    tc_port = prompt_for_teddycloud_port(default_port, translator)
    
    # If the port changed, check if it's available
    new_port = int(tc_port)
    if new_port != current_port and not check_port_available(new_port):
        if not confirm_port_usage_anyway(new_port, translator):
            return modify_teddycloud_port(config, translator)
            
    ports["teddycloud"] = new_port
    console.print(f"[bold green]{translator.get('TeddyCloud backend port updated to')} {new_port}[/]")
    
    return config