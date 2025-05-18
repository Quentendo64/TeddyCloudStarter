#!/usr/bin/env python3
"""
Nginx mode configuration for TeddyCloudStarter.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

import questionary

from ..docker.manager import DockerManager
from ..ui.nginx_mode_ui import (
    confirm_change_security_method,
    confirm_continue_anyway,
    display_self_signed_certificate_info,
    display_waiting_for_htpasswd,
    prompt_client_cert_name,
    prompt_client_cert_password,
    prompt_client_cert_source,
    prompt_for_domain,
    prompt_for_fallback_option,
    prompt_for_https_mode,
    prompt_htpasswd_option,
    prompt_security_type,
    select_https_mode_for_modification,
    select_security_type_for_modification,
    prompt_nginx_type,
)
from ..utilities.network import check_domain_resolvable, check_port_available
from ..utilities.validation import ConfigValidator
from ..wizard.ui_helpers import console, custom_style
from ..utilities.logger import logger
from .letsencrypt_helper import (
    check_domain_suitable_for_letsencrypt,
    handle_letsencrypt_setup,
)

_validator = ConfigValidator()


def get_server_certs_path(project_path):
    """Get the path for server certificates."""
    return os.path.join(project_path, "data", "server_certs")


def get_security_path(project_path):
    """Get the path for security files."""
    data_path = os.path.join(project_path, "data")
    return os.path.join(data_path, "security")


def get_htpasswd_path(security_path):
    """Get the path for the .htpasswd file."""
    return os.path.join(security_path, ".htpasswd")


def check_https_prerequisites(https_mode):
    """Check for prerequisites based on HTTPS mode."""
    if https_mode in ("self_signed", "user_provided"):
        try:
            subprocess.run(
                ["openssl", "version"], check=True, capture_output=True, text=True
            )
            return True, ""
        except (subprocess.SubprocessError, FileNotFoundError):
            return (
                False,
                "OpenSSL is not available. Cannot generate or validate certificates.",
            )
    return True, ""


def check_port_prerequisites():
    """Check if required ports are available."""
    port_80_available = check_port_available(80)
    port_443_available = check_port_available(443)

    warnings = []
    if not port_80_available:
        warnings.append("Port 80 appears to be in use. This is required for Nginx.")

    if not port_443_available:
        warnings.append("Port 443 appears to be in use. This is required for Nginx.")

    return port_80_available and port_443_available, warnings


def handle_self_signed_certificates(domain, translator, ca_manager, project_path):
    """Handle self-signed certificate configuration.

    Args:
        domain: Domain name for the certificate
        translator: The translator instance for localization
        ca_manager: Certificate Authority manager
        project_path: Base project path

    Returns:
        tuple: (success, result_mode) where result_mode is the HTTPS mode to use
    """
    server_certs_path = get_server_certs_path(project_path)

    display_self_signed_certificate_info(domain, translator)

    # Check OpenSSL availability
    openssl_available, error_msg = check_https_prerequisites("self_signed")
    if not openssl_available:
        console.print(
            f"[bold red]{translator.get('OpenSSL is not available. Cannot generate self-signed certificate.')}[/]"
        )
        console.print(
            f"[bold yellow]{translator.get('Falling back to custom certificate mode.')}[/]"
        )
        return False, "user_provided"

    success, message = ca_manager.generate_self_signed_certificate(
        server_certs_path, domain, translator
    )

    if not success:
        console.print(
            f"[bold red]{translator.get('Failed to generate self-signed certificate')}: {message}[/]"
        )
        fallback_option = prompt_for_fallback_option(translator)

        if fallback_option == "try_again":
            return False, "retry"
        else:
            console.print(
                f"[bold cyan]{translator.get('Switching to custom certificates mode')}...[/]"
            )
            return False, "user_provided"

    return True, "self_signed"


def wait_for_htpasswd_file(htpasswd_file_path, translator):
    """Wait for the .htpasswd file to be created or for user to cancel.

    Args:
        htpasswd_file_path: Path to the .htpasswd file
        translator: The translator instance for localization

    Returns:
        bool: True if file found, False if user cancelled
    """
    htpasswd_exists = Path(htpasswd_file_path).exists()

    if not htpasswd_exists:
        console.print(
            f"[bold yellow]{translator.get('.htpasswd file not found. You must add it to continue.')}[/]"
        )

        should_return_to_menu = False

        display_waiting_for_htpasswd(htpasswd_file_path, translator)

        while True:
            time.sleep(1)

            try:
                htpasswd_exists = os.path.isfile(htpasswd_file_path)

                if htpasswd_exists:
                    console.print(
                        f"[bold green]{translator.get('.htpasswd file found! Continuing...')}[/]"
                    )
                    break
            except Exception as e:
                console.print(f"[bold red]Error checking files: {str(e)}[/]")

            console.print(
                f"[yellow]{translator.get('Still waiting for .htpasswd file at')}: {htpasswd_file_path}[/]"
            )

            if confirm_change_security_method(translator):
                should_return_to_menu = True
                console.print(
                    f"[bold cyan]{translator.get('Returning to security selection menu...')}[/]"
                )
                break

        if should_return_to_menu:
            return False
    else:
        console.print(
            f"[bold green]{translator.get('.htpasswd file found and ready to use.')}[/]"
        )

    return True


def configure_basic_auth(translator, basic_auth_manager, project_path):
    """Configure basic authentication settings.

    Args:
        translator: The translator instance for localization
        basic_auth_manager: The basic auth manager instance
        project_path: Base project path

    Returns:
        bool: True if configuration succeeded, False otherwise
    """
    security_path = get_security_path(project_path)
    htpasswd_file_path = get_htpasswd_path(security_path)

    Path(security_path).mkdir(parents=True, exist_ok=True)

    htpasswd_option = prompt_htpasswd_option(translator)

    if htpasswd_option == "generate":
        console.print(
            f"[bold cyan]{translator.get('Let\'s create a .htpasswd file with your users and passwords')}.[/]"
        )

        if basic_auth_manager:
            success = basic_auth_manager.generate_htpasswd_file(htpasswd_file_path)
            if success:
                console.print(
                    f"[bold green]{translator.get('.htpasswd file successfully created at')} {htpasswd_file_path}[/]"
                )
            else:
                console.print(
                    f"[bold red]{translator.get('Failed to create .htpasswd file. You may need to create it manually.')}[/]"
                )
        else:
            console.print(
                f"[bold red]{translator.get('Error: Basic auth manager not available. Cannot generate .htpasswd file.')}[/]"
            )
            console.print(
                f"[yellow]{translator.get('Please create the .htpasswd file manually at')} {htpasswd_file_path}[/]"
            )
    else:
        console.print(
            f"[bold cyan]{translator.get('Remember to place your .htpasswd file at')} {htpasswd_file_path}[/]"
        )

    return wait_for_htpasswd_file(htpasswd_file_path, translator)


def configure_client_certificates(translator, client_cert_manager):
    """Configure client certificates.

    Args:
        translator: The translator instance for localization
        client_cert_manager: The client certificate manager instance

    Returns:
        bool: True if configuration succeeded, False otherwise
    """
    cert_source = prompt_client_cert_source(translator)

    if cert_source == "generate":
        client_name = prompt_client_cert_name(translator)
        passout = prompt_client_cert_password(translator)
        success, cert_info = client_cert_manager.generate_client_certificate(
            client_name, passout=passout
        )
        if success and cert_info:
            console.print(
                f"[bold green]{translator.get('Client certificate successfully created and saved to config.')}[/]"
            )
            return True
        else:
            console.print(
                f"[bold red]{translator.get('Failed to create client certificate. Please try again.')}[/]"
            )
            return False

    return True


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
    logger.info("Starting Nginx mode configuration.")
    lets_encrypt_manager = security_managers.get("lets_encrypt_manager")
    ca_manager = security_managers.get("ca_manager")
    client_cert_manager = security_managers.get("client_cert_manager")
    basic_auth_manager = security_managers.get("basic_auth_manager")

    if "nginx" not in config:
        config["nginx"] = {
            "domain": "",
            "https_mode": "",
            "nginx_type": "standard",
            "security": {"type": "", "allowed_ips": [], "auth_bypass_ips": []},
        }
        logger.debug("Initialized nginx config: %s", config["nginx"])

    nginx_config = config["nginx"]
    project_path = config.get("environment", {}).get("path", "")
    if not project_path:
        logger.warning("Project path not set. Using current directory.")
        console.print(
            f"[bold red]{translator.get('Warning')}: {translator.get('Project path not set. Using current directory.')}[/]"
        )
        exit

    nginx_config["nginx_type"] = prompt_nginx_type(translator)
    logger.debug(f"Selected nginx_type: {nginx_config['nginx_type']}")

    # Check for required ports
    ports_available, warnings = check_port_prerequisites()

    for warning in warnings:
        logger.warning(warning)
        console.print(
            f"[bold yellow]{translator.get('Warning')}: {translator.get(warning)}[/]"
        )

    if not ports_available and not confirm_continue_anyway(translator):
        logger.error("Required ports are in use and user chose not to proceed. Exiting setup.")
        import sys

        console.print(
            f"[bold red]{translator.get('Exiting setup. Required ports are in use and user chose not to proceed.')}"
        )
        sys.exit(0)

    # Configure domain
    if not nginx_config["domain"]:
        domain = prompt_for_domain("", translator)
        nginx_config["domain"] = domain
        logger.info(f"Domain set to: {domain}")
    else:
        domain = nginx_config["domain"]
        logger.info(f"Using existing domain: {domain}")

    # Configure HTTPS mode
    if nginx_config.get("https_mode") in [
        "letsencrypt",
        "self_signed",
        "user_provided",
    ]:
        # HTTPS mode already set, skip prompting
        pass
    else:
        while True:
            # Check if domain is resolvable for Let's Encrypt
            # Special case for localhost which should never use Let's Encrypt
            if domain.lower() == "localhost" or domain.lower() == "127.0.0.1":
                domain_resolvable = False
            else:
                domain_resolvable = check_domain_resolvable(domain)

            # Prepare HTTPS mode choices based on domain resolvability
            if domain_resolvable:
                https_choices = [
                    {
                        "id": "letsencrypt",
                        "text": translator.get(
                            "Let's Encrypt (automatic certificates)"
                        ),
                    },
                    {
                        "id": "self_signed",
                        "text": translator.get("Create self-signed certificates"),
                    },
                    {
                        "id": "user_provided",
                        "text": translator.get(
                            "Custom certificates (provide your own)"
                        ),
                    },
                ]
                default_choice = "letsencrypt"
            else:
                https_choices = [
                    {
                        "id": "self_signed",
                        "text": translator.get("Create self-signed certificates"),
                    },
                    {
                        "id": "user_provided",
                        "text": translator.get(
                            "Custom certificates (provide your own)"
                        ),
                    },
                ]
                default_choice = (
                    "self_signed"  # Set default to one that exists in the choices
                )

            logger.debug(f"Prompting for HTTPS mode. Domain resolvable: {domain_resolvable}")
            https_mode_id = prompt_for_https_mode(
                https_choices, default_choice, translator
            )
            nginx_config["https_mode"] = https_mode_id
            logger.info(f"HTTPS mode set to: {https_mode_id}")

            # --- NEW LETS ENCRYPT FLOW ---
            if nginx_config["https_mode"] == "letsencrypt":
                # Save config with letsencrypt
                config["nginx"] = nginx_config
                config["mode"] = "nginx"
                from ..configuration.generator import (
                    generate_docker_compose,
                    generate_nginx_configs,
                )
                from ..configurations import TEMPLATES

                # Regenerate docker-compose.yml
                generate_docker_compose(config, translator, TEMPLATES)
                # Regenerate nginx configs
                generate_nginx_configs(config, translator, TEMPLATES)
                # Create a staging certificate
                docker_manager = DockerManager(translator=translator)
                logger.info("Selected Let's Encrypt mode. Generating configs and requesting certificates.")
                staging_success = (
                    lets_encrypt_manager.create_letsencrypt_certificate_webroot(
                        domain=domain,
                        email=None,
                        sans=None,
                        staging=True,
                        force_renewal=True,
                        project_path=project_path,
                        docker_manager=docker_manager,
                    )
                )
                if staging_success:
                    logger.success("Staging Let's Encrypt certificate created successfully.")
                    # If success, create a production certificate
                    prod_success = (
                        lets_encrypt_manager.create_letsencrypt_certificate_webroot(
                            domain=domain,
                            email=None,
                            sans=None,
                            staging=False,
                            force_renewal=True,
                            project_path=project_path,
                            docker_manager=docker_manager,
                        )
                    )
                    if prod_success:
                        logger.success("Production Let's Encrypt certificate created successfully.")
                        console.print(
                            f"[bold green]{translator.get('Production Let\'s Encrypt certificate successfully created!')}[/]"
                        )
                        break
                    else:
                        logger.error("Failed to create production certificate. Offering self-signed fallback.")
                        console.print(
                            f"[bold red]{translator.get('Failed to create production certificate. Offering self-signed fallback.')}[/]"
                        )
                        fallback = questionary.confirm(
                            translator.get(
                                "Would you like to generate a self-signed certificate instead?"
                            ),
                            default=True,
                            style=custom_style,
                        ).ask()
                        if fallback:
                            nginx_config["https_mode"] = "self_signed"
                            continue
                        else:
                            break
                else:
                    logger.error("Failed to create staging certificate. Offering self-signed fallback.")
                    console.print(
                        f"[bold red]{translator.get('Failed to create staging certificate. Offering self-signed fallback.')}[/]"
                    )
                    fallback = questionary.confirm(
                        translator.get(
                            "Would you like to generate a self-signed certificate instead?"
                        ),
                        default=True,
                        style=custom_style,
                    ).ask()
                    if fallback:
                        nginx_config["https_mode"] = "self_signed"
                        continue
                    else:
                        break
            # --- END LETS ENCRYPT FLOW ---

            # Handle self-signed certificates
            if nginx_config["https_mode"] == "self_signed":
                logger.info("Selected self-signed certificate mode.")
                success, result_mode = handle_self_signed_certificates(
                    domain, translator, ca_manager, project_path
                )

                if not success:
                    logger.warning(f"Self-signed certificate generation failed. Fallback mode: {result_mode}")
                    if result_mode == "retry":
                        continue  # Try again with self-signed
                    else:
                        nginx_config["https_mode"] = (
                            result_mode  # Switch to user_provided
                        )
                        continue

            break

    logger.success("Nginx mode configuration complete.")
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
    ca_manager = security_managers.get("ca_manager")
    client_cert_manager = security_managers.get("client_cert_manager")
    basic_auth_manager = security_managers.get("basic_auth_manager")
    ip_restrictions_manager = security_managers.get("ip_restrictions_manager")

    # Only prompt if not already set
    if nginx_config["security"].get("type") in ["none", "basic_auth", "client_cert"]:
        # Already set, skip prompting
        pass
    else:
        while True:
            security_type_id = prompt_security_type(translator)
            if security_type_id == "none":
                nginx_config["security"]["type"] = "none"
                break
            elif security_type_id == "basic_auth":
                nginx_config["security"]["type"] = "basic_auth"
                if configure_basic_auth(translator, basic_auth_manager, project_path):
                    break
            else:  # client_cert
                nginx_config["security"]["type"] = "client_cert"
                if configure_client_certificates(translator, client_cert_manager):
                    break
    # Only prompt for IP restrictions once
    if not nginx_config.get("ip_restrictions_configured"):
        if ip_restrictions_manager:
            ip_restrictions_manager.configure_ip_restrictions(nginx_config)
        else:
            console.print(
                f"[bold yellow]{translator.get('Warning')}: {translator.get('IP restrictions manager not available')}[/]"
            )
        nginx_config["ip_restrictions_configured"] = True
    return nginx_config


def modify_https_mode(config, translator, security_managers):
    """
    Modify HTTPS mode for nginx mode.

    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        security_managers: Dictionary containing the security module managers
    """
    lets_encrypt_manager = security_managers.get("lets_encrypt_manager")
    ca_manager = security_managers.get("ca_manager")

    nginx_config = config["nginx"]
    current_mode = nginx_config["https_mode"]

    project_path = config.get("environment", {}).get("path", "")
    if not project_path:
        console.print(
            f"[bold red]{translator.get('Warning')}: {translator.get('Project path not set. Using current directory.')}[/]"
        )
        project_path = os.getcwd()

    while True:
        console.print(
            f"[bold cyan]{translator.get('Current HTTPS mode')}: {current_mode}[/]"
        )

        _, new_mode = select_https_mode_for_modification(current_mode, translator)

        if new_mode != current_mode:
            if new_mode == "letsencrypt" and current_mode != "letsencrypt":
                domain = nginx_config.get("domain", "")
                if not domain:
                    console.print(
                        f"[bold yellow]{translator.get('Warning')}: {translator.get('No domain set. Let\'s Encrypt requires a valid domain.')}[/]"
                    )
                    continue

                if not check_domain_suitable_for_letsencrypt(domain, translator):
                    continue

                port_available = check_port_available(80)
                if not port_available:
                    console.print(
                        f"[bold yellow]{translator.get('Warning: Port 80 appears to be in use')}"
                    )
                    console.print(
                        f"[yellow]{translator.get('Let\'s Encrypt requires port 80 to be available for domain verification')}"
                    )

                    use_anyway = questionary.confirm(
                        translator.get(
                            "Would you like to proceed anyway? (Certbot will attempt to bind to port 80)"
                        ),
                        default=False,
                        style=custom_style,
                    ).ask()

                    if not use_anyway:
                        continue

                from .letsencrypt_helper import switch_to_letsencrypt_https_mode

                success = switch_to_letsencrypt_https_mode(
                    config, translator, lets_encrypt_manager
                )
                if not success:
                    nginx_config["https_mode"] = current_mode
                    console.print(
                        f"[bold red]{translator.get('Failed to switch to Let\'s Encrypt. Keeping')} {current_mode} {translator.get('mode')}.[/]"
                    )
                    continue

                console.print(
                    f"[bold cyan]{translator.get('Requesting initial Let\'s Encrypt certificate in standalone mode...')}[/]"
                )
                cert_success = lets_encrypt_manager.request_certificate(
                    domain=domain, mode="standalone", staging=False
                )

                if not cert_success:
                    console.print(
                        f"[bold yellow]{translator.get('Certificate request failed. You may need to try again later.')}[/]"
                    )
            else:
                nginx_config["https_mode"] = new_mode
                console.print(
                    f"[bold green]{translator.get('HTTPS mode updated to')} {new_mode}[/]"
                )

                if new_mode == "letsencrypt":
                    letsencrypt_success = handle_letsencrypt_setup(
                        nginx_config, translator, lets_encrypt_manager
                    )

                    if not letsencrypt_success:
                        nginx_config["https_mode"] = "self_signed"
                        console.print(
                            f"[bold cyan]{translator.get('Switching to self-signed certificates mode')}...[/]"
                        )
                        current_mode = "self_signed"
                        continue

                elif new_mode == "self_signed":
                    domain = nginx_config.get("domain", "")
                if not domain:
                    console.print(
                        f"[bold yellow]{translator.get('Warning')}: {translator.get('No domain set. Using localhost as fallback.')}[/]"
                    )
                    domain = "localhost"
                    nginx_config["domain"] = domain

                server_certs_path = os.path.join(project_path, "data", "server_certs")

                display_self_signed_certificate_info(domain, translator)

                try:
                    subprocess.run(
                        ["openssl", "version"],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                except (subprocess.SubprocessError, FileNotFoundError):
                    console.print(
                        f"[bold red]{translator.get('OpenSSL is not available. Cannot generate self-signed certificate.')}[/]"
                    )
                    console.print(
                        f"[bold yellow]{translator.get('Proceeding with self-signed mode, but you will need to provide certificates manually.')}[/]"
                    )
                    continue

                if ca_manager:
                    success, message = ca_manager.generate_self_signed_certificate(
                        server_certs_path, domain, translator
                    )

                    if success:
                        console.print(
                            f"[bold green]{translator.get('Self-signed certificate successfully generated for')} {domain}[/]"
                        )
                    else:
                        console.print(
                            f"[bold red]{translator.get('Failed to generate self-signed certificate')}: {message}[/]"
                        )
                        console.print(
                            f"[yellow]{translator.get('You will need to manually provide certificates in')} {server_certs_path}[/]"
                        )
                else:
                    console.print(
                        f"[bold red]{translator.get('Certificate Authority manager not available. Cannot generate certificates.')}[/]"
                    )

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
    client_cert_manager = security_managers.get("client_cert_manager")
    basic_auth_manager = security_managers.get("basic_auth_manager")

    nginx_config = config["nginx"]
    current_security_type = nginx_config["security"]["type"]

    project_path = config.get("environment", {}).get("path", "")
    if not project_path:
        console.print(
            f"[bold red]{translator.get('Warning')}: {translator.get('Project path not set. Using current directory.')}[/]"
        )
        project_path = os.getcwd()

    console.print(
        f"[bold cyan]{translator.get('Current security type')}: {current_security_type}[/]"
    )

    new_security_type = select_security_type_for_modification(
        current_security_type, translator
    )

    if new_security_type != current_security_type:
        nginx_config["security"]["type"] = new_security_type
        console.print(
            f"[bold green]{translator.get('Security type updated to')} {new_security_type}[/]"
        )

        if new_security_type == "basic_auth":
            htpasswd_option = prompt_htpasswd_option(translator)

            security_path = get_security_path(project_path)
            htpasswd_file_path = get_htpasswd_path(security_path)

            Path(security_path).mkdir(parents=True, exist_ok=True)

            if htpasswd_option == "generate":
                console.print(
                    f"[bold cyan]{translator.get('Let\'s create a .htpasswd file with your users and passwords')}.[/]"
                )

                if basic_auth_manager:
                    success = basic_auth_manager.generate_htpasswd_file(
                        htpasswd_file_path
                    )
                    if success:
                        console.print(
                            f"[bold green]{translator.get('.htpasswd file successfully created at')} {htpasswd_file_path}[/]"
                        )
                    else:
                        console.print(
                            f"[bold red]{translator.get('Failed to create .htpasswd file. You may need to create it manually.')}[/]"
                        )
                else:
                    console.print(
                        f"[bold red]{translator.get('Error: Basic auth manager not available. Cannot generate .htpasswd file.')}[/]"
                    )
                    console.print(
                        f"[yellow]{translator.get('Please create the .htpasswd file manually at')} {htpasswd_file_path}[/]"
                    )
            else:
                console.print(
                    f"[bold cyan]{translator.get('Remember to place your .htpasswd file at')} {htpasswd_file_path}[/]"
                )

            htpasswd_exists = Path(htpasswd_file_path).exists()

            if not htpasswd_exists:
                console.print(
                    f"[bold yellow]{translator.get('.htpasswd file not found. You must add it to continue.')}[/]"
                )

                display_waiting_for_htpasswd(htpasswd_file_path, translator)

                while True:
                    time.sleep(1)

                    try:
                        htpasswd_exists = os.path.isfile(htpasswd_file_path)

                        if htpasswd_exists:
                            console.print(
                                f"[bold green]{translator.get('.htpasswd file found! Continuing...')}[/]"
                            )
                            break
                    except Exception as e:
                        console.print(f"[bold red]Error checking files: {str(e)}[/]")

                    console.print(
                        f"[yellow]{translator.get('Still waiting for .htpasswd file at')}: {htpasswd_file_path}[/]"
                    )

                    if confirm_change_security_method(translator):
                        nginx_config["security"]["type"] = "none"
                        console.print(
                            f"[bold cyan]{translator.get('Switching to no additional security mode...')}[/]"
                        )
                        return
            else:
                console.print(
                    f"[bold green]{translator.get('.htpasswd file found and ready to use.')}[/]"
                )

        elif new_security_type == "client_cert":
            cert_source = prompt_client_cert_source(translator)

            if cert_source == "generate":
                client_name = prompt_client_cert_name(translator)
                success, cert_info = client_cert_manager.generate_client_certificate(
                    client_name
                )
                if success and cert_info:
                    console.print(
                        f"[bold green]{translator.get('Client certificate successfully created and saved to config.')}[/]"
                    )
                else:
                    console.print(
                        f"[bold red]{translator.get('Failed to create client certificate. Please try again.')}[/]"
                    )

    console.print(
        f"[bold cyan]{translator.get('IP address restrictions can be configured in the dedicated menu option.')}[/]"
    )

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
        console.print(
            f"[bold cyan]{translator.get('Current allowed IPs')}: {', '.join(current_ip_restrictions)}[/]"
        )
    else:
        console.print(
            f"[bold cyan]{translator.get('No IP restrictions currently active')}[/]"
        )

    if security_managers.get("ip_restrictions_manager"):
        security_managers["ip_restrictions_manager"].configure_ip_restrictions(
            nginx_config
        )
    else:
        console.print(
            f"[bold yellow]{translator.get('Warning')}: {translator.get('IP restrictions manager not available')}[/]"
        )

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
    # Import here to avoid circular import
    import questionary

    from ..configurations import TEMPLATES
    from ..docker.manager import DockerManager
    from .generator import generate_nginx_configs

    nginx_config = config["nginx"]
    current_domain = nginx_config.get("domain", "")

    console.print(
        f"[bold cyan]{translator.get('Current domain name')}: {current_domain or translator.get('Not set')}[/]"
    )

    domain = prompt_for_domain(current_domain, translator)

    if domain != current_domain:
        nginx_config["domain"] = domain
        console.print(
            f"[bold green]{translator.get('Domain name updated to')} {domain}[/]"
        )

        if nginx_config["https_mode"] == "letsencrypt":
            needs_switch = not check_domain_suitable_for_letsencrypt(
                domain, translator, nginx_config["https_mode"]
            )

            if needs_switch:
                nginx_config["https_mode"] = "self_signed"
                console.print(
                    f"[bold green]{translator.get('HTTPS mode updated to self-signed certificates.')}[/]"
                )
        # Regenerate nginx configs
        success = generate_nginx_configs(config, translator, TEMPLATES)
        if success:
            console.print(
                f"[bold green]{translator.get('Nginx configuration regenerated successfully.')}[/]"
            )
            # Ask if user wants to restart Docker services
            restart = questionary.confirm(
                translator.get(
                    "Would you like to restart Docker services to apply the new domain?"
                ),
                default=True,
            ).ask()
            if restart:
                # Get project_path if available
                project_path = config.get("environment", {}).get("path", None)
                docker_manager = DockerManager(translator=translator)
                docker_manager.restart_services(project_path=project_path)
        else:
            console.print(
                f"[bold red]{translator.get('Failed to regenerate nginx configuration.')}[/]"
            )
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

    if nginx_config["security"]["type"] != "basic_auth":
        console.print(
            f"[bold yellow]{translator.get('Basic auth bypass IPs can only be configured when basic authentication is enabled.')}[/]"
        )
        return config

    from ..security.ip_restrictions import AuthBypassIPManager

    auth_bypass_manager = AuthBypassIPManager(translator=translator)

    auth_bypass_manager.configure_auth_bypass_ips(nginx_config)

    return config
