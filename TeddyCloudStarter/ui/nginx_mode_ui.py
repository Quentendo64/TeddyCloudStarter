#!/usr/bin/env python3
"""
UI module for Nginx mode configuration in TeddyCloudStarter.
"""
import questionary
import os
import subprocess
from pathlib import Path
from rich.panel import Panel
from rich import box
from rich.prompt import Prompt

from ..wizard.ui_helpers import console, custom_style
from ..utilities.network import check_port_available, check_domain_resolvable
from ..utilities.validation import validate_domain_name, validate_ip_address


def prompt_for_domain(current_domain="", translator=None):
    """
    Prompt user to enter a domain name.
    
    Args:
        current_domain: Current domain name (if any)
        translator: The translator instance for localization
        
    Returns:
        str: The entered domain name
    """
    return questionary.text(
        "Enter the domain name for your TeddyCloud instance:",
        default=current_domain,
        validate=lambda d: validate_domain_name(d),
        style=custom_style
    ).ask()


def display_letsencrypt_not_available_warning(domain, translator):
    """
    Display a warning that Let's Encrypt is not available for the domain.
    
    Args:
        domain: The domain name
        translator: The translator instance for localization
    """
    console.print(Panel(
        f"[bold yellow]{translator.get('Let\'s Encrypt Not Available')}[/]\n\n"
        f"{translator.get('The domain')} \"{domain}\" {translator.get('could not be resolved using public DNS servers (Quad9)')}\n"
        f"{translator.get('Let\'s Encrypt requires a publicly resolvable domain to issue certificates.')}\n"
        f"{translator.get('You can use self-signed or custom certificates for your setup.')}",
        box=box.ROUNDED,
        border_style="yellow"
    ))


def prompt_for_https_mode(choices, default_choice, translator):
    """
    Prompt user to select an HTTPS mode.
    
    Args:
        choices: List of available HTTPS mode choices
        default_choice: Default choice to select
        translator: The translator instance for localization
        
    Returns:
        str: The selected HTTPS mode option text
    """
    return questionary.select(
        translator.get("How would you like to handle HTTPS?"),
        choices=choices,
        default=default_choice,
        style=custom_style
    ).ask()


def display_letsencrypt_requirements(translator):
    """
    Display Let's Encrypt requirements panel.
    
    Args:
        translator: The translator instance for localization
    """
    console.print(Panel(
        f"[bold yellow]{translator.get('Let\'s Encrypt Requirements')}[/]\n\n"
        f"{translator.get('To use Let\'s Encrypt, you need:')}\n"
        f"1. {translator.get('A public domain name pointing to this server')}\n"
        f"2. {translator.get('Public internet access on ports 80 and 443')}\n"
        f"3. {translator.get('This server must be reachable from the internet')}",
        box=box.ROUNDED,
        border_style="yellow"
    ))


def confirm_letsencrypt_requirements(translator):
    """
    Ask user to confirm they meet Let's Encrypt requirements.
    
    Args:
        translator: The translator instance for localization
        
    Returns:
        bool: True if confirmed, False otherwise
    """
    return questionary.confirm(
        translator.get("Do you meet these requirements?"),
        default=True,
        style=custom_style
    ).ask()


def confirm_test_certificate(translator):
    """
    Ask user if they want to test if Let's Encrypt can issue a certificate.
    
    Args:
        translator: The translator instance for localization
        
    Returns:
        bool: True if confirmed, False otherwise
    """
    return questionary.confirm(
        translator.get("Would you like to test if Let's Encrypt can issue a certificate for your domain?"),
        default=True,
        style=custom_style
    ).ask()


def display_self_signed_certificate_info(domain, translator):
    """
    Display information about self-signed certificate generation.
    
    Args:
        domain: The domain name
        translator: The translator instance for localization
    """
    console.print(Panel(
        f"[bold cyan]{translator.get('Self-Signed Certificate Generation')}[/]\n\n"
        f"{translator.get('A self-signed certificate will be generated for')} '{domain}'.\n"
        f"{translator.get('This certificate will not be trusted by browsers, but is suitable for testing and development.')}",
        box=box.ROUNDED,
        border_style="cyan"
    ))


def prompt_security_type(translator):
    """
    Prompt user to select a security type.
    
    Args:
        translator: The translator instance for localization
        
    Returns:
        str: The selected security type option text
    """
    return questionary.select(
        translator.get("How would you like to secure your TeddyCloud instance?"),
        choices=[
            translator.get("No additional security"),
            translator.get("Basic Authentication (.htpasswd)"),
            translator.get("Client Certificates"),
        ],
        style=custom_style
    ).ask()


def prompt_htpasswd_option(translator):
    """
    Prompt user to select how to handle .htpasswd file.
    
    Args:
        translator: The translator instance for localization
        
    Returns:
        str: The selected option text
    """
    return questionary.select(
        translator.get("How would you like to handle the .htpasswd file?"),
        choices=[
            translator.get("Generate .htpasswd file with the wizard"),
            translator.get("I'll provide my own .htpasswd file")
        ],
        style=custom_style
    ).ask()


def prompt_client_cert_source(translator):
    """
    Prompt user to select how to handle client certificates.
    
    Args:
        translator: The translator instance for localization
        
    Returns:
        str: The selected option text
    """
    return questionary.select(
        translator.get("How would you like to handle client certificates?"),
        choices=[
            translator.get("I'll provide my own certificates"),
            translator.get("Generate certificates for me")
        ],
        style=custom_style
    ).ask()


def prompt_client_cert_name(translator):
    """
    Prompt user to enter a name for the client certificate.
    
    Args:
        translator: The translator instance for localization
        
    Returns:
        str: The entered certificate name
    """
    return questionary.text(
        translator.get("Enter a name for the client certificate:"),
        default="TeddyCloudClient01",
        style=custom_style
    ).ask()


def prompt_modify_ip_restrictions(has_current_restrictions, translator):
    """
    Prompt user if they want to modify IP address restrictions.
    
    Args:
        has_current_restrictions: Whether there are existing restrictions
        translator: The translator instance for localization
        
    Returns:
        bool: True if confirmed, False otherwise
    """
    return questionary.confirm(
        translator.get("Would you like to modify IP address restrictions?"),
        default=has_current_restrictions,
        style=custom_style
    ).ask()


def display_domain_not_resolvable_warning(domain, translator):
    """
    Display warning that domain is not resolvable.
    
    Args:
        domain: The domain name
        translator: The translator instance for localization
    """
    console.print(Panel(
        f"[bold yellow]{translator.get('Domain Not Resolvable')}[/]\n\n"
        f"{translator.get('The domain')} '{domain}' {translator.get('could not be resolved using public DNS servers.')}\n"
        f"{translator.get('If using Let\'s Encrypt, make sure the domain is publicly resolvable.')}",
        box=box.ROUNDED,
        border_style="yellow"
    ))


def confirm_switch_to_self_signed(translator):
    """
    Ask user if they want to switch from Let's Encrypt to self-signed certificates.
    
    Args:
        translator: The translator instance for localization
        
    Returns:
        bool: True if confirmed, False otherwise
    """
    return questionary.confirm(
        translator.get("Would you like to switch from Let's Encrypt to self-signed certificates?"),
        default=True,
        style=custom_style
    ).ask()


def confirm_continue_anyway(translator):
    """
    Ask user if they want to continue despite port conflicts.
    
    Args:
        translator: The translator instance for localization
        
    Returns:
        bool: True if confirmed, False otherwise
    """
    return questionary.confirm(
        translator.get("Do you want to continue anyway?"),
        default=False,
        style=custom_style
    ).ask()


def display_waiting_for_htpasswd(htpasswd_file_path, translator):
    """
    Display message about waiting for .htpasswd file.
    
    Args:
        htpasswd_file_path: Path to the .htpasswd file
        translator: The translator instance for localization
    """
    console.print(f"[bold cyan]{translator.get('Waiting for .htpasswd file to be added...')}[/]")
    console.print(f"[cyan]{translator.get('Please add the file at')}: {htpasswd_file_path}[/]")


def confirm_change_security_method(translator):
    """
    Ask user if they want to return to the security selection menu.
    
    Args:
        translator: The translator instance for localization
        
    Returns:
        bool: True if confirmed, False otherwise
    """
    return questionary.confirm(
        translator.get("Do you want to return to the security selection menu?"),
        default=False,
        style=custom_style
    ).ask()


def select_https_mode_for_modification(current_mode, translator):
    """
    Prompt user to select HTTPS mode when modifying configuration.
    
    Args:
        current_mode: Current HTTPS mode
        translator: The translator instance for localization
        
    Returns:
        tuple: (selected option text, selected mode value)
    """
    # Define the choices
    choices = [
        translator.get("Let's Encrypt (automatic certificates)"),
        translator.get("Create self-signed certificates"),
        translator.get("Custom certificates (provide your own)")
    ]
    
    # Determine the default choice based on current mode
    default_choice = choices[0] if current_mode == "letsencrypt" else choices[1] if current_mode == "self_signed" else choices[2]
    
    https_mode = questionary.select(
        translator.get("How would you like to handle HTTPS?"),
        choices=choices,
        default=default_choice,
        style=custom_style
    ).ask()
    
    # Determine the new mode value based on selection
    new_mode = "letsencrypt"
    if https_mode.startswith(translator.get("Create self-signed")):
        new_mode = "self_signed"
    elif https_mode.startswith(translator.get("Custom")):
        new_mode = "user_provided"
    
    return https_mode, new_mode


def select_security_type_for_modification(current_security_type, translator):
    """
    Prompt user to select security type when modifying configuration.
    
    Args:
        current_security_type: Current security type
        translator: The translator instance for localization
        
    Returns:
        tuple: (selected option text, new security type value)
    """
    # Set up security options
    security_options = [
        translator.get("No additional security"),
        translator.get("Basic Authentication (.htpasswd)"),
        translator.get("Client Certificates"),
    ]
    
    # Determine default selection based on current setting
    default_idx = 0
    if current_security_type == "basic_auth":
        default_idx = 1
    elif current_security_type == "client_cert":
        default_idx = 2
    
    security_type = questionary.select(
        translator.get("How would you like to secure your TeddyCloud instance?"),
        choices=security_options,
        default=security_options[default_idx],
        style=custom_style
    ).ask()
    
    # Determine new security type value based on selection
    new_security_type = "none"
    if security_type.startswith(translator.get("Basic")):
        new_security_type = "basic_auth"
    elif security_type.startswith(translator.get("Client")):
        new_security_type = "client_cert"
    
    return security_type, new_security_type


def prompt_for_fallback_option(translator):
    """
    Ask user what they want to do if self-signed certificate generation fails.
    
    Args:
        translator: The translator instance for localization
        
    Returns:
        str: The selected option text
    """
    return questionary.select(
        translator.get("What would you like to do?"),
        choices=[
            translator.get("Try generating the self-signed certificate again"),
            translator.get("Switch to custom certificate mode (provide your own certificates)"),
        ],
        style=custom_style
    ).ask()