#!/usr/bin/env python3
"""
Certificate management UI for TeddyCloudStarter.
"""
import re
import questionary
from ..wizard.ui_helpers import console, custom_style

def show_certificate_management_menu(config, translator, security_managers):
    """
    Show certificate management submenu.
    
    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        security_managers: Dictionary containing security manager instances
        
    Returns:
        bool: True if user chose to exit, False otherwise
    """
    choices = []
    
    # Add appropriate options based on configuration
    if config["mode"] == "nginx":
        if config["nginx"]["https_mode"] == "letsencrypt":
            choices.append(translator.get("Let's Encrypt Certificate Management"))
            choices.append(translator.get("Test domain for Let's Encrypt"))
        
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
        create_client_certificate(translator, security_managers["client_cert_manager"])
        return False  # Continue showing menu
        
    elif action == translator.get("Invalidate client certificate"):
        invalidate_client_certificate(config, translator, security_managers["client_cert_manager"])
        return False  # Continue showing menu
        
    elif action == translator.get("Let's Encrypt Certificate Management"):
        show_letsencrypt_management_menu(config, translator, security_managers["lets_encrypt_manager"])
        return False  # Continue showing menu
        
    elif action == translator.get("Test domain for Let's Encrypt"):
        test_domain_for_letsencrypt(config, translator, security_managers["lets_encrypt_manager"])
        return False  # Continue showing menu
        
    # Back to main menu
    return True

def create_client_certificate(translator, client_cert_manager):
    """
    Create a new client certificate.
    
    Args:
        translator: The translator instance for localization
        client_cert_manager: The client certificate manager instance
    """
    client_name = questionary.text(
        translator.get("Enter a name for the client certificate:"),
        default="TeddyCloudClient",
        validate=lambda text: bool(text.strip()),
        style=custom_style
    ).ask()
    
    # Ask for password for PKCS#12 file
    use_custom_password = questionary.confirm(
        translator.get("Would you like to set a custom password for the certificate bundle (.p12 file)?"),
        default=False,
        style=custom_style
    ).ask()
    
    passout = None
    if use_custom_password:
        passout = questionary.password(
            translator.get("Enter password for the PKCS#12 certificate bundle:"),
            validate=lambda text: len(text.strip()) >= 4 or text.strip() == "",
            style=custom_style
        ).ask()
        
        # If empty password was entered, remind user about the default
        if not passout.strip():
            console.print(f"[bold yellow]{translator.get('Empty password provided, using default password \"teddycloud\"')}[/]")
            passout = None
    
    success, _ = client_cert_manager.generate_client_certificate(client_name, passout=passout)
    if success:
        console.print(f"[bold green]{translator.get('Client certificate created for')} {client_name}[/]")
    else:
        console.print(f"[bold red]{translator.get('Failed to create client certificate for')} {client_name}[/]")

def invalidate_client_certificate(config, translator, client_cert_manager):
    """
    Revoke a client certificate.
    
    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        client_cert_manager: The client certificate manager instance
    """
    # Create a fresh instance of ConfigManager to get the latest certificate data
    from ..config_manager import ConfigManager
    config_manager = ConfigManager()
    
    # Use the fresh config for certificate data
    fresh_config = config_manager.config
    
    # Check if there are client certificates in the config
    if ("security" not in fresh_config or 
        "client_certificates" not in fresh_config["security"] or 
        not fresh_config["security"]["client_certificates"]):
        console.print(f"[bold red]{translator.get('No client certificates found in configuration.')}[/]")
        return
        
    # Get non-revoked certificates
    active_certs = [cert for cert in fresh_config["security"]["client_certificates"] 
                   if not cert.get("revoked", False)]
    
    if not active_certs:
        console.print(f"[bold yellow]{translator.get('All client certificates are already revoked.')}[/]")
        return
    
    # Create a list of choices for certificates
    cert_choices = []
    
    for cert in active_certs:
        client_name = cert.get("client_name", "Unknown")
        serial = cert.get("serial", "Unknown")
        valid_till = cert.get("valid_till", "Unknown")
        
        # Format as: "ClientName (Serial: 123..., Valid till: 2035-04-25)"
        display_text = f"{client_name} (Serial: ...{serial[-8:]}, {translator.get('Valid till')}: {valid_till})"
        cert_choices.append({
            "name": display_text,
            "value": serial
        })
    
    # Add cancel option
    cert_choices.append({
        "name": translator.get("Cancel"),
        "value": "cancel"
    })
    
    # Ask user to select a certificate
    selected_cert = questionary.select(
        translator.get("Select certificate to invalidate:"),
        choices=cert_choices,
        style=custom_style
    ).ask()
    
    if selected_cert == "cancel":
        console.print(f"[bold yellow]{translator.get('Certificate invalidation canceled.')}[/]")
        return
    
    # Confirm revocation
    confirm = questionary.confirm(
        translator.get("Are you sure you want to invalidate this certificate?"),
        default=False,
        style=custom_style
    ).ask()
    
    if not confirm:
        console.print(f"[bold yellow]{translator.get('Certificate invalidation canceled.')}[/]")
        return
    
    # Always use full revocation (no prompt)
    console.print(f"[bold cyan]{translator.get('Fully revoking certificate...')}[/]")
    
    # Use client_cert_manager for revocation
    success, _ = client_cert_manager.revoke_client_certificate(cert_name=selected_cert)
    
    if success:
        # Update certificate status in config
        config_manager.invalidate_client_certificate(selected_cert)
        
        console.print(f"[bold green]{translator.get('Certificate successfully invalidated.')}[/]")
        
        # Check if we are in nginx mode with client certificate authentication
        if (fresh_config.get("mode") == "nginx" and 
            fresh_config.get("nginx", {}).get("security", {}).get("type") == "client_cert"):
            
            # Regenerate nginx configuration to include the CRL file
            console.print(f"[bold cyan]{translator.get('Regenerating nginx configuration...')}[/]")
            
            # Import the generator module to regenerate the configuration
            from ..configuration.generator import generate_nginx_configs
            from ..configurations import TEMPLATES
            
            # Regenerate the nginx configuration
            if generate_nginx_configs(fresh_config, translator, TEMPLATES):
                console.print(f"[bold green]{translator.get('Nginx configuration regenerated successfully.')}[/]")
                
                # Ask if user wants to restart the nginx-auth service to apply changes
                restart_service = questionary.confirm(
                    translator.get("Would you like to restart the nginx-auth service to apply the changes?"),
                    default=True,
                    style=custom_style
                ).ask()
                
                if restart_service:
                    import subprocess
                    try:
                        console.print(f"[bold cyan]{translator.get('Restarting nginx-auth service...')}[/]")
                        result = subprocess.run(["docker", "restart", "nginx-auth"], 
                                              check=True, capture_output=True)
                        console.print(f"[bold green]{translator.get('nginx-auth service restarted successfully.')}[/]")
                    except subprocess.CalledProcessError as e:
                        console.print(f"[bold red]{translator.get('Failed to restart nginx-auth service:')} {e}[/]")
            else:
                console.print(f"[bold red]{translator.get('Failed to regenerate nginx configuration.')}[/]")
    else:
        console.print(f"[bold red]{translator.get('Failed to invalidate certificate.')}[/]")

def show_letsencrypt_management_menu(config, translator, lets_encrypt_manager):
    """
    Show Let's Encrypt certificate management submenu.
    
    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        lets_encrypt_manager: The Let's Encrypt manager instance
        
    Returns:
        bool: True if user chose to exit, False otherwise
    """
    choices = [
        translator.get("Request production certificate (webroot mode)"),
        translator.get("Request production certificate (standalone mode)"),
        translator.get("Request staging certificate (webroot mode)"),
        translator.get("Request staging certificate (standalone mode)"),
        translator.get("Force refresh Let's Encrypt certificates"),
        translator.get("Back to certificate menu")
    ]
    
    action = questionary.select(
        translator.get("Let's Encrypt Certificate Management"),
        choices=choices,
        style=custom_style
    ).ask()
    
    if action == translator.get("Request production certificate (webroot mode)"):
        request_letsencrypt_certificate(config, translator, lets_encrypt_manager, staging=False, mode="webroot")
        return False
        
    elif action == translator.get("Request production certificate (standalone mode)"):
        request_letsencrypt_certificate(config, translator, lets_encrypt_manager, staging=False, mode="standalone")
        return False
        
    elif action == translator.get("Request staging certificate (webroot mode)"):
        request_letsencrypt_certificate(config, translator, lets_encrypt_manager, staging=True, mode="webroot")
        return False
        
    elif action == translator.get("Request staging certificate (standalone mode)"):
        request_letsencrypt_certificate(config, translator, lets_encrypt_manager, staging=True, mode="standalone")
        return False
        
    elif action == translator.get("Force refresh Let's Encrypt certificates"):
        refresh_letsencrypt_certificates(config, translator, lets_encrypt_manager)
        return False
    
    # Back to certificate menu
    return True

def request_letsencrypt_certificate(config, translator, lets_encrypt_manager, staging=False, mode="webroot"):
    """
    Request Let's Encrypt certificate.
    
    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        lets_encrypt_manager: The Let's Encrypt manager instance
        staging: Whether to use staging environment
        mode: Authentication mode, "webroot" or "standalone"
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
    
    # Ask for additional domains (SANs)
    additional_domains = []
    add_sans = questionary.confirm(
        translator.get("Would you like to add additional domain names (SANs) to the certificate?"),
        default=False,
        style=custom_style
    ).ask()
    
    if add_sans:
        adding_domains = True
        while adding_domains:
            san = questionary.text(
                translator.get("Enter additional domain name (leave empty to finish):"),
                style=custom_style
            ).ask()
            
            if not san:
                adding_domains = False
            else:
                additional_domains.append(san)
                console.print(f"[green]{translator.get('Added domain:')} {san}[/]")
    
    # Show certificate request info
    staging_str = translator.get("staging") if staging else translator.get("production")
    mode_str = mode
    
    console.print(f"[bold cyan]{translator.get('Requesting')} {staging_str} {translator.get('certificate using')} {mode_str} {translator.get('mode')}...[/]")
    console.print(f"[cyan]{translator.get('Primary domain:')} {domain}[/]")
    
    if additional_domains:
        console.print(f"[cyan]{translator.get('Additional domains:')} {', '.join(additional_domains)}[/]")
    
    if email:
        console.print(f"[cyan]{translator.get('Email:')} {email}[/]")
    
    # Request the certificate using the new API
    result = lets_encrypt_manager.request_certificate(
        domain=domain,
        mode=mode,
        staging=staging,
        email=email,
        additional_domains=additional_domains
    )
    
    if result:
        cert_type = translator.get("Staging") if staging else translator.get("Production")
        success_msg = f"{cert_type} {translator.get('certificate requested successfully for')} {domain}"
        console.print(f"[bold green]{success_msg}[/]")
    else:
        cert_type = translator.get("staging") if staging else translator.get("production")
        error_msg = f"{translator.get('Failed to request')} {cert_type} {translator.get('certificate')}"
        console.print(f"[bold red]{error_msg}[/]")

def refresh_letsencrypt_certificates(config, translator, lets_encrypt_manager):
    """
    Refresh Let's Encrypt certificates.
    
    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        lets_encrypt_manager: The Let's Encrypt manager instance
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
    
    # Ask for additional domains (SANs)
    additional_domains = []
    add_sans = questionary.confirm(
        translator.get("Would you like to add additional domain names (SANs) to the certificate?"),
        default=False,
        style=custom_style
    ).ask()
    
    if add_sans:
        adding_domains = True
        while adding_domains:
            san = questionary.text(
                translator.get("Enter additional domain name (leave empty to finish):"),
                style=custom_style
            ).ask()
            
            if not san:
                adding_domains = False
            else:
                additional_domains.append(san)
                console.print(f"[green]{translator.get('Added domain:')} {san}[/]")
    
    result = lets_encrypt_manager.force_refresh_certificates(
        domain=domain, 
        email=email,
        additional_domains=additional_domains
    )
    
    if result:
        console.print(f"[bold green]{translator.get('Let\'s Encrypt certificates refreshed for')} {domain}[/]")
    else:
        console.print(f"[bold red]{translator.get('Failed to refresh Let\'s Encrypt certificates for')} {domain}[/]")

def test_domain_for_letsencrypt(config, translator, lets_encrypt_manager):
    """
    Test domain for Let's Encrypt.
    
    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        lets_encrypt_manager: The Let's Encrypt manager instance
    """
    domain = config["nginx"]["domain"]
    console.print(f"[bold yellow]{translator.get('Testing domain')} {domain} {translator.get('for Let\'s Encrypt...')}[/]")
    result = lets_encrypt_manager.test_domain(domain)
    if result:
        console.print(f"[bold green]{translator.get('Domain')} {domain} {translator.get('is valid for Let\'s Encrypt')}[/]")
    else:
        console.print(f"[bold red]{translator.get('Domain')} {domain} {translator.get('is not valid for Let\'s Encrypt')}[/]")