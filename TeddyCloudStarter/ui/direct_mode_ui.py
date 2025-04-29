#!/usr/bin/env python3
"""
UI module for Direct mode configuration in TeddyCloudStarter.
"""
import questionary
from ..wizard.ui_helpers import console, custom_style
from ..utilities.network import check_port_available


def confirm_use_http(default_value, translator):
    """
    Ask user if they want to expose the admin interface on HTTP.
    
    Args:
        default_value: Default choice
        translator: The translator instance for localization
        
    Returns:
        bool: True if confirmed, False otherwise
    """
    return questionary.confirm(
        translator.get("Would you like to expose the TeddyCloud Admin Web Interface on HTTP (port 80)?"),
        default=default_value,
        style=custom_style
    ).ask()


def confirm_custom_http_port(translator):
    """
    Ask user if they want to specify a different HTTP port.
    
    Args:
        translator: The translator instance for localization
        
    Returns:
        bool: True if confirmed, False otherwise
    """
    return questionary.confirm(
        translator.get("Would you like to specify a different port?"),
        default=True,
        style=custom_style
    ).ask()


def prompt_for_http_port(default_port, translator):
    """
    Prompt user to enter HTTP port.
    
    Args:
        default_port: Default port value
        translator: The translator instance for localization
        
    Returns:
        str: The entered port
    """
    return questionary.text(
        translator.get("Enter HTTP port:"),
        default=default_port,
        validate=lambda p: p.isdigit() and 1 <= int(p) <= 65535,
        style=custom_style
    ).ask()


def confirm_use_https(default_value, translator):
    """
    Ask user if they want to expose the admin interface on HTTPS.
    
    Args:
        default_value: Default choice
        translator: The translator instance for localization
        
    Returns:
        bool: True if confirmed, False otherwise
    """
    return questionary.confirm(
        translator.get("Would you like to expose the TeddyCloud Admin Web Interface on HTTPS (port 8443)?"),
        default=default_value,
        style=custom_style
    ).ask()


def confirm_custom_https_port(translator):
    """
    Ask user if they want to specify a different HTTPS port.
    
    Args:
        translator: The translator instance for localization
        
    Returns:
        bool: True if confirmed, False otherwise
    """
    return questionary.confirm(
        translator.get("Would you like to specify a different port?"),
        default=True,
        style=custom_style
    ).ask()


def prompt_for_https_port(default_port, translator):
    """
    Prompt user to enter HTTPS port.
    
    Args:
        default_port: Default port value
        translator: The translator instance for localization
        
    Returns:
        str: The entered port
    """
    return questionary.text(
        translator.get("Enter HTTPS port:"),
        default=default_port,
        validate=lambda p: p.isdigit() and 1 <= int(p) <= 65535,
        style=custom_style
    ).ask()


def confirm_custom_teddycloud_port(translator):
    """
    Ask user if they want to specify a different port for TeddyCloud backend.
    
    Args:
        translator: The translator instance for localization
        
    Returns:
        bool: True if confirmed, False otherwise
    """
    return questionary.confirm(
        translator.get("Would you like to specify a different port for TeddyCloud backend (normally 443)?"),
        default=True,
        style=custom_style
    ).ask()


def prompt_for_teddycloud_port(default_port, translator):
    """
    Prompt user to enter TeddyCloud backend port.
    
    Args:
        default_port: Default port value
        translator: The translator instance for localization
        
    Returns:
        str: The entered port
    """
    return questionary.text(
        translator.get("Enter TeddyCloud backend port:"),
        default=default_port,
        validate=lambda p: p.isdigit() and 1 <= int(p) <= 65535,
        style=custom_style
    ).ask()


def confirm_port_usage_anyway(port, translator):
    """
    Ask user if they want to use a port that appears to be in use.
    
    Args:
        port: The port number
        translator: The translator instance for localization
        
    Returns:
        bool: True if confirmed, False otherwise
    """
    console.print(f"[bold yellow]{translator.get('Warning')}: {translator.get('Port')} {port} {translator.get('appears to be in use')}.[/]")
    return questionary.confirm(
        translator.get("Would you like to use this port anyway?"),
        default=False,
        style=custom_style
    ).ask()


def confirm_no_admin_interface(translator):
    """
    Ask user to confirm if they want to continue without admin interface access.
    
    Args:
        translator: The translator instance for localization
        
    Returns:
        bool: True if confirmed, False otherwise
    """
    console.print(f"[bold red]{translator.get('Warning')}: {translator.get('You have not exposed any ports for the admin interface')}.[/]")
    return questionary.confirm(
        translator.get("Are you sure you want to continue without access to the admin interface?"),
        default=False,
        style=custom_style
    ).ask()