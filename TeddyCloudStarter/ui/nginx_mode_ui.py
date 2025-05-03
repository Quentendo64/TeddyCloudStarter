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
        str: The selected security type identifier ('none', 'basic_auth', or 'client_cert')
    """
    choices = [
        {'id': 'none', 'text': translator.get("No additional security")},
        {'id': 'basic_auth', 'text': translator.get("Basic Authentication (.htpasswd)")},
        {'id': 'client_cert', 'text': translator.get("Client Certificates")},
    ]
    
    choice_texts = [choice['text'] for choice in choices]
    selected_text = questionary.select(
        translator.get("How would you like to secure your TeddyCloud instance?"),
        choices=choice_texts,
        style=custom_style
    ).ask()
    
    for choice in choices:
        if choice['text'] == selected_text:
            return choice['id']
    
    return 'none'


def prompt_htpasswd_option(translator):
    """
    Prompt user to select how to handle .htpasswd file.
    
    Args:
        translator: The translator instance for localization
        
    Returns:
        str: The selected option identifier ('generate' or 'provide')
    """
    choices = [
        {'id': 'generate', 'text': translator.get("Generate .htpasswd file with the wizard")},
        {'id': 'provide', 'text': translator.get("I'll provide my own .htpasswd file")}
    ]
    
    choice_texts = [choice['text'] for choice in choices]
    selected_text = questionary.select(
        translator.get("How would you like to handle the .htpasswd file?"),
        choices=choice_texts,
        style=custom_style
    ).ask()
    
    for choice in choices:
        if choice['text'] == selected_text:
            return choice['id']
    
    return 'generate'


def prompt_client_cert_source(translator):
    """
    Prompt user to select how to handle client certificates.
    
    Args:
        translator: The translator instance for localization
        
    Returns:
        str: The selected option identifier ('generate' or 'provide')
    """
    choices = [
        {'id': 'generate', 'text': translator.get("Generate certificates for me")},
        {'id': 'provide', 'text': translator.get("I'll provide my own certificates")}
    ]
    
    choice_texts = [choice['text'] for choice in choices]
    selected_text = questionary.select(
        translator.get("How would you like to handle client certificates?"),
        choices=choice_texts,
        style=custom_style
    ).ask()
    
    for choice in choices:
        if choice['text'] == selected_text:
            return choice['id']
    
    return 'generate'


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
        current_mode: Current HTTPS mode identifier
        translator: The translator instance for localization
        
    Returns:
        str: The selected HTTPS mode identifier ('letsencrypt', 'self_signed', or 'user_provided')
    """
    choices = [
        {'id': 'letsencrypt', 'text': translator.get("Let's Encrypt (automatic certificates)")},
        {'id': 'self_signed', 'text': translator.get("Create self-signed certificates")},
        {'id': 'user_provided', 'text': translator.get("Custom certificates (provide your own)")}
    ]
    
    default_id = current_mode
    default_text = next((choice['text'] for choice in choices if choice['id'] == default_id), choices[0]['text'])
    
    choice_texts = [choice['text'] for choice in choices]
    selected_text = questionary.select(
        translator.get("How would you like to handle HTTPS?"),
        choices=choice_texts,
        default=default_text,
        style=custom_style
    ).ask()
    
    for choice in choices:
        if choice['text'] == selected_text:
            return choice['id']
    
    return 'letsencrypt'


def select_security_type_for_modification(current_security_type, translator):
    """
    Prompt user to select security type when modifying configuration.
    
    Args:
        current_security_type: Current security type identifier
        translator: The translator instance for localization
        
    Returns:
        str: The selected security type identifier ('none', 'basic_auth', or 'client_cert')
    """
    choices = [
        {'id': 'none', 'text': translator.get("No additional security")},
        {'id': 'basic_auth', 'text': translator.get("Basic Authentication (.htpasswd)")},
        {'id': 'client_cert', 'text': translator.get("Client Certificates")},
    ]
    
    default_id = current_security_type
    default_text = next((choice['text'] for choice in choices if choice['id'] == default_id), choices[0]['text'])
    
    choice_texts = [choice['text'] for choice in choices]
    selected_text = questionary.select(
        translator.get("How would you like to secure your TeddyCloud instance?"),
        choices=choice_texts,
        default=default_text,
        style=custom_style
    ).ask()
    
    for choice in choices:
        if choice['text'] == selected_text:
            return choice['id']
    
    return 'none'


def prompt_for_fallback_option(translator):
    """
    Ask user what they want to do if self-signed certificate generation fails.
    
    Args:
        translator: The translator instance for localization
        
    Returns:
        str: The selected option identifier ('try_again' or 'switch_to_custom')
    """
    choices = [
        {'id': 'try_again', 'text': translator.get("Try generating the self-signed certificate again")},
        {'id': 'switch_to_custom', 'text': translator.get("Switch to custom certificate mode (provide your own certificates)")}
    ]
    
    choice_texts = [choice['text'] for choice in choices]
    selected_text = questionary.select(
        translator.get("What would you like to do?"),
        choices=choice_texts,
        style=custom_style
    ).ask()
    
    for choice in choices:
        if choice['text'] == selected_text:
            return choice['id']
    
    return 'try_again'


def prompt_for_domain(current_domain, translator):
    """Prompt for a domain name.
    
    Args:
        current_domain: The current domain name (if any)
        translator: The translator instance for localization
        
    Returns:
        str: The selected domain name
    """
    if current_domain:
        domain_message = translator.get("Enter your domain name (or leave as-is)")
        default_domain = current_domain
    else:
        domain_message = translator.get("Enter your domain name")
        default_domain = ""
        
    return questionary.text(
        domain_message,
        default=default_domain,
        style=custom_style
    ).ask()

def prompt_for_https_mode(https_choices, default_choice_value, translator):
    """Prompt for HTTPS mode.
    
    Args:
        https_choices: List of available HTTPS mode choices
        default_choice_value: The default HTTPS mode value string
        translator: The translator instance for localization
        
    Returns:
        str: The selected HTTPS mode value string
    """
    # Create a standardized format of choices that questionary expects
    formatted_choices = []
    
    for choice in https_choices:
        # Handle id/text format (old format)
        if isinstance(choice, dict) and 'id' in choice and 'text' in choice:
            formatted_choices.append({
                "value": choice['id'],
                "name": choice['text']
            })
                
    # Extract valid values for validation
    valid_values = [choice["value"] for choice in formatted_choices]
    
    # Find the actual choice dictionary corresponding to the default value
    default_choice_obj = None
    if default_choice_value in valid_values:
        default_choice_obj = next((choice for choice in formatted_choices if choice["value"] == default_choice_value), None)
    
    # If the provided default value isn't valid or not found, fall back to the first choice object
    if not default_choice_obj:
        if formatted_choices:
            default_choice_obj = formatted_choices[0]
        else:
            # Fallback option if no choices are available (should never happen)
            console.print(f"[bold red]{translator.get('Error: No HTTPS choices available.')}[/]")
            return None
    
    # Create the questionary selection, passing the choice object as default
    selected_value = questionary.select(
        translator.get("Select HTTPS mode:"),
        choices=formatted_choices,
        default=default_choice_obj, # Pass the dictionary object
        style=custom_style
    ).ask() # ask() returns the 'value' of the selected choice
    
    return selected_value # Return the selected value string
def display_self_signed_certificate_info(domain, translator):
    """Display information about self-signed certificates.
    
    Args:
        domain: The domain name for the certificate
        translator: The translator instance for localization
    """
    console.print(f"[bold cyan]{translator.get('Generating self-signed certificates for')} {domain}...[/]")
    console.print(f"[yellow]{translator.get('Note: Self-signed certificates will cause browser warnings. They are recommended only for testing.')}[/]")

def prompt_security_type(translator):
    """Prompt for security type.
    
    Args:
        translator: The translator instance for localization
        
    Returns:
        str: The selected security type
    """
    return questionary.select(
        translator.get("Select security method for admin access:"),
        choices=[
            {"value": 'none', "name": translator.get("No additional security")},
            {"value": 'basic_auth', "name": translator.get("Username/password (HTTP Basic Auth)")},
            {"value": 'client_cert', "name": translator.get("Client certificates")}
        ],
        style=custom_style
    ).ask()

def prompt_htpasswd_option(translator):
    """Prompt for .htpasswd file options.
    
    Args:
        translator: The translator instance for localization
        
    Returns:
        str: The selected .htpasswd option
    """
    return questionary.select(
        translator.get("How would you like to create the .htpasswd file?"),
        choices=[
            {"value": 'generate', "name": translator.get("Generate now (interactive)")},
            {"value": 'manual', "name": translator.get("I'll create it myself")}
        ],
        style=custom_style
    ).ask()

def prompt_client_cert_source(translator):
    """Prompt for client certificate source.
    
    Args:
        translator: The translator instance for localization
        
    Returns:
        str: The selected client certificate source
    """
    return questionary.select(
        translator.get("How would you like to manage client certificates?"),
        choices=[
            {"value": 'generate', "name": translator.get("Generate new client certificate")},
            {"value": 'skip', "name": translator.get("Skip for now (generate later)")}
        ],
        style=custom_style
    ).ask()

def prompt_client_cert_name(translator):
    """Prompt for client certificate name.
    
    Args:
        translator: The translator instance for localization
        
    Returns:
        str: The entered client name
    """
    return questionary.text(
        translator.get("Enter a name for the client certificate (e.g., 'admin', 'my-device'):"),
        style=custom_style
    ).ask()

def prompt_modify_ip_restrictions(translator):
    """Prompt for IP restriction modification options.
    
    Args:
        translator: The translator instance for localization
        
    Returns:
        str: The selected IP restriction action
    """
    return questionary.select(
        translator.get("IP restriction options:"),
        choices=[
            {"value": 'add', "name": translator.get("Add IP address")},
            {"value": 'remove', "name": translator.get("Remove IP address")},
            {"value": 'clear', "name": translator.get("Clear all IP restrictions")},
            {"value": 'back', "name": translator.get("Back")}
        ],
        style=custom_style
    ).ask()

def confirm_continue_anyway(translator):
    """Confirm if user wants to continue despite port issues.
    
    Args:
        translator: The translator instance for localization
        
    Returns:
        bool: True if user wants to continue, False otherwise
    """
    return questionary.confirm(
        translator.get("Would you like to proceed anyway?"),
        default=False,
        style=custom_style
    ).ask()

def display_waiting_for_htpasswd(htpasswd_path, translator):
    """Display .htpasswd waiting message.
    
    Args:
        htpasswd_path: Path where .htpasswd file is expected
        translator: The translator instance for localization
    """
    console.print(f"[bold cyan]{translator.get('Waiting for .htpasswd file at')} {htpasswd_path}[/]")
    console.print(f"[yellow]{translator.get('Press Ctrl+C to cancel at any time')}[/]")

def confirm_change_security_method(translator):
    """Confirm if user wants to change the security method.
    
    Args:
        translator: The translator instance for localization
        
    Returns:
        bool: True if user wants to change, False otherwise
    """
    return questionary.confirm(
        translator.get("Would you like to choose a different security method?"),
        default=False,
        style=custom_style
    ).ask()

def select_https_mode_for_modification(current_mode, translator):
    """Prompt for selecting a new HTTPS mode.
    
    Args:
        current_mode: The current HTTPS mode
        translator: The translator instance for localization
        
    Returns:
        tuple: (selected display text, selected mode value)
    """
    choices = [
        {
            "value": "letsencrypt", 
            "name": translator.get("Let's Encrypt (automatic certificates)")
        },
        {
            "value": "self_signed", 
            "name": translator.get("Self-signed certificates")
        },
        {
            "value": "user_provided", 
            "name": translator.get("Custom certificates (provide your own)")
        },
        {
            "value": "none", 
            "name": translator.get("No HTTPS (not recommended)")
        }
    ]
    
    # Find the default choice based on current_mode
    default_choice = next((c for c in choices if c["value"] == current_mode), choices[0])
    
    selected = questionary.select(
        translator.get("Select new HTTPS mode:"),
        choices=choices,
        default=default_choice["value"],
        style=custom_style
    ).ask()
    
    # Return both display text and value
    selected_choice = next(c for c in choices if c["value"] == selected)
    return selected_choice["name"], selected

def select_security_type_for_modification(current_type, translator):
    """Prompt for selecting a new security type.
    
    Args:
        current_type: The current security type
        translator: The translator instance for localization
        
    Returns:
        str: The selected security type
    """
    choices = [
        {
            "value": "none", 
            "name": translator.get("No additional security")
        },
        {
            "value": "basic_auth", 
            "name": translator.get("Username/password (HTTP Basic Auth)")
        },
        {
            "value": "client_cert", 
            "name": translator.get("Client certificates")
        },
        {
            "value": "ip_restriction", 
            "name": translator.get("IP address restrictions only")
        }
    ]
    
    # Find the default choice based on current_type
    default_choice = next((c for c in choices if c["value"] == current_type), choices[0])
    
    selected = questionary.select(
        translator.get("Select new security type:"),
        choices=choices,
        default=default_choice["value"],
        style=custom_style
    ).ask()
    
    return selected

def prompt_for_fallback_option(translator):
    """Prompt for fallback option when certificate generation fails.
    
    Args:
        translator: The translator instance for localization
        
    Returns:
        str: The selected fallback option
    """
    return questionary.select(
        translator.get("Would you like to retry self-signed certificate generation or switch to custom certificates?"),
        choices=[
            {"value": 'try_again', "name": translator.get("Try self-signed certificate again")},
            {"value": 'custom', "name": translator.get("Switch to custom certificates mode")}
        ],
        style=custom_style
    ).ask()