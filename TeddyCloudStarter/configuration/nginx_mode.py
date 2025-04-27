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
from ..utils import check_port_available, validate_domain_name, validate_ip_address

def configure_nginx_mode(config, translator, cert_manager):
    """
    Configure nginx deployment mode settings.
    
    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        cert_manager: The certificate manager instance
        
    Returns:
        dict: The updated configuration dictionary
    """
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
    
    # Ask about HTTPS
    https_mode = questionary.select(
        translator.get("How would you like to handle HTTPS?"),
        choices=[
            translator.get("Let's Encrypt (automatic certificates)"),
            translator.get("Custom certificates (provide your own)")
        ],
        style=custom_style
    ).ask()
    
    nginx_config["https_mode"] = "letsencrypt" if https_mode.startswith(translator.get("Let's")) else "custom"
    
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
                cert_manager.request_letsencrypt_certificate(domain)
        else:
            # Switch to custom mode
            nginx_config["https_mode"] = "custom"
            console.print(f"[bold cyan]{translator.get('Switching to custom certificates mode')}...[/]")
    
    if nginx_config["https_mode"] == "custom":
        server_certs_path = os.path.join(project_path, "data", "server_certs")
        server_crt_path = os.path.join(server_certs_path, "server.crt")
        server_key_path = os.path.join(server_certs_path, "server.key")
        
        console.print(Panel(
            f"[bold cyan]{translator.get('Custom Certificate Instructions')}[/]\n\n"
            f"{translator.get('You will need to provide your own SSL certificates.')}\n"
            f"1. {translator.get('Create a directory')}: {server_certs_path}\n"
            f"2. {translator.get('Place your certificate as')}: {server_crt_path}\n"
            f"3. {translator.get('Place your private key as')}: {server_key_path}",
            box=box.ROUNDED,
            border_style="cyan"
        ))
        
        # Create server_certs directory if it doesn't exist
        Path(server_certs_path).mkdir(parents=True, exist_ok=True)
        
        # Check if certificates exist
        server_cert_exists = Path(server_crt_path).exists()
        server_key_exists = Path(server_key_path).exists()
        
        if not (server_cert_exists and server_key_exists):
            console.print(f"[bold yellow]{translator.get('Certificates not found. You must add them to continue.')}[/]")
            
            console.print(f"[bold cyan]{translator.get('Waiting for certificates to be added...')}[/]")
            console.print(f"[cyan]{translator.get('Please add the following files:')}\n"
                          f"1. {server_crt_path}\n"
                          f"2. {server_key_path}[/]")
            
            # Wait for the certificates to appear - user cannot proceed without them
            import time
            import subprocess
            
            # Try to create empty marker files to ensure directory is writeable
            try:
                Path(os.path.join(server_certs_path, "certificate_check.tmp")).touch()
                os.remove(os.path.join(server_certs_path, "certificate_check.tmp"))
                console.print(f"[green]{translator.get('Directory is writable.')}[/]")
            except Exception as e:
                console.print(f"[bold yellow]{translator.get('Warning: Directory permissions issue - ')} {str(e)}[/]")
            
            attempt_count = 0
            while True:
                attempt_count += 1
                # Sleep briefly to avoid high CPU usage and give time for file system operations
                time.sleep(1)
                
                # Force directory refresh with system commands (can help with file system cache issues)
                if attempt_count % 5 == 0:
                    try:
                        if os.name == 'nt':  # Windows
                            subprocess.run(f'dir "{server_certs_path}"', shell=True, capture_output=True)
                        else:  # Unix-based
                            subprocess.run(f'ls -la "{server_certs_path}"', shell=True, capture_output=True)
                    except Exception:
                        pass
                
                # Try multiple detection methods
                server_cert_exists = False
                server_key_exists = False
                
                # Method 1: Direct os.path.isfile check
                try:
                    server_cert_exists = os.path.isfile(server_crt_path)
                    server_key_exists = os.path.isfile(server_key_path)
                except Exception:
                    pass
                
                # Method 2: Try direct file open if method 1 failed
                if not server_cert_exists:
                    try:
                        with open(server_crt_path, 'rb') as f:
                            server_cert_exists = True
                    except Exception:
                        pass
                        
                if not server_key_exists:
                    try:
                        with open(server_key_path, 'rb') as f:
                            server_key_exists = True
                    except Exception:
                        pass
                
                # Method 3: Use subprocess as a last resort
                if not (server_cert_exists and server_key_exists) and attempt_count % 10 == 0:
                    try:
                        if os.name == 'nt':  # Windows
                            cert_result = subprocess.run(f'if exist "{server_crt_path}" echo EXISTS', 
                                                        shell=True, capture_output=True, text=True)
                            key_result = subprocess.run(f'if exist "{server_key_path}" echo EXISTS', 
                                                        shell=True, capture_output=True, text=True)
                            
                            server_cert_exists = server_cert_exists or 'EXISTS' in cert_result.stdout
                            server_key_exists = server_key_exists or 'EXISTS' in key_result.stdout
                        else:
                            cert_result = subprocess.run(f'test -f "{server_crt_path}" && echo "EXISTS"', 
                                                        shell=True, capture_output=True, text=True)
                            key_result = subprocess.run(f'test -f "{server_key_path}" && echo "EXISTS"', 
                                                        shell=True, capture_output=True, text=True)
                            
                            server_cert_exists = server_cert_exists or 'EXISTS' in cert_result.stdout
                            server_key_exists = server_key_exists or 'EXISTS' in key_result.stdout
                    except Exception:
                        pass
                
                # Provide detailed update about file detection
                if attempt_count % 5 == 0:
                    console.print(f"[dim]{translator.get('Checking for certificate files (attempt')}: {attempt_count})...[/]")
                    
                    # Print file sizes if they exist to help diagnose issues
                    try:
                        if os.path.exists(server_crt_path):
                            size = os.path.getsize(server_crt_path)
                            console.print(f"[dim]{translator.get('Found')} server.crt - {size} bytes[/]")
                        if os.path.exists(server_key_path):
                            size = os.path.getsize(server_key_path)
                            console.print(f"[dim]{translator.get('Found')} server.key - {size} bytes[/]")
                    except Exception:
                        pass
                
                if server_cert_exists and server_key_exists:
                    console.print(f"[bold green]{translator.get('Both certificate files found! Continuing...')}[/]")
                    
                    # Validate certificates for Nginx compatibility and matching
                    console.print(f"[cyan]{translator.get('Validating certificates for Nginx compatibility...')}[/]")
                    is_valid, error_msg = validate_certificates(server_crt_path, server_key_path, translator)
                    
                    if not is_valid:
                        console.print(f"[bold red]{translator.get('Certificate validation failed')}:[/]")
                        console.print(f"[red]{error_msg}[/]")
                        
                        # Ask if user wants to try again with different certificates
                        retry_cert = questionary.confirm(
                            translator.get("Do you want to replace the certificates with valid ones?"),
                            default=True,
                            style=custom_style
                        ).ask()
                        
                        if retry_cert:
                            # Remove the invalid certificates
                            try:
                                if os.path.exists(server_crt_path):
                                    os.remove(server_crt_path)
                                if os.path.exists(server_key_path):
                                    os.remove(server_key_path)
                                console.print(f"[yellow]{translator.get('Invalid certificates removed. Please provide new ones.')}[/]")
                                # Continue the loop to wait for new certificates
                                continue
                            except Exception as e:
                                console.print(f"[bold red]{translator.get('Error removing invalid certificates')}: {str(e)}[/]")
                        else:
                            # User wants to continue anyway
                            console.print(f"[bold yellow]{translator.get('Warning: Continuing with invalid certificates. Nginx may fail to start.')}[/]")
                    else:
                        console.print(f"[bold green]{translator.get('Certificates validated successfully!')}[/]")
                    
                    break
                
                # Give status update on which files are still missing
                missing_files = []
                if not server_cert_exists:
                    missing_files.append(f"server.crt ({server_crt_path})")
                if not server_key_exists:
                    missing_files.append(f"server.key ({server_key_path})")
                
                missing_str = ", ".join(missing_files)
                
                # Only show the waiting message every few seconds to avoid flooding the console
                if attempt_count % 3 == 0:
                    console.print(f"[yellow]{translator.get('Still waiting for')}: {missing_str}[/]")
                
                # Ask if user wants to return to certificate selection every 15 seconds
                if attempt_count % 15 == 0:
                    change_cert_method = questionary.confirm(
                        translator.get("Do you want to return to the certificate selection menu?"),
                        default=False,
                        style=custom_style
                    ).ask()
                    
                    if change_cert_method:
                        # Switch to Let's Encrypt and continue with proper configuration
                        nginx_config["https_mode"] = "letsencrypt"
                        console.print(f"[bold cyan]{translator.get('Switching to Let\'s Encrypt certificate mode...')}[/]")
                        
                        # Show Let's Encrypt requirements
                        console.print(Panel(
                            f"[bold yellow]{translator.get('Let\'s Encrypt Requirements')}[/]\n\n"
                            f"{translator.get('To use Let\'s Encrypt, you need:')}\n"
                            f"1. {translator.get('A public domain name pointing to this server')}\n"
                            f"2. {translator.get('Public internet access on ports 80 and 443')}\n"
                            f"3. {translator.get('This server must be reachable from the internet')}",
                            box=box.ROUNDED,
                            border_style="yellow"
                        ))
                        
                        # Ask if user meets Let's Encrypt requirements to continue properly
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
                                cert_manager.request_letsencrypt_certificate(domain)
                        else:
                            # If user doesn't meet requirements, we won't test Let's Encrypt
                            console.print(f"[bold yellow]{translator.get('Skipping Let\'s Encrypt certificate test.')}[/]")
                        
                        # Continue with the rest of configuration - don't return
                        break
        else:
            console.print(f"[bold green]{translator.get('Certificate files found and ready to use.')}[/]")
    
    # Configure security
    configure_security(nginx_config, translator, cert_manager, project_path)
    
    return config

def configure_security(nginx_config, translator, cert_manager, project_path):
    """
    Configure security settings for Nginx mode.
    
    Args:
        nginx_config: The nginx configuration dictionary
        translator: The translator instance for localization
        cert_manager: The certificate manager instance
        project_path: The project path for file operations
    """
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
                
                # Use Docker to generate htpasswd file
                generate_htpasswd_file(htpasswd_file_path, translator)
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
                cert_manager.generate_client_certificate(client_name, project_path)
            
            break  # Break out of the outer while loop once configuration is complete
    
    # Ask about IP restrictions
    configure_ip_restrictions(nginx_config, translator)

def configure_ip_restrictions(nginx_config, translator):
    """
    Configure IP address restrictions for Nginx mode.
    
    Args:
        nginx_config: The nginx configuration dictionary
        translator: The translator instance for localization
    """
    use_ip_restriction = questionary.confirm(
        translator.get("Would you like to restrict access by IP address?"),
        default=bool(nginx_config["security"]["allowed_ips"]),
        style=custom_style
    ).ask()
    
    if use_ip_restriction:
        ip_addresses = []
        
        console.print(f"[bold cyan]{translator.get('Enter the IP addresses to allow (empty line to finish):')}[/]")
        console.print(f"[green]{translator.get('You can use individual IPs (e.g., 192.168.1.10) or CIDR notation (e.g., 192.168.1.0/24)')}[/]")
        
        # Show current IPs if any
        if nginx_config["security"]["allowed_ips"]:
            console.print(f"[bold cyan]{translator.get('Current allowed IPs')}:[/]")
            for ip in nginx_config["security"]["allowed_ips"]:
                console.print(f"[cyan]{ip}[/]")
        
        # Allow adding new IPs
        while True:
            ip = Prompt.ask(f"[bold cyan]{translator.get('IP address or CIDR')}[/]", default="")
            
            if not ip:
                break
            
            if validate_ip_address(ip):
                ip_addresses.append(ip)
                console.print(f"[green]{translator.get('Added')}: {ip}[/]")
            else:
                console.print(f"[bold red]{translator.get('Invalid IP address or CIDR')}: {ip}[/]")
        
        nginx_config["security"]["allowed_ips"] = ip_addresses
        console.print(f"[bold green]{translator.get('IP restrictions updated')}[/]")
    else:
        nginx_config["security"]["allowed_ips"] = []
        console.print(f"[bold green]{translator.get('IP restrictions removed')}[/]")

def modify_domain_name(config, translator):
    """
    Modify domain name for nginx mode.
    
    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
    """
    nginx_config = config["nginx"]
    current_domain = nginx_config["domain"]
    
    console.print(f"[bold cyan]{translator.get('Current domain name')}: {current_domain}[/]")
    
    domain = questionary.text(
        translator.get("Enter the domain name for your TeddyCloud instance:"),
        default=current_domain,
        validate=lambda d: validate_domain_name(d),
        style=custom_style
    ).ask()
    
    nginx_config["domain"] = domain
    console.print(f"[bold green]{translator.get('Domain name updated to')} {domain}[/]")
    
    return config

def modify_https_mode(config, translator, cert_manager):
    """
    Modify HTTPS mode for nginx mode.
    
    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        cert_manager: The certificate manager instance
    """
    nginx_config = config["nginx"]
    current_mode = nginx_config["https_mode"]
    
    # Get the project path from config
    project_path = config.get("environment", {}).get("path", "")
    if not project_path:
        console.print(f"[bold red]{translator.get('Warning')}: {translator.get('Project path not set. Using current directory.')}[/]")
        project_path = os.getcwd()
    
    console.print(f"[bold cyan]{translator.get('Current HTTPS mode')}: {current_mode}[/]")
    
    # Define the choices
    choices = [
        translator.get("Let's Encrypt (automatic certificates)"),
        translator.get("Custom certificates (provide your own)")
    ]
    
    # Determine the default choice based on current mode
    default_choice = choices[0] if current_mode == "letsencrypt" else choices[1]
    
    https_mode = questionary.select(
        translator.get("How would you like to handle HTTPS?"),
        choices=choices,
        default=default_choice,
        style=custom_style
    ).ask()
    
    new_mode = "letsencrypt" if https_mode.startswith(translator.get("Let's")) else "custom"
    
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
                    cert_manager.request_letsencrypt_certificate(nginx_config["domain"])
            else:
                # Switch back to custom mode
                nginx_config["https_mode"] = "custom"
                console.print(f"[bold cyan]{translator.get('Switching to custom certificates mode')}...[/]")
        
        if nginx_config["https_mode"] == "custom":
            server_certs_path = os.path.join(project_path, "data", "server_certs")
            server_crt_path = os.path.join(server_certs_path, "server.crt")
            server_key_path = os.path.join(server_certs_path, "server.key")
            
            console.print(Panel(
                f"[bold cyan]{translator.get('Custom Certificate Instructions')}[/]\n\n"
                f"{translator.get('You will need to provide your own SSL certificates.')}\n"
                f"1. {translator.get('Create a directory')}: {server_certs_path}\n"
                f"2. {translator.get('Place your certificate as')}: {server_crt_path}\n"
                f"3. {translator.get('Place your private key as')}: {server_key_path}",
                box=box.ROUNDED,
                border_style="cyan"
            ))
            
            # Create server_certs directory if it doesn't exist
            Path(server_certs_path).mkdir(parents=True, exist_ok=True)
            
            # Check if certificates exist
            server_cert_exists = Path(server_crt_path).exists()
            server_key_exists = Path(server_key_path).exists()
            
            if not (server_cert_exists and server_key_exists):
                console.print(f"[bold yellow]{translator.get('Certificates not found. You must add them to continue.')}[/]")
                
                console.print(f"[bold cyan]{translator.get('Waiting for certificates to be added...')}[/]")
                console.print(f"[cyan]{translator.get('Please add the following files:')}\n"
                              f"1. {server_crt_path}\n"
                              f"2. {server_key_path}[/]")
                
                # Wait for the certificates to appear - user cannot proceed without them
                import time
                
                while True:
                    # Sleep briefly to avoid high CPU usage and give time for file system operations
                    time.sleep(1)
                    
                    # Force refresh the directory
                    try:
                        # Check if certificates exist now
                        server_cert_exists = os.path.isfile(server_crt_path)
                        server_key_exists = os.path.isfile(server_key_path)
                        
                        if server_cert_exists and server_key_exists:
                            console.print(f"[bold green]{translator.get('Both certificate files found! Continuing...')}[/]")
                            
                            # Validate certificates for Nginx compatibility and matching
                            console.print(f"[cyan]{translator.get('Validating certificates for Nginx compatibility...')}[/]")
                            is_valid, error_msg = validate_certificates(server_crt_path, server_key_path, translator)
                            
                            if not is_valid:
                                console.print(f"[bold red]{translator.get('Certificate validation failed')}:[/]")
                                console.print(f"[red]{error_msg}[/]")
                                
                                # Ask if user wants to try again with different certificates
                                retry_cert = questionary.confirm(
                                    translator.get("Do you want to replace the certificates with valid ones?"),
                                    default=True,
                                    style=custom_style
                                ).ask()
                                
                                if retry_cert:
                                    # Remove the invalid certificates
                                    try:
                                        if os.path.exists(server_crt_path):
                                            os.remove(server_crt_path)
                                        if os.path.exists(server_key_path):
                                            os.remove(server_key_path)
                                        console.print(f"[yellow]{translator.get('Invalid certificates removed. Please provide new ones.')}[/]")
                                        # Continue the loop to wait for new certificates
                                        continue
                                    except Exception as e:
                                        console.print(f"[bold red]{translator.get('Error removing invalid certificates')}: {str(e)}[/]")
                                else:
                                    # User wants to continue anyway
                                    console.print(f"[bold yellow]{translator.get('Warning: Continuing with invalid certificates. Nginx may fail to start.')}[/]")
                            else:
                                console.print(f"[bold green]{translator.get('Certificates validated successfully!')}[/]")
                                
                            break
                    except Exception as e:
                        console.print(f"[bold red]Error checking files: {str(e)}[/]")
                    
                    # Give status update on which files are still missing
                    missing_files = []
                    if not server_cert_exists:
                        missing_files.append(f"server.crt ({server_crt_path})")
                    if not server_key_exists:
                        missing_files.append(f"server.key ({server_key_path})")
                    
                    missing_str = ", ".join(missing_files)
                    console.print(f"[yellow]{translator.get('Still waiting for')}: {missing_str}[/]")
                    
                    # Ask if user wants to return to certificate selection instead of adding custom certificates
                    change_cert_method = questionary.confirm(
                        translator.get("Do you want to return to the certificate selection menu?"),
                        default=False,
                        style=custom_style
                    ).ask()
                    
                    if change_cert_method:
                        # Switch to Let's Encrypt and continue with proper configuration
                        nginx_config["https_mode"] = "letsencrypt"
                        console.print(f"[bold cyan]{translator.get('Switching to Let\'s Encrypt certificate mode...')}[/]")
                        
                        # Show Let's Encrypt requirements
                        console.print(Panel(
                            f"[bold yellow]{translator.get('Let\'s Encrypt Requirements')}[/]\n\n"
                            f"{translator.get('To use Let\'s Encrypt, you need:')}\n"
                            f"1. {translator.get('A public domain name pointing to this server')}\n"
                            f"2. {translator.get('Public internet access on ports 80 and 443')}\n"
                            f"3. {translator.get('This server must be reachable from the internet')}",
                            box=box.ROUNDED,
                            border_style="yellow"
                        ))
                        
                        # Ask if user meets Let's Encrypt requirements to continue properly
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
                                cert_manager.request_letsencrypt_certificate(nginx_config["domain"])
                        else:
                            # If user doesn't meet requirements, we won't test Let's Encrypt
                            console.print(f"[bold yellow]{translator.get('Skipping Let\'s Encrypt certificate test.')}[/]")
                        
                        # Continue with the rest of configuration - don't return
                        break
            else:
                console.print(f"[bold green]{translator.get('Certificate files found and ready to use.')}[/]")
    
    return config

def modify_security_settings(config, translator, cert_manager):
    """
    Modify security settings for nginx mode.
    
    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        cert_manager: The certificate manager instance
    """
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
                console.print(f"[yellow]{translator.get('You\'ll need to create the .htpasswd file manually at')} {htpasswd_file_path}[/]")
                console.print(f"[yellow]{translator.get('Please use an online .htpasswd generator or the htpasswd utility')}[/]")
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
                cert_manager.generate_client_certificate(client_name, project_path)
    
    # Handle IP restrictions
    modify_ip = questionary.confirm(
        translator.get("Would you like to modify IP address restrictions?"),
        default=bool(current_ip_restrictions),
        style=custom_style
    ).ask()
    
    if modify_ip:
        configure_ip_restrictions(nginx_config, translator)
    
    return config

def generate_htpasswd_file(htpasswd_file_path, translator):
    """
    Generates a .htpasswd file using Docker httpd Alpine image.
    
    Args:
        htpasswd_file_path: Path where the .htpasswd file will be saved
        translator: Translator instance for localization
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Function to check internet connectivity to Docker Hub
    def check_internet_connection():
        """
        Check if we can connect to Docker Hub or other internet resources.
        Uses multiple methods to be more reliable than a simple ping.
        
        Returns:
            bool: True if internet connectivity is detected, False otherwise
        """
        # Method 1: Try DNS resolution first (doesn't require admin privileges)
        try:
            import socket
            socket.gethostbyname("registry-1.docker.io")
            return True
        except Exception:
            pass
        
        # Method 2: Try a lightweight HTTP request if available
        try:
            import urllib.request
            urllib.request.urlopen("https://registry-1.docker.io/", timeout=2)
            return True
        except Exception:
            pass

        # Method 3: Try with Python's socket directly
        try:
            import socket
            socket_obj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            socket_obj.settimeout(2)
            socket_obj.connect(("registry-1.docker.io", 443))
            socket_obj.close()
            return True
        except Exception:
            pass
            
        # Method 4: Fall back to checking if Docker command works with a simple image
        try:
            # Try to see if a Docker registry communication works (this actually tests Docker's ability to talk to registry)
            result = subprocess.run(
                ["docker", "search", "--limit=1", "alpine"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            pass
        
        # Method 5: Only use ping as a last resort
        try:
            # Try to connect to a reliable DNS first
            subprocess.run(["ping", "1.1.1.1", "-n", "1" if os.name == 'nt' else "-c", "1"], 
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
            return True
        except Exception:
            try:
                # Try an alternate reliable host
                subprocess.run(["ping", "8.8.8.8", "-n", "1" if os.name == 'nt' else "-c", "1"], 
                               check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
                return True
            except Exception:
                # All methods failed
                return False

    # Function to attempt .htpasswd generation, with retry handling
    def attempt_htpasswd_generation(users):
        while True:
            try:
                # Check if Docker is available
                try:
                    subprocess.run(["docker", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                except (subprocess.SubprocessError, FileNotFoundError):
                    console.print(f"[bold red]{translator.get('Docker is not available. Cannot generate .htpasswd file.')}[/]")
                    console.print(f"[yellow]{translator.get('You\'ll need to create the .htpasswd file manually.')}[/]")
                    return False

                # Check internet connection
                if not check_internet_connection():
                    console.print(f"[bold red]{translator.get('Error: No internet connection detected. Docker may not be able to pull the httpd image.')}[/]")
                    retry = questionary.confirm(
                        translator.get("Would you like to check your connection and retry?"),
                        default=True,
                        style=custom_style
                    ).ask()
                    
                    if not retry:
                        console.print(f"[yellow]{translator.get('Skipping .htpasswd generation. You will need to create it manually.')}[/]")
                        return False
                    
                    console.print(f"[cyan]{translator.get('Retrying .htpasswd generation...')}[/]")
                    continue
                console.print(f"[cyan]{translator.get('Pulling httpd:alpine Docker image...')}[/]")
                pull_result = subprocess.run(
                    ["docker", "pull", "httpd:alpine"],
                    capture_output=True,
                    text=True
                )
                
                if pull_result.returncode != 0:
                    console.print(f"[bold red]{translator.get('Error pulling Docker image')}:[/]")
                    console.print(f"[red]{pull_result.stderr}[/]")
                    
                    # Check if it's a network error
                    if "network" in pull_result.stderr.lower() or "connection" in pull_result.stderr.lower() or "dial" in pull_result.stderr.lower() or "lookup" in pull_result.stderr.lower():
                        console.print(f"[bold yellow]{translator.get('Network error detected. Please check your internet connection.')}[/]")
                        
                        retry = questionary.confirm(
                            translator.get("Would you like to retry after checking your connection?"),
                            default=True,
                            style=custom_style
                        ).ask()
                        
                        if retry:
                            console.print(f"[cyan]{translator.get('Retrying .htpasswd generation...')}[/]")
                            continue
                        else:
                            console.print(f"[yellow]{translator.get('Skipping .htpasswd generation. You will need to create it manually.')}[/]")
                            return False
                    else:
                        # For other Docker errors
                        console.print(f"[bold red]{translator.get('Docker error. Cannot generate .htpasswd file.')}[/]")
                        return False
                
                # Create .htpasswd file using Docker
                console.print(f"[bold cyan]{translator.get('Generating .htpasswd file...')}[/]")
                
                # Create the parent directory if it doesn't exist
                security_path = os.path.dirname(htpasswd_file_path)
                Path(security_path).mkdir(parents=True, exist_ok=True)
                
                # Windows specific: Fix the path format for Docker
                if os.name == 'nt':
                    docker_security_path = security_path.replace('\\', '/')
                    if ':' in docker_security_path:
                        docker_security_path = '/' + docker_security_path[0].lower() + docker_security_path[2:]
                else:
                    docker_security_path = security_path
                
                console.print(f"[dim]{translator.get('Using Docker volume path')}: {docker_security_path}[/]")
                
                # Define temp filename for Docker to create
                temp_filename = "temp_htpasswd.txt"
                temp_htpasswd = os.path.join(security_path, temp_filename)
                
                # Generate the initial file
                first_user = users[0]
                cmd = [
                    "docker", "run", "--rm", 
                    "-v", f"{security_path}:/htpasswd",
                    "httpd:alpine", "sh", "-c", 
                    f"htpasswd -cb /htpasswd/{temp_filename} {first_user['username']} {first_user['password']}"
                ]
                
                # On Windows, use special Docker path format
                if os.name == 'nt':
                    cmd = [
                        "docker", "run", "--rm", 
                        "-v", f"{docker_security_path}:/htpasswd",
                        "httpd:alpine", "sh", "-c", 
                        f"htpasswd -cb /htpasswd/{temp_filename} {first_user['username']} {first_user['password']}"
                    ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    console.print(f"[bold red]{translator.get('Error creating .htpasswd file')}:[/]")
                    console.print(f"[red]{result.stderr}[/]")
                    raise Exception(f"Failed to create .htpasswd: {result.stderr}")
                
                # Add additional users
                for user in users[1:]:
                    # On Windows, use special Docker path format
                    cmd = [
                        "docker", "run", "--rm", 
                        "-v", f"{security_path}:/htpasswd",
                        "httpd:alpine", "sh", "-c", 
                        f"htpasswd -b /htpasswd/{temp_filename} {user['username']} {user['password']}"
                    ]
                    
                    if os.name == 'nt':
                        cmd = [
                            "docker", "run", "--rm", 
                            "-v", f"{docker_security_path}:/htpasswd",
                            "httpd:alpine", "sh", "-c", 
                            f"htpasswd -b /htpasswd/{temp_filename} {user['username']} {user['password']}"
                        ]
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode != 0:
                        raise Exception(f"Failed to add user {user['username']}: {result.stderr}")
                
                # Ensure directory exists for the target file
                Path(os.path.dirname(htpasswd_file_path)).mkdir(parents=True, exist_ok=True)
                
                try:
                    # Move the temp file to the final location
                    if os.path.exists(temp_htpasswd):
                        # Check if the destination exists and remove it if needed
                        if os.path.exists(htpasswd_file_path):
                            os.remove(htpasswd_file_path)
                            
                        # Copy instead of move to handle cross-device scenarios
                        shutil.copy2(temp_htpasswd, htpasswd_file_path)
                        
                        # Only remove temp file after successful copy
                        if os.path.exists(htpasswd_file_path) and os.path.getsize(htpasswd_file_path) > 0:
                            try:
                                os.remove(temp_htpasswd)
                            except Exception as e:
                                console.print(f"[dim]{translator.get('Note: Could not remove temporary file')} {temp_htpasswd}: {str(e)}[/]")
                    else:
                        raise FileNotFoundError(f"Temporary file {temp_htpasswd} not found")
                except Exception as e:
                    console.print(f"[bold red]{translator.get('Error moving .htpasswd file')}: {str(e)}[/]")
                    
                    # Try direct Docker write approach as fallback
                    console.print(f"[cyan]{translator.get('Attempting alternative .htpasswd generation...')}[/]")
                    try:
                        # Write directly to final location
                        first_user = users[0]
                        cmd = [
                            "docker", "run", "--rm", 
                            "-v", f"{docker_security_path}:/htpasswd",
                            "httpd:alpine", "sh", "-c", 
                            f"htpasswd -cb /htpasswd/.htpasswd {first_user['username']} {first_user['password']}"
                        ]
                        
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True
                        )
                        
                        if result.returncode != 0:
                            raise Exception(f"Failed in fallback method: {result.stderr}")
                        
                        # Add additional users directly
                        for user in users[1:]:
                            cmd = [
                                "docker", "run", "--rm", 
                                "-v", f"{docker_security_path}:/htpasswd",
                                "httpd:alpine", "sh", "-c", 
                                f"htpasswd -b /htpasswd/.htpasswd {user['username']} {user['password']}"
                            ]
                            
                            result = subprocess.run(
                                cmd,
                                capture_output=True,
                                text=True
                            )
                            
                            if result.returncode != 0:
                                raise Exception(f"Failed to add user {user['username']}: {result.stderr}")
                    except Exception as e:
                        console.print(f"[bold red]{translator.get('Alternative method also failed')}: {str(e)}[/]")
                        raise
                
                # Verify the file was created and has content
                if os.path.exists(htpasswd_file_path) and os.path.getsize(htpasswd_file_path) > 0:
                    console.print(f"[bold green]{translator.get('.htpasswd file generated successfully!')}[/]")
                    console.print(f"[green]{translator.get('.htpasswd file location')}: {htpasswd_file_path}[/]")
                    return True
                else:
                    console.print(f"[bold red]{translator.get('Failed to create .htpasswd file or file is empty')}[/]")
                    retry = questionary.confirm(
                        translator.get("Would you like to retry?"),
                        default=True,
                        style=custom_style
                    ).ask()
                    
                    if not retry:
                        return False
                    
                    # If retry, loop will continue
                
            except Exception as e:
                console.print(f"[bold red]{translator.get('Error generating .htpasswd file')}: {str(e)}[/]")
                
                # Print detailed exception information for debugging
                import traceback
                console.print(f"[dim]{traceback.format_exc()}[/]")
                
                # Ask to retry
                retry = questionary.confirm(
                    translator.get("Would you like to retry .htpasswd generation?"),
                    default=True,
                    style=custom_style
                ).ask()
                
                if not retry:
                    return False
    
    # Main function execution starts here
    try:
        # Create a table for collecting user credentials
        table = Table(title=translator.get("User Authentication Setup"))
        table.add_column(translator.get("Username"), justify="left", style="cyan")
        table.add_column(translator.get("Password"), justify="left", style="green", no_wrap=True)
        table.add_column(translator.get("Status"), justify="right", style="bold")
        
        # Collect user credentials
        users = []
        console.print(f"[bold cyan]{translator.get('Enter user credentials for basic authentication')}[/]")
        console.print(f"[cyan]{translator.get('(Passwords will not be displayed as you type)')}\n[/]")
        
        while True:
            username = Prompt.ask(f"[bold cyan]{translator.get('Username')} [/][dim]{translator.get('(leave empty to finish)')}[/]", 
                                default="")
            
            if not username:
                if not users:
                    console.print(f"[bold yellow]{translator.get('No users added. At least one user is required.')}[/]")
                    continue
                break
            
            # Check for duplicate usernames
            if any(u['username'] == username for u in users):
                console.print(f"[bold red]{translator.get('Username already exists. Please choose another one.')}[/]")
                continue
                
            # Use getpass for hidden password input
            console.print(f"[bold cyan]{translator.get('Enter password for user')} {username}:[/]")
            password = getpass.getpass("")
            
            if not password:
                console.print(f"[bold red]{translator.get('Password cannot be empty')}[/]")
                continue
                
            console.print(f"[bold cyan]{translator.get('Confirm password for user')} {username}:[/]")
            confirm_password = getpass.getpass("")
            
            if password != confirm_password:
                console.print(f"[bold red]{translator.get('Passwords do not match')}[/]")
                continue
                
            # Add user to the list
            users.append({
                'username': username,
                'password': password
            })
            
            table.add_row(
                username, 
                "********", 
                f"[bold green]{translator.get('Added')}[/]"
            )
        
        # Display the table with all users
        if users:
            console.print("\n")
            console.print(table)
        
        if not users:
            console.print(f"[bold yellow]{translator.get('No users added. You\'ll need to create the .htpasswd file manually.')}[/]")
            return False
        
        # Attempt to generate the htpasswd file with retry functionality
        return attempt_htpasswd_generation(users)
            
    except Exception as e:
        console.print(f"[bold red]{translator.get('Error generating .htpasswd file')}: {str(e)}[/]")
        
        # Print detailed exception information for debugging
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/]")
        return False

def validate_certificates(cert_path, key_path, translator):
    """
    Validate that the provided certificates are Nginx compatible and match each other.
    
    Args:
        cert_path: Path to the SSL certificate file
        key_path: Path to the SSL private key file
        translator: The translator instance for localization
    
    Returns:
        tuple: (bool, str) - (is_valid, error_message)
    """
    # Check if OpenSSL is available
    try:
        subprocess.run(["openssl", "version"], check=True, capture_output=True, text=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        console.print(f"[bold yellow]{translator.get('Warning: OpenSSL is not available. Certificate validation skipped.')}[/]")
        return True, ""
    
    # Check if certificate is valid
    try:
        cert_result = subprocess.run(
            ["openssl", "x509", "-in", cert_path, "-text", "-noout"],
            check=False, capture_output=True, text=True
        )
        
        if cert_result.returncode != 0:
            return False, f"{translator.get('Invalid certificate')}: {cert_result.stderr}"
            
        # Check if certificate is compatible with Nginx (basic validation)
        if "X509v3" not in cert_result.stdout:
            return False, translator.get('Certificate is not an X509v3 certificate, which might not be compatible with Nginx')
    except Exception as e:
        return False, f"{translator.get('Error validating certificate')}: {str(e)}"
    
    # Check if private key is valid
    try:
        key_result = subprocess.run(
            ["openssl", "rsa", "-in", key_path, "-check", "-noout"],
            check=False, capture_output=True, text=True
        )
        
        if key_result.returncode != 0:
            return False, f"{translator.get('Invalid private key')}: {key_result.stderr}"
    except Exception as e:
        return False, f"{translator.get('Error validating private key')}: {str(e)}"
    
    # Check if key matches certificate
    try:
        # Get modulus from certificate
        cert_modulus_result = subprocess.run(
            ["openssl", "x509", "-in", cert_path, "-modulus", "-noout"],
            check=False, capture_output=True, text=True
        )
        
        # Get modulus from private key
        key_modulus_result = subprocess.run(
            ["openssl", "rsa", "-in", key_path, "-modulus", "-noout"],
            check=False, capture_output=True, text=True
        )
        
        # Compare moduli
        if cert_modulus_result.stdout.strip() != key_modulus_result.stdout.strip():
            return False, translator.get('Certificate and private key do not match')
    except Exception as e:
        return False, f"{translator.get('Error checking if certificate and key match')}: {str(e)}"
    
    return True, ""