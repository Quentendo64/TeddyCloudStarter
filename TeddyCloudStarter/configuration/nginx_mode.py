#!/usr/bin/env python3
"""
Nginx mode configuration for TeddyCloudStarter.
"""
import questionary
import os
import subprocess
import getpass
import sys
import shutil
from rich.panel import Panel
from rich import box
from rich.prompt import Prompt
from rich.table import Table
from rich import print as rprint
from pathlib import Path
from ..wizard.ui_helpers import console, custom_style
from ..utilities.network import check_port_available, check_domain_resolvable
from ..utilities.validation import validate_domain_name, validate_ip_address, ConfigValidator

# Initialize the validator once at module level
_validator = ConfigValidator()

def configure_nginx_mode(config, translator, security_managers):
    """
    Configure nginx deployment mode settings.
    
    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        security_managers: Dictionary containing the security module managers
        
    Returns:
        dict: The updated configuration dictionary
    """
    # Import standard modules that might be needed during execution
    import time
    import subprocess
    import traceback
    from pathlib import Path
    
    # Extract security managers
    lets_encrypt_manager = security_managers.get("lets_encrypt_manager")
    ca_manager = security_managers.get("ca_manager")
    client_cert_manager = security_managers.get("client_cert_manager")
    basic_auth_manager = security_managers.get("basic_auth_manager")
    
    # Initialize nginx configuration if it doesn't exist
    if "nginx" not in config:
        config["nginx"] = {
            "domain": "",
            "https_mode": "letsencrypt",
            "security": {
                "type": "none",
                "allowed_ips": []
            }
        }
        
    nginx_config = config["nginx"]
    
    # Get the project path from config
    project_path = config.get("environment", {}).get("path", "")
    if not project_path:
        console.print(f"[bold red]{translator.get('Warning')}: {translator.get('Project path not set. Using current directory.')}[/]")
        project_path = os.getcwd()
    
    # Check if ports 80 and 443 are available
    port_80_available = check_port_available(80)
    port_443_available = check_port_available(443)
    
    if not port_80_available:
        console.print(f"[bold yellow]{translator.get('Warning')}: {translator.get('Port 80 appears to be in use. This is required for Nginx')}.[/]")
    
    if not port_443_available:
        console.print(f"[bold yellow]{translator.get('Warning')}: {translator.get('Port 443 appears to be in use. This is required for Nginx')}.[/]")
    
    if not port_80_available or not port_443_available:
        continue_anyway = questionary.confirm(
            translator.get("Do you want to continue anyway?"),
            default=False,
            style=custom_style
        ).ask()
        
        if not continue_anyway:
            return config
    
    # Ask for domain
    domain = questionary.text(
        translator.get("Enter the domain name for your TeddyCloud instance:"),
        validate=lambda d: validate_domain_name(d),
        style=custom_style
    ).ask()
    
    nginx_config["domain"] = domain
    
    # Main certificate selection loop
    while True:
        # Check if domain is publicly resolvable
        domain_resolvable = check_domain_resolvable(domain)
        
        # Define choices for HTTPS mode based on domain resolution
        https_choices = []
        if domain_resolvable:
            # If domain is resolvable, all options are available
            https_choices = [
                translator.get("Let's Encrypt (automatic certificates)"),
                translator.get("Create self-signed certificates"),
                translator.get("Custom certificates (provide your own)")
            ]
            default_choice = https_choices[0]
        else:
            # If domain is not resolvable, Let's Encrypt is not available
            https_choices = [
                translator.get("Create self-signed certificates"),
                translator.get("Custom certificates (provide your own)")
            ]
            default_choice = https_choices[0]
            # Also update config to use self-signed certificates
            nginx_config["https_mode"] = "self_signed"
            
            # Inform the user why Let's Encrypt option is not available
            console.print(Panel(
                f"[bold yellow]{translator.get('Let\'s Encrypt Not Available')}[/]\n\n"
                f"{translator.get('The domain')} '{domain}' {translator.get('could not be resolved using public DNS servers (Quad9)')}\n"
                f"{translator.get('Let\'s Encrypt requires a publicly resolvable domain to issue certificates.')}\n"
                f"{translator.get('You can use self-signed or custom certificates for your setup.')}",
                box=box.ROUNDED,
                border_style="yellow"
            ))
        
        # Ask about HTTPS
        https_mode = questionary.select(
            translator.get("How would you like to handle HTTPS?"),
            choices=https_choices,
            default=default_choice,
            style=custom_style
        ).ask()
        
        # Update HTTPS mode setting based on selection
        if domain_resolvable:  # Only update if all options were available
            if https_mode.startswith(translator.get("Let's")):
                nginx_config["https_mode"] = "letsencrypt"
            elif https_mode.startswith(translator.get("Create self-signed")):
                nginx_config["https_mode"] = "self_signed"
            else:
                nginx_config["https_mode"] = "custom"
        else:  # Domain not resolvable, only self-signed or custom options
            if https_mode.startswith(translator.get("Create self-signed")):
                nginx_config["https_mode"] = "self_signed"
            else:
                nginx_config["https_mode"] = "custom"
        
        if nginx_config["https_mode"] == "letsencrypt":
            # Warn about Let's Encrypt requirements
            console.print(Panel(
                f"[bold yellow]{translator.get('Let\'s Encrypt Requirements')}[/]\n\n"
                f"{translator.get('To use Let\'s Encrypt, you need:')}\n"
                f"1. {translator.get('A public domain name pointing to this server')}\n"
                f"2. {translator.get('Public internet access on ports 80 and 443')}\n"
                f"3. {translator.get('This server must be reachable from the internet')}",
                box=box.ROUNDED,
                border_style="yellow"
            ))
            
            confirm_letsencrypt = questionary.confirm(
                translator.get("Do you meet these requirements?"),
                default=True,
                style=custom_style
            ).ask()
            
            if confirm_letsencrypt:
                # Test if domain is properly set up
                test_cert = questionary.confirm(
                    translator.get("Would you like to test if Let's Encrypt can issue a certificate for your domain?"),
                    default=True,
                    style=custom_style
                ).ask()
                
                if test_cert:
                    lets_encrypt_manager.request_certificate(domain)
            else:
                # Switch to self-signed mode as fallback
                nginx_config["https_mode"] = "self_signed"
                console.print(f"[bold cyan]{translator.get('Switching to self-signed certificates mode')}...[/]")
                # Continue with self-signed certificate handling
        
        if nginx_config["https_mode"] == "self_signed":
            server_certs_path = os.path.join(project_path, "data", "server_certs")
            server_crt_path = os.path.join(server_certs_path, "server.crt")
            server_key_path = os.path.join(server_certs_path, "server.key")
            
            console.print(Panel(
                f"[bold cyan]{translator.get('Self-Signed Certificate Generation')}[/]\n\n"
                f"{translator.get('A self-signed certificate will be generated for')} '{domain}'.\n"
                f"{translator.get('This certificate will not be trusted by browsers, but is suitable for testing and development.')}",
                box=box.ROUNDED,
                border_style="cyan"
            ))
            
            # Check if OpenSSL is available
            try:
                subprocess.run(["openssl", "version"], check=True, capture_output=True, text=True)
            except (subprocess.SubprocessError, FileNotFoundError):
                console.print(f"[bold red]{translator.get('OpenSSL is not available. Cannot generate self-signed certificate.')}[/]")
                console.print(f"[bold yellow]{translator.get('Falling back to custom certificate mode.')}[/]")
                nginx_config["https_mode"] = "custom"
                continue
            
            # Generate self-signed certificate using the CertificateAuthority class
            success, message = ca_manager.generate_self_signed_certificate(server_certs_path, domain, translator)
            
            if not success:
                console.print(f"[bold red]{translator.get('Failed to generate self-signed certificate')}: {message}[/]")
                
                # Ask user if they want to try again, use custom certificates, or quit
                fallback_option = questionary.select(
                    translator.get("What would you like to do?"),
                    choices=[
                        translator.get("Try generating the self-signed certificate again"),
                        translator.get("Switch to custom certificate mode (provide your own certificates)"),
                    ],
                    style=custom_style
                ).ask()
                
                if fallback_option.startswith(translator.get("Try generating")):
                    # Stay in self-signed mode and try again in the next loop iteration
                    continue
                else:
                    # Switch to custom certificates mode
                    nginx_config["https_mode"] = "custom"
                    console.print(f"[bold cyan]{translator.get('Switching to custom certificates mode')}...[/]")
                    continue
            
        # Only break out of the main certificate selection loop when we've successfully configured certificates
        break
    
    # Configure security
    configure_security(nginx_config, translator, security_managers, project_path)
    
    return config

def configure_security(nginx_config, translator, security_managers, project_path):
    """
    Configure security settings for Nginx mode.
    
    Args:
        nginx_config: The nginx configuration dictionary
        translator: The translator instance for localization
        security_managers: Dictionary containing the security module managers
        project_path: The project path for file operations
    """
    # Extract security managers
    ca_manager = security_managers.get("ca_manager")
    client_cert_manager = security_managers.get("client_cert_manager")
    basic_auth_manager = security_managers.get("basic_auth_manager")
    ip_restrictions_manager = security_managers.get("ip_restrictions_manager")
    
    while True:
        security_type = questionary.select(
            translator.get("How would you like to secure your TeddyCloud instance?"),
            choices=[
                translator.get("No additional security"),
                translator.get("Basic Authentication (.htpasswd)"),
                translator.get("Client Certificates"),
            ],
            style=custom_style
        ).ask()
        
        if security_type.startswith(translator.get("No")):
            nginx_config["security"]["type"] = "none"
            break
        elif security_type.startswith(translator.get("Basic")):
            nginx_config["security"]["type"] = "basic_auth"
            
            # Ask if user wants to provide their own .htpasswd or generate one
            htpasswd_option = questionary.select(
                translator.get("How would you like to handle the .htpasswd file?"),
                choices=[
                    translator.get("Generate .htpasswd file with the wizard"),
                    translator.get("I'll provide my own .htpasswd file")                
                ],
                style=custom_style
            ).ask()
            
            # Use project path for data directory and htpasswd file
            data_path = os.path.join(project_path, "data")
            security_path = os.path.join(data_path, "security")
            htpasswd_file_path = os.path.join(security_path, ".htpasswd")
            
            # Create security directory if it doesn't exist
            Path(security_path).mkdir(parents=True, exist_ok=True)
            
            # Handle htpasswd creation choice
            if htpasswd_option == translator.get("Generate .htpasswd file with the wizard"):
                console.print(f"[bold cyan]{translator.get('Let\'s create a .htpasswd file with your users and passwords')}.[/]")
                
                # Use basic_auth_manager to generate htpasswd file
                if basic_auth_manager:
                    success = basic_auth_manager.generate_htpasswd_file(htpasswd_file_path)
                    if success:
                        console.print(f"[bold green]{translator.get('.htpasswd file successfully created at')} {htpasswd_file_path}[/]")
                    else:
                        console.print(f"[bold red]{translator.get('Failed to create .htpasswd file. You may need to create it manually.')}[/]")
                else:
                    console.print(f"[bold red]{translator.get('Error: Basic auth manager not available. Cannot generate .htpasswd file.')}[/]")
                    console.print(f"[yellow]{translator.get('Please create the .htpasswd file manually at')} {htpasswd_file_path}[/]")
            else:
                console.print(f"[bold cyan]{translator.get('Remember to place your .htpasswd file at')} {htpasswd_file_path}[/]")
            
            # Check if .htpasswd exists
            htpasswd_exists = Path(htpasswd_file_path).exists()
            
            if not htpasswd_exists:
                console.print(f"[bold yellow]{translator.get('.htpasswd file not found. You must add it to continue.')}[/]")
                
                # Flag to track if we need to return to security menu
                should_return_to_menu = False
                
                console.print(f"[bold cyan]{translator.get('Waiting for .htpasswd file to be added...')}[/]")
                console.print(f"[cyan]{translator.get('Please add the file at')}: {htpasswd_file_path}[/]")
                
                # Wait for the .htpasswd to appear - user cannot proceed without it
                import time
                
                while True:
                    # Sleep briefly to avoid high CPU usage and give time for file system operations
                    time.sleep(1)
                    
                    # Force refresh the directory
                    try:
                        # Check if .htpasswd exists now
                        htpasswd_exists = os.path.isfile(htpasswd_file_path)
                        
                        if htpasswd_exists:
                            console.print(f"[bold green]{translator.get('.htpasswd file found! Continuing...')}[/]")
                            break
                    except Exception as e:
                        console.print(f"[bold red]Error checking files: {str(e)}[/]")
                    
                    console.print(f"[yellow]{translator.get('Still waiting for .htpasswd file at')}: {htpasswd_file_path}[/]")
                    
                    # Ask if user wants to change security method instead of adding .htpasswd
                    change_security_method = questionary.confirm(
                        translator.get("Do you want to return to the security selection menu?"),
                        default=False,
                        style=custom_style
                    ).ask()
                    
                    if change_security_method:
                        # Set flag to return to security selection menu
                        should_return_to_menu = True
                        console.print(f"[bold cyan]{translator.get('Returning to security selection menu...')}[/]")
                        break  # Break out of the waiting loop
                
                # If we need to return to security menu, skip the break and continue the outer loop
                if should_return_to_menu:
                    continue  # Continue the outer while loop to show the security menu again
            else:
                console.print(f"[bold green]{translator.get('.htpasswd file found and ready to use.')}[/]")
            
            break  # Break out of the outer while loop once configuration is complete
            
        else:  # Client Certificates
            nginx_config["security"]["type"] = "client_cert"
            
            cert_source = questionary.select(
                translator.get("How would you like to handle client certificates?"),
                choices=[
                    translator.get("I'll provide my own certificates"),
                    translator.get("Generate certificates for me")
                ],
                style=custom_style
            ).ask()
            
            if cert_source.startswith(translator.get("Generate")):
                client_name = questionary.text(
                    translator.get("Enter a name for the client certificate:"),
                    default="TeddyCloudClient01",
                    style=custom_style
                ).ask()
                
                # Generate certificate with the client_cert_manager and store the result
                success, cert_info = client_cert_manager.generate_client_certificate(client_name)
                
                if success and cert_info:
                    console.print(f"[bold green]{translator.get('Client certificate successfully created and saved to config.')}[/]")
                else:
                    console.print(f"[bold red]{translator.get('Failed to create client certificate. Please try again.')}[/]")
            
            break  # Break out of the outer while loop once configuration is complete
    
    # Ask about IP restrictions
    if ip_restrictions_manager:
        ip_restrictions_manager.configure_ip_restrictions(nginx_config)
    else:
        console.print(f"[bold yellow]{translator.get('Warning')}: {translator.get('IP restrictions manager not available')}[/]")
    
    return nginx_config

def modify_https_mode(config, translator, security_managers):
    """
    Modify HTTPS mode for nginx mode.
    
    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        security_managers: Dictionary containing the security module managers
    """
    # Import standard modules that might be needed during execution
    import time
    import subprocess
    import traceback
    from pathlib import Path
    
    # Extract security managers
    lets_encrypt_manager = security_managers.get("lets_encrypt_manager")
    ca_manager = security_managers.get("ca_manager")  # Add certificate authority manager
    
    nginx_config = config["nginx"]
    current_mode = nginx_config["https_mode"]
    
    # Get the project path from config
    project_path = config.get("environment", {}).get("path", "")
    if not project_path:
        console.print(f"[bold red]{translator.get('Warning')}: {translator.get('Project path not set. Using current directory.')}[/]")
        project_path = os.getcwd()
    
    # Main certificate selection loop
    while True:
        console.print(f"[bold cyan]{translator.get('Current HTTPS mode')}: {current_mode}[/]")
        
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
        
        new_mode = "letsencrypt" if https_mode.startswith(translator.get("Let's")) else "self_signed" if https_mode.startswith(translator.get("Create self-signed")) else "user_provided"
        
        if new_mode != current_mode:
            nginx_config["https_mode"] = new_mode
            console.print(f"[bold green]{translator.get('HTTPS mode updated to')} {new_mode}[/]")
            
            if new_mode == "letsencrypt":
                # Warn about Let's Encrypt requirements
                console.print(Panel(
                    f"[bold yellow]{translator.get('Let\'s Encrypt Requirements')}[/]\n\n"
                    f"{translator.get('To use Let\'s Encrypt, you need:')}\n"
                    f"1. {translator.get('A public domain name pointing to this server')}\n"
                    f"2. {translator.get('Public internet access on ports 80 and 443')}\n"
                    f"3. {translator.get('This server must be reachable from the internet')}",
                    box=box.ROUNDED,
                    border_style="yellow"
                ))
                
                confirm_letsencrypt = questionary.confirm(
                    translator.get("Do you meet these requirements?"),
                    default=True,
                    style=custom_style
                ).ask()
                
                if confirm_letsencrypt:
                    # Test if domain is properly set up
                    test_cert = questionary.confirm(
                        translator.get("Would you like to test if Let's Encrypt can issue a certificate for your domain?"),
                        default=True,
                        style=custom_style
                    ).ask()
                    
                    if test_cert:
                        lets_encrypt_manager.request_certificate(nginx_config["domain"])
                else:
                    # Switch back to self-signed mode
                    nginx_config["https_mode"] = "self_signed"
                    console.print(f"[bold cyan]{translator.get('Switching to self-signed certificates mode')}...[/]")
                    # Continue to self-signed certificate handling in the next iteration
                    current_mode = "self_signed"
                    continue
            
            # Generate self-signed certificates immediately when that option is selected
            elif new_mode == "self_signed":
                domain = nginx_config.get("domain", "")
                if not domain:
                    console.print(f"[bold yellow]{translator.get('Warning')}: {translator.get('No domain set. Using example.com as fallback.')}[/]")
                    domain = "example.com"
                    nginx_config["domain"] = domain
                
                server_certs_path = os.path.join(project_path, "data", "server_certs")
                server_crt_path = os.path.join(server_certs_path, "server.crt")
                server_key_path = os.path.join(server_certs_path, "server.key")
                
                console.print(Panel(
                    f"[bold cyan]{translator.get('Self-Signed Certificate Generation')}[/]\n\n"
                    f"{translator.get('A self-signed certificate will be generated for')} '{domain}'.\n"
                    f"{translator.get('This certificate will not be trusted by browsers, but is suitable for testing and development.')}",
                    box=box.ROUNDED,
                    border_style="cyan"
                ))
                
                # Check if OpenSSL is available
                try:
                    subprocess.run(["openssl", "version"], check=True, capture_output=True, text=True)
                except (subprocess.SubprocessError, FileNotFoundError):
                    console.print(f"[bold red]{translator.get('OpenSSL is not available. Cannot generate self-signed certificate.')}[/]")
                    console.print(f"[bold yellow]{translator.get('Proceeding with self-signed mode, but you will need to provide certificates manually.')}[/]")
                    continue
                
                # Generate self-signed certificate using the CertificateAuthority class
                if ca_manager:
                    success, message = ca_manager.generate_self_signed_certificate(server_certs_path, domain, translator)
                    
                    if success:
                        console.print(f"[bold green]{translator.get('Self-signed certificate successfully generated for')} {domain}[/]")
                    else:
                        console.print(f"[bold red]{translator.get('Failed to generate self-signed certificate')}: {message}[/]")
                        console.print(f"[yellow]{translator.get('You will need to manually provide certificates in')} {server_certs_path}[/]")
                else:
                    console.print(f"[bold red]{translator.get('Certificate Authority manager not available. Cannot generate certificates.')}[/]")
        
        # Break out of the main loop when configuration is complete
        break
    
    return config

def modify_security_settings(config, translator, security_managers):
    """
    Modify security settings for nginx mode.
    
    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        security_managers: Dictionary containing the security module managers
    """
    # Extract security managers
    client_cert_manager = security_managers.get("client_cert_manager")
    basic_auth_manager = security_managers.get("basic_auth_manager")
    
    nginx_config = config["nginx"]
    current_security_type = nginx_config["security"]["type"]
    current_ip_restrictions = nginx_config["security"]["allowed_ips"]
    
    # Get the project path from config
    project_path = config.get("environment", {}).get("path", "")
    if not project_path:
        console.print(f"[bold red]{translator.get('Warning')}: {translator.get('Project path not set. Using current directory.')}[/]")
        project_path = os.getcwd()
    
    console.print(f"[bold cyan]{translator.get('Current security type')}: {current_security_type}[/]")
    if current_ip_restrictions:
        console.print(f"[bold cyan]{translator.get('Current allowed IPs')}: {', '.join(current_ip_restrictions)}[/]")
    
    # First, choose security type
    security_options = [
        translator.get("No additional security"),
        translator.get("Basic Authentication (.htpasswd)"),
        translator.get("Client Certificates"),
    ]
    
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
    
    if security_type.startswith(translator.get("No")):
        new_security_type = "none"
    elif security_type.startswith(translator.get("Basic")):
        new_security_type = "basic_auth"
    else:  # Client Certificates
        new_security_type = "client_cert"
    
    # If security type changed, handle the new settings
    if new_security_type != current_security_type:
        nginx_config["security"]["type"] = new_security_type
        console.print(f"[bold green]{translator.get('Security type updated to')} {new_security_type}[/]")
        
        if new_security_type == "basic_auth":
            # Basic auth handling
            htpasswd_option = questionary.select(
                translator.get("How would you like to handle the .htpasswd file?"),
                choices=[
                    translator.get("I'll provide my own .htpasswd file"),
                    translator.get("Generate .htpasswd file with the wizard")
                ],
                style=custom_style
            ).ask()
            
            # Use project path for data directory and htpasswd file
            data_path = os.path.join(project_path, "data")
            security_path = os.path.join(data_path, "security")
            htpasswd_file_path = os.path.join(security_path, ".htpasswd")
            
            # Create security directory if it doesn't exist
            Path(security_path).mkdir(parents=True, exist_ok=True)
            
            if htpasswd_option.startswith(translator.get("Generate")):
                console.print(f"[bold cyan]{translator.get('Let\'s create a .htpasswd file with your users and passwords')}.[/]")
                
                # Use basic_auth_manager to generate htpasswd file
                if basic_auth_manager:
                    success = basic_auth_manager.generate_htpasswd_file(htpasswd_file_path)
                    if success:
                        console.print(f"[bold green]{translator.get('.htpasswd file successfully created at')} {htpasswd_file_path}[/]")
                    else:
                        console.print(f"[bold red]{translator.get('Failed to create .htpasswd file. You may need to create it manually.')}[/]")
                else:
                    console.print(f"[bold red]{translator.get('Error: Basic auth manager not available. Cannot generate .htpasswd file.')}[/]")
                    console.print(f"[yellow]{translator.get('Please create the .htpasswd file manually at')} {htpasswd_file_path}[/]")
            else:
                console.print(f"[bold cyan]{translator.get('Remember to place your .htpasswd file at')} {htpasswd_file_path}[/]")
            
            # Check if .htpasswd exists
            htpasswd_exists = Path(htpasswd_file_path).exists()
            
            if not htpasswd_exists:
                console.print(f"[bold yellow]{translator.get('.htpasswd file not found. You must add it to continue.')}[/]")
                
                console.print(f"[bold cyan]{translator.get('Waiting for .htpasswd file to be added...')}[/]")
                console.print(f"[cyan]{translator.get('Please add the file at')}: {htpasswd_file_path}[/]")
                
                # Wait for the .htpasswd to appear - user cannot proceed without it
                import time
                
                while True:
                    # Sleep briefly to avoid high CPU usage and give time for file system operations
                    time.sleep(1)
                    
                    # Force refresh the directory
                    try:
                        # Check if .htpasswd exists now
                        htpasswd_exists = os.path.isfile(htpasswd_file_path)
                        
                        if htpasswd_exists:
                            console.print(f"[bold green]{translator.get('.htpasswd file found! Continuing...')}[/]")
                            break
                    except Exception as e:
                        console.print(f"[bold red]Error checking files: {str(e)}[/]")
                    
                    console.print(f"[yellow]{translator.get('Still waiting for .htpasswd file at')}: {htpasswd_file_path}[/]")
                    
                    # Ask if user wants to change security method instead of adding .htpasswd
                    change_security_method = questionary.confirm(
                        translator.get("Do you want to return to the security selection menu?"),
                        default=False,
                        style=custom_style
                    ).ask()
                    
                    if change_security_method:
                        # Switch to no security
                        nginx_config["security"]["type"] = "none"
                        console.print(f"[bold cyan]{translator.get('Switching to no additional security mode...')}[/]")
                        return
            else:
                console.print(f"[bold green]{translator.get('.htpasswd file found and ready to use.')}[/]")
            
        elif new_security_type == "client_cert":
            # Client certificate handling
            cert_source = questionary.select(
                translator.get("How would you like to handle client certificates?"),
                choices=[
                    translator.get("I'll provide my own certificates"),
                    translator.get("Generate certificates for me")
                ],
                style=custom_style
            ).ask()
            
            if cert_source.startswith(translator.get("Generate")):
                client_name = questionary.text(
                    translator.get("Enter a name for the client certificate:"),
                    default="TeddyCloudClient01",
                    style=custom_style
                ).ask()
                # Generate certificate with client_cert_manager
                success, cert_info = client_cert_manager.generate_client_certificate(client_name)   
                create_client_certificate(translator, security_managers["client_cert_manager"])             
                if success and cert_info:
                    console.print(f"[bold green]{translator.get('Client certificate successfully created and saved to config.')}[/]")
                else:
                    console.print(f"[bold red]{translator.get('Failed to create client certificate. Please try again.')}[/]")
    
    # Handle IP restrictions
    modify_ip = questionary.confirm(
        translator.get("Would you like to modify IP address restrictions?"),
        default=bool(current_ip_restrictions),
        style=custom_style
    ).ask()
    
    if modify_ip:
        if security_managers.get("ip_restrictions_manager"):
            security_managers["ip_restrictions_manager"].configure_ip_restrictions(nginx_config)
        else:
            console.print(f"[bold yellow]{translator.get('Warning')}: {translator.get('IP restrictions manager not available')}[/]")
    
    return config

def modify_domain_name(config, translator):
    """
    Modify domain name for nginx mode.
    
    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        
    Returns:
        dict: The updated configuration dictionary
    """
    nginx_config = config["nginx"]
    current_domain = nginx_config.get("domain", "")
    
    console.print(f"[bold cyan]{translator.get('Current domain name')}: {current_domain or translator.get('Not set')}[/]")
    
    domain = questionary.text(
        translator.get("Enter the domain name for your TeddyCloud instance:"),
        default=current_domain,
        validate=lambda d: validate_domain_name(d),
        style=custom_style
    ).ask()
    
    if domain != current_domain:
        nginx_config["domain"] = domain
        console.print(f"[bold green]{translator.get('Domain name updated to')} {domain}[/]")
        
        # Check if domain is publicly resolvable
        domain_resolvable = check_domain_resolvable(domain)
        if not domain_resolvable:
            console.print(Panel(
                f"[bold yellow]{translator.get('Domain Not Resolvable')}[/]\n\n"
                f"{translator.get('The domain')} '{domain}' {translator.get('could not be resolved using public DNS servers.')}\n"
                f"{translator.get('If using Let\'s Encrypt, make sure the domain is publicly resolvable.')}",
                box=box.ROUNDED,
                border_style="yellow"
            ))
            
            # If using Let's Encrypt, offer to change HTTPS mode
            if nginx_config.get("https_mode") == "letsencrypt":
                console.print(f"[bold yellow]{translator.get('Warning')}: {translator.get('Let\'s Encrypt requires a publicly resolvable domain.')}[/]")
                change_https_mode = questionary.confirm(
                    translator.get("Would you like to switch from Let's Encrypt to self-signed certificates?"),
                    default=True,
                    style=custom_style
                ).ask()
                
                if change_https_mode:
                    nginx_config["https_mode"] = "self_signed"
                    console.print(f"[bold green]{translator.get('HTTPS mode updated to self-signed certificates.')}[/]")
    else:
        console.print(f"[bold cyan]{translator.get('Domain name unchanged.')}[/]")
    
    return config