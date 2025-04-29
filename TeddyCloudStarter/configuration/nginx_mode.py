#!/usr/bin/env python3
"""
Nginx mode configuration for TeddyCloudStarter.
"""
import os
import subprocess
import time
from pathlib import Path
from ..wizard.ui_helpers import console
from ..utilities.network import check_port_available, check_domain_resolvable
from ..utilities.validation import ConfigValidator
from ..ui.nginx_mode_ui import (
    prompt_for_domain,
    prompt_for_https_mode,
    display_self_signed_certificate_info,
    prompt_security_type,
    prompt_htpasswd_option, 
    prompt_client_cert_source,
    prompt_client_cert_name,
    prompt_modify_ip_restrictions,
    confirm_continue_anyway,
    display_waiting_for_htpasswd,
    confirm_change_security_method,
    select_https_mode_for_modification,
    select_security_type_for_modification,
    prompt_for_fallback_option
)
from .letsencrypt_helper import handle_letsencrypt_setup, check_domain_suitable_for_letsencrypt

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
                "allowed_ips": [],
                "auth_bypass_ips": []
            }
        }
        
    nginx_config = config["nginx"]
    
    # Ensure the auth_bypass_ips field exists (for backward compatibility)
    if "security" in nginx_config and "auth_bypass_ips" not in nginx_config["security"]:
        nginx_config["security"]["auth_bypass_ips"] = []
    
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
        if not confirm_continue_anyway(translator):
            return config
    
    # Ask for domain
    domain = prompt_for_domain("", translator)
    
    nginx_config["domain"] = domain
    
    # Main certificate selection loop
    while True:
        # Check if domain is publicly resolvable
        domain_resolvable = check_domain_resolvable(domain)
        
        # Define choices for HTTPS mode based on domain resolution
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
        
        # Ask about HTTPS
        https_mode = prompt_for_https_mode(https_choices, default_choice, translator)
        
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
        
        # Handle Let's Encrypt configuration 
        if nginx_config["https_mode"] == "letsencrypt":
            letsencrypt_success = handle_letsencrypt_setup(nginx_config, translator, lets_encrypt_manager)
            if not letsencrypt_success:
                # Switch to self-signed mode as fallback
                nginx_config["https_mode"] = "self_signed"
                console.print(f"[bold cyan]{translator.get('Switching to self-signed certificates mode')}...[/]")
                # Continue with self-signed certificate handling
        
        # Handle self-signed certificate generation
        if nginx_config["https_mode"] == "self_signed":
            server_certs_path = os.path.join(project_path, "data", "server_certs")
            
            display_self_signed_certificate_info(domain, translator)
            
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
                fallback_option = prompt_for_fallback_option(translator)
                
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
        security_type = prompt_security_type(translator)
        
        if security_type.startswith(translator.get("No")):
            nginx_config["security"]["type"] = "none"
            break
        elif security_type.startswith(translator.get("Basic")):
            nginx_config["security"]["type"] = "basic_auth"
            
            # Ask if user wants to provide their own .htpasswd or generate one
            htpasswd_option = prompt_htpasswd_option(translator)
            
            # Use project path for data directory and htpasswd file
            data_path = os.path.join(project_path, "data")
            security_path = os.path.join(data_path, "security")
            htpasswd_file_path = os.path.join(security_path, ".htpasswd")
            
            # Create security directory if it doesn't exist
            Path(security_path).mkdir(parents=True, exist_ok=True)
            
            # Handle htpasswd creation choice
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
                
                # Flag to track if we need to return to security menu
                should_return_to_menu = False
                
                display_waiting_for_htpasswd(htpasswd_file_path, translator)
                
                # Wait for the .htpasswd to appear - user cannot proceed without it
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
                    if confirm_change_security_method(translator):
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
            
            cert_source = prompt_client_cert_source(translator)
            
            if cert_source.startswith(translator.get("Generate")):
                client_name = prompt_client_cert_name(translator)
                
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
        
        # Get user's selection for HTTPS mode
        _, new_mode = select_https_mode_for_modification(current_mode, translator)
        
        if new_mode != current_mode:
            nginx_config["https_mode"] = new_mode
            console.print(f"[bold green]{translator.get('HTTPS mode updated to')} {new_mode}[/]")
            
            if new_mode == "letsencrypt":
                # Use the Let's Encrypt helper function for setup
                letsencrypt_success = handle_letsencrypt_setup(nginx_config, translator, lets_encrypt_manager)
                
                if not letsencrypt_success:
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
                
                display_self_signed_certificate_info(domain, translator)
                
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
    
    # Get the project path from config
    project_path = config.get("environment", {}).get("path", "")
    if not project_path:
        console.print(f"[bold red]{translator.get('Warning')}: {translator.get('Project path not set. Using current directory.')}[/]")
        project_path = os.getcwd()
    
    console.print(f"[bold cyan]{translator.get('Current security type')}: {current_security_type}[/]")
    
    # First, choose security type
    _, new_security_type = select_security_type_for_modification(current_security_type, translator)
    
    # If security type changed, handle the new settings
    if new_security_type != current_security_type:
        nginx_config["security"]["type"] = new_security_type
        console.print(f"[bold green]{translator.get('Security type updated to')} {new_security_type}[/]")
        
        if new_security_type == "basic_auth":
            # Basic auth handling
            htpasswd_option = prompt_htpasswd_option(translator)
            
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
                
                display_waiting_for_htpasswd(htpasswd_file_path, translator)
                
                # Wait for the .htpasswd to appear - user cannot proceed without it
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
                    if confirm_change_security_method(translator):
                        # Switch to no security
                        nginx_config["security"]["type"] = "none"
                        console.print(f"[bold cyan]{translator.get('Switching to no additional security mode...')}[/]")
                        return
            else:
                console.print(f"[bold green]{translator.get('.htpasswd file found and ready to use.')}[/]")
            
        elif new_security_type == "client_cert":
            # Client certificate handling
            cert_source = prompt_client_cert_source(translator)
            
            if cert_source.startswith(translator.get("Generate")):
                client_name = prompt_client_cert_name(translator)
                # Generate certificate with client_cert_manager
                success, cert_info = client_cert_manager.generate_client_certificate(client_name)            
                if success and cert_info:
                    console.print(f"[bold green]{translator.get('Client certificate successfully created and saved to config.')}[/]")
                else:
                    console.print(f"[bold red]{translator.get('Failed to create client certificate. Please try again.')}[/]")
    
    # Note to user about IP restrictions being in a separate menu
    console.print(f"[bold cyan]{translator.get('IP address restrictions can be configured in the dedicated menu option.')}[/]")
    
    return config

def modify_ip_restrictions(config, translator, security_managers):
    """
    Modify IP address restrictions for nginx mode.
    
    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        security_managers: Dictionary containing the security module managers
        
    Returns:
        dict: The updated configuration dictionary
    """
    nginx_config = config["nginx"]
    current_ip_restrictions = nginx_config["security"].get("allowed_ips", [])
    
    console.print(f"[bold cyan]{translator.get('Configure IP Address Filtering')}[/]")
    
    if current_ip_restrictions:
        console.print(f"[bold cyan]{translator.get('Current allowed IPs')}: {', '.join(current_ip_restrictions)}[/]")
    else:
        console.print(f"[bold cyan]{translator.get('No IP restrictions currently active')}[/]")
    
    # Handle IP restrictions
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
    
    domain = prompt_for_domain(current_domain, translator)
    
    if domain != current_domain:
        nginx_config["domain"] = domain
        console.print(f"[bold green]{translator.get('Domain name updated to')} {domain}[/]")
        
        # Check if domain is suitable for Let's Encrypt if that's the current mode
        if nginx_config["https_mode"] == "letsencrypt":
            needs_switch = not check_domain_suitable_for_letsencrypt(
                domain, 
                translator, 
                nginx_config["https_mode"]
            )
            
            if needs_switch:
                nginx_config["https_mode"] = "self_signed"
                console.print(f"[bold green]{translator.get('HTTPS mode updated to self-signed certificates.')}[/]")
    else:
        console.print(f"[bold cyan]{translator.get('Domain name unchanged.')}[/]")
    
    return config

def configure_auth_bypass_ips(config, translator, security_managers):
    """
    Configure IP addresses that can bypass basic authentication.
    Only applies when using basic auth security type.
    
    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        security_managers: Dictionary containing the security module managers
        
    Returns:
        dict: The updated configuration dictionary
    """
    nginx_config = config["nginx"]
    
    # Check if basic auth is enabled
    if nginx_config["security"]["type"] != "basic_auth":
        console.print(f"[bold yellow]{translator.get('Basic auth bypass IPs can only be configured when basic authentication is enabled.')}[/]")
        return config
    
    # Import the AuthBypassIPManager from ip_restrictions module
    from ..security.ip_restrictions import AuthBypassIPManager
    
    # Create an instance of the AuthBypassIPManager
    auth_bypass_manager = AuthBypassIPManager(translator=translator)
    
    # Use the AuthBypassIPManager to configure the auth bypass IPs
    auth_bypass_manager.configure_auth_bypass_ips(nginx_config)
    
    return config