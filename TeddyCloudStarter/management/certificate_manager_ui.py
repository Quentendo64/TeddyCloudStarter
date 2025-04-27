#!/usr/bin/env python3
"""
Certificate management UI for TeddyCloudStarter.
"""
import re
import questionary
from ..wizard.ui_helpers import console, custom_style

def show_certificate_management_menu(config, translator, cert_manager):
    """
    Show certificate management submenu.
    
    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        cert_manager: The certificate manager instance
        
    Returns:
        bool: True if user chose to exit, False otherwise
    """
    choices = []
    
    # Add appropriate options based on configuration
    if config["mode"] == "nginx":
        if config["nginx"]["https_mode"] == "letsencrypt":
            choices.append(translator.get("Test domain for Let's Encrypt"))
            choices.append(translator.get("Force refresh Let's Encrypt certificates"))
        
        if config["nginx"]["security"]["type"] == "client_cert":
            choices.append(translator.get("Create additional client certificate"))
            choices.append(translator.get("Invalidate client certificate"))
    
    # Add back option
    choices.append(translator.get("Back to main menu"))
    
    action = questionary.select(
        translator.get("Certificate Management"),
        choices=choices,
        style=custom_style
    ).ask()
    
    if action == translator.get("Create additional client certificate"):
        create_client_certificate(translator, cert_manager)
        return False  # Continue showing menu
        
    elif action == translator.get("Invalidate client certificate"):
        cert_manager.revoke_client_certificate()
        return False  # Continue showing menu
        
    elif action == translator.get("Force refresh Let's Encrypt certificates"):
        refresh_letsencrypt_certificates(config, translator, cert_manager)
        return False  # Continue showing menu
        
    elif action == translator.get("Test domain for Let's Encrypt"):
        test_domain_for_letsencrypt(config, translator, cert_manager)
        return False  # Continue showing menu
        
    # Back to main menu
    return True

def create_client_certificate(translator, cert_manager):
    """
    Create a new client certificate.
    
    Args:
        translator: The translator instance for localization
        cert_manager: The certificate manager instance
    """
    client_name = questionary.text(
        translator.get("Enter a name for the client certificate:"),
        default="TeddyCloudClient",
        validate=lambda text: bool(text.strip()),
        style=custom_style
    ).ask()
    
    cert_manager.generate_client_certificate(client_name)
    console.print(f"[bold green]{translator.get('Client certificate created for')} {client_name}[/]")

def refresh_letsencrypt_certificates(config, translator, cert_manager):
    """
    Refresh Let's Encrypt certificates.
    
    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        cert_manager: The certificate manager instance
    """
    domain = config["nginx"]["domain"]
    
    # Ask for email
    use_email = questionary.confirm(
        translator.get("Would you like to receive email notifications about certificate expiry?"),
        default=True,
        style=custom_style
    ).ask()
    
    email = None
    if use_email:
        email = questionary.text(
            translator.get("Enter your email address:"),
            validate=lambda x: re.match(r"[^@]+@[^@]+\.[^@]+", x),
            style=custom_style
        ).ask()
    
    cert_manager.force_refresh_letsencrypt_certificates(domain, email)
    console.print(f"[bold green]{translator.get('Let\'s Encrypt certificates refreshed for')} {domain}[/]")

def test_domain_for_letsencrypt(config, translator, cert_manager):
    """
    Test domain for Let's Encrypt.
    
    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        cert_manager: The certificate manager instance
    """
    domain = config["nginx"]["domain"]
    console.print(f"[bold yellow]{translator.get('Testing domain')} {domain} {translator.get('for Let\'s Encrypt...')}[/]")
    result = cert_manager.test_domain_for_letsencrypt(domain)
    if result:
        console.print(f"[bold green]{translator.get('Domain')} {domain} {translator.get('is valid for Let\'s Encrypt')}[/]")
    else:
        console.print(f"[bold red]{translator.get('Domain')} {domain} {translator.get('is not valid for Let\'s Encrypt')}[/]")