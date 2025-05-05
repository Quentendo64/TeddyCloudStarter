#!/usr/bin/env python3
"""
Certificate management UI for TeddyCloudStarter.
"""
import re

import questionary

from ..wizard.ui_helpers import console, custom_style
from ..utilities.logger import logger


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
    logger.debug("Entering show_certificate_management_menu.")
    choices = []

    if config["mode"] == "nginx":
        logger.debug("Mode is nginx.")
        if config["nginx"]["https_mode"] == "letsencrypt":
            logger.debug("HTTPS mode is letsencrypt. Adding Let's Encrypt management options.")
            choices.append(
                {
                    "id": "lets_encrypt_management",
                    "text": translator.get("Let's Encrypt Certificate Management"),
                }
            )
            choices.append(
                {
                    "id": "test_domain",
                    "text": translator.get("Test domain for Let's Encrypt"),
                }
            )
        if config["nginx"]["security"]["type"] == "client_cert":
            logger.debug("Security type is client_cert. Adding client certificate options.")
            choices.append(
                {
                    "id": "create_client_cert",
                    "text": translator.get("Create additional client certificate"),
                }
            )
            from ..config_manager import ConfigManager

            config_manager = ConfigManager()
            fresh_config = config_manager.config
            active_certs = []
            if (
                "security" in fresh_config
                and "client_certificates" in fresh_config["security"]
            ):
                active_certs = [
                    cert
                    for cert in fresh_config["security"]["client_certificates"]
                    if not cert.get("revoked", False)
                ]
            logger.debug(f"Active client certificates: {active_certs}")
            if active_certs:
                logger.debug("There are active client certificates. Adding invalidate option.")
                choices.append(
                    {
                        "id": "invalidate_client_cert",
                        "text": translator.get("Invalidate client certificate"),
                    }
                )

    choices.append({"id": "back", "text": translator.get("Back to main menu")})
    logger.debug(f"Menu choices: {choices}")

    choice_texts = [choice["text"] for choice in choices]
    selected_text = questionary.select(
        translator.get("Certificate Management"),
        choices=choice_texts,
        style=custom_style,
    ).ask()
    logger.info(f"User selected: {selected_text}")

    selected_id = "back"
    for choice in choices:
        if choice["text"] == selected_text:
            selected_id = choice["id"]
            break
    logger.debug(f"Selected menu id: {selected_id}")

    if selected_id == "create_client_cert":
        logger.debug("User chose to create client certificate.")
        create_client_certificate(
            translator,
            security_managers["client_cert_manager"],
            config,
            security_managers,
        )
        return False

    elif selected_id == "invalidate_client_cert":
        logger.debug("User chose to invalidate client certificate.")
        invalidate_client_certificate(
            config,
            translator,
            security_managers["client_cert_manager"],
            security_managers,
        )
        return False

    elif selected_id == "lets_encrypt_management":
        logger.debug("User chose Let's Encrypt management.")
        action_id = show_letsencrypt_management_menu(
            config, translator, security_managers["lets_encrypt_manager"]
        )
        logger.debug(f"LetsEncrypt management action selected: {action_id}")

        if action_id == "prod_webroot":
            request_letsencrypt_certificate(
                config,
                translator,
                security_managers["lets_encrypt_manager"],
                staging=False,
                mode="webroot",
            )
        elif action_id == "prod_standalone":
            request_letsencrypt_certificate(
                config,
                translator,
                security_managers["lets_encrypt_manager"],
                staging=False,
                mode="standalone",
            )
        elif action_id == "staging_webroot":
            request_letsencrypt_certificate(
                config,
                translator,
                security_managers["lets_encrypt_manager"],
                staging=True,
                mode="webroot",
            )
        elif action_id == "staging_standalone":
            request_letsencrypt_certificate(
                config,
                translator,
                security_managers["lets_encrypt_manager"],
                staging=True,
                mode="standalone",
            )
        elif action_id == "refresh":
            refresh_letsencrypt_certificates(
                config, translator, security_managers["lets_encrypt_manager"]
            )

        return False

    elif selected_id == "test_domain":
        logger.debug("User chose to test domain for Let's Encrypt.")
        test_domain_for_letsencrypt(
            config, translator, security_managers["lets_encrypt_manager"]
        )
        return False

    logger.debug("User chose to return to main menu.")
    return True


def create_client_certificate(
    translator, client_cert_manager, config=None, security_managers=None
):
    """
    Create a new client certificate.

    Args:
        translator: The translator instance for localization
        client_cert_manager: The client certificate manager instance
        config: The configuration dictionary (optional, for menu navigation)
        security_managers: The security managers dictionary (optional, for menu navigation)
    """
    logger.debug("Entering create_client_certificate.")
    client_name = questionary.text(
        translator.get("Enter a name for the client certificate:"),
        default="TeddyCloudClient",
        validate=lambda text: bool(text.strip()),
        style=custom_style,
    ).ask()
    logger.info(f"User entered client name: {client_name}")

    use_custom_password = questionary.confirm(
        translator.get(
            "Would you like to set a custom password for the certificate bundle (.p12 file)?"
        ),
        default=False,
        style=custom_style,
    ).ask()
    logger.info(f"User chose custom password: {use_custom_password}")

    passout = None
    if use_custom_password:
        passout = questionary.password(
            translator.get("Enter password for the certificate bundle:"),
            validate=lambda text: len(text) >= 4,
            style=custom_style,
        ).ask()
        logger.debug(f"User entered custom password: {'*' * len(passout) if passout else None}")

    success, cert_info = client_cert_manager.generate_client_certificate(
        client_name, passout=passout
    )
    logger.debug(f"Certificate generation result: success={success}, cert_info={cert_info}")

    if success:
        logger.success("Client certificate successfully created.")
        console.print(
            f"[bold green]{translator.get('Client certificate successfully created')}[/]"
        )
        if cert_info and "p12_path" in cert_info:
            logger.info(f"Certificate bundle saved to: {cert_info['p12_path']}")
            console.print(
                f"[green]{translator.get('Certificate bundle (.p12 file) saved to:')} {cert_info['p12_path']}[/]"
            )
            if not use_custom_password and "password" in cert_info:
                logger.info(f"Auto-generated password: {cert_info['password']}")
                console.print(
                    f"[yellow]{translator.get('Auto-generated password:')} {cert_info['password']}[/]"
                )
                console.print(
                    f"[yellow]{translator.get('IMPORTANT: Save this password! It will not be shown again.')}[/]"
                )
    else:
        logger.error("Failed to create client certificate.")
        console.print(
            f"[bold red]{translator.get('Failed to create client certificate.')}[/]"
        )
    # Always return to certificate management menu if context is available
    if config and security_managers:
        logger.debug("Returning to certificate management menu after client certificate creation.")
        show_certificate_management_menu(config, translator, security_managers)


def invalidate_client_certificate(
    config, translator, client_cert_manager, security_managers=None
):
    """
    Revoke a client certificate.

    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        client_cert_manager: The client certificate manager instance
        security_managers: Optional, needed to re-show the menu
    """
    logger.debug("Entering invalidate_client_certificate.")
    from ..config_manager import ConfigManager

    config_manager = ConfigManager()
    fresh_config = config_manager.config

    if (
        "security" not in fresh_config
        or "client_certificates" not in fresh_config["security"]
        or not fresh_config["security"]["client_certificates"]
    ):
        logger.warning("No client certificates found.")
        console.print(
            f"[bold yellow]{translator.get('No client certificates found.')}[/]"
        )
        if security_managers:
            logger.debug("Returning to certificate management menu after no certs found.")
            show_certificate_management_menu(config, translator, security_managers)
        return

    active_certs = [
        cert
        for cert in fresh_config["security"]["client_certificates"]
        if not cert.get("revoked", False)
    ]
    logger.debug(f"Active certificates for invalidation: {active_certs}")

    if not active_certs:
        logger.warning("No active client certificates found to invalidate.")
        console.print(
            f"[bold yellow]{translator.get('No active client certificates found to invalidate.')}[/]"
        )
        if security_managers:
            logger.debug("Returning to certificate management menu after no active certs found.")
            show_certificate_management_menu(config, translator, security_managers)
        return

    cert_choices = [cert["safe_name"] for cert in active_certs]
    cert_choices.append(translator.get("Cancel"))

    selected_cert = questionary.select(
        translator.get("Select certificate to invalidate:"),
        choices=cert_choices,
        style=custom_style,
    ).ask()
    logger.info(f"User selected certificate to invalidate: {selected_cert}")

    if selected_cert == translator.get("Cancel"):
        logger.info("Certificate invalidation canceled by user.")
        console.print(
            f"[bold yellow]{translator.get('Certificate invalidation canceled.')}[/]"
        )
        if security_managers:
            logger.debug("Returning to certificate management menu after cancel.")
            show_certificate_management_menu(config, translator, security_managers)
        return

    cert_name_clean = selected_cert  # safe_name is used directly

    confirm = questionary.confirm(
        translator.get("Are you sure you want to invalidate this certificate?"),
        default=False,
        style=custom_style,
    ).ask()
    logger.info(f"User confirmation to invalidate: {confirm}")
    if not confirm:
        logger.info("Certificate invalidation canceled by user at confirmation.")
        console.print(
            f"[bold yellow]{translator.get('Certificate invalidation canceled.')}[/]"
        )
        if security_managers:
            logger.debug("Returning to certificate management menu after cancel at confirmation.")
            show_certificate_management_menu(config, translator, security_managers)
        return

    console.print(f"[bold cyan]{translator.get('Fully revoking certificate...')}[/]")
    logger.info(f"Revoking certificate: {cert_name_clean}")

    success, _ = client_cert_manager.revoke_client_certificate(
        cert_name=cert_name_clean
    )
    logger.debug(f"Certificate revocation result: {success}")

    if success:
        config_manager.invalidate_client_certificate(cert_name_clean)
        logger.success("Certificate successfully invalidated.")
        console.print(
            f"[bold green]{translator.get('Certificate successfully invalidated.')}[/]"
        )

        # Always refresh docker-compose.yml after revocation
        from ..configuration.generator import generate_docker_compose
        from ..configurations import TEMPLATES

        if generate_docker_compose(fresh_config, translator, TEMPLATES):
            logger.success("Docker Compose configuration regenerated successfully.")
            console.print(
                f"[bold green]{translator.get('Docker Compose configuration regenerated successfully.')}[/]"
            )
        else:
            logger.error("Failed to regenerate Docker Compose configuration.")
            console.print(
                f"[bold red]{translator.get('Failed to regenerate Docker Compose configuration.')}[/]"
            )

        if (
            fresh_config.get("mode") == "nginx"
            and fresh_config.get("nginx", {}).get("security", {}).get("type")
            == "client_cert"
        ):

            logger.info("Regenerating nginx configuration after certificate invalidation.")
            console.print(
                f"[bold cyan]{translator.get('Regenerating nginx configuration...')}[/]"
            )

            from ..configuration.generator import generate_nginx_configs
            from ..configurations import TEMPLATES

            if generate_nginx_configs(fresh_config, translator, TEMPLATES):
                logger.success("Nginx configuration regenerated successfully.")
                console.print(
                    f"[bold green]{translator.get('Nginx configuration regenerated successfully.')}[/]"
                )
                # Use DockerManager to check if nginx-auth is running, passing project_path
                from ..docker.manager import DockerManager

                docker_manager = DockerManager(translator=translator)
                # Get project_path from config
                project_path = config.get("environment", {}).get("path")
                services_status = docker_manager.get_services_status(
                    project_path=project_path
                )
                nginx_auth_running = services_status.get("nginx-auth", {}).get(
                    "state"
                ) == translator.get("Running")
                logger.debug(f"nginx-auth running: {nginx_auth_running}")
                if nginx_auth_running:
                    restart_service = questionary.confirm(
                        translator.get(
                            "Would you like to restart the nginx-auth service to apply the changes?"
                        ),
                        default=True,
                        style=custom_style,
                    ).ask()
                    logger.info(f"User chose to restart nginx-auth: {restart_service}")
                    if restart_service:
                        try:
                            docker_manager.restart_service(
                                "nginx-auth", project_path=project_path
                            )
                            logger.success("nginx-auth service restarted successfully.")
                        except Exception as e:
                            logger.error(f"Failed to restart nginx-auth service: {e}")
                            console.print(
                                f"[bold red]{translator.get('Failed to restart nginx-auth service:')} {e}[/]"
                            )
            else:
                logger.error("Failed to regenerate nginx configuration.")
                console.print(
                    f"[bold red]{translator.get('Failed to regenerate nginx configuration.')}[/]"
                )
    else:
        logger.error("Failed to invalidate certificate.")
        console.print(
            f"[bold red]{translator.get('Failed to invalidate certificate.')}[/]"
        )
    # Always return to certificate management menu if context is available
    if security_managers:
        logger.debug("Returning to certificate management menu after invalidation.")
        show_certificate_management_menu(config, translator, security_managers)


def show_letsencrypt_management_menu(config, translator, lets_encrypt_manager):
    """
    Show Let's Encrypt certificate management submenu.

    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        lets_encrypt_manager: The Let's Encrypt manager instance

    Returns:
        str: The selected action identifier ('prod_webroot', 'prod_standalone',
             'staging_webroot', 'staging_standalone', 'refresh', or 'back')
    """
    logger.debug("Entering show_letsencrypt_management_menu.")
    choices = [
        {
            "id": "prod_webroot",
            "text": translator.get("Request production certificate (webroot mode)"),
        },
        {
            "id": "prod_standalone",
            "text": translator.get("Request production certificate (standalone mode)"),
        },
        {
            "id": "staging_webroot",
            "text": translator.get("Request staging certificate (webroot mode)"),
        },
        {
            "id": "staging_standalone",
            "text": translator.get("Request staging certificate (standalone mode)"),
        },
        {
            "id": "refresh",
            "text": translator.get("Force refresh Let's Encrypt certificates"),
        },
        {"id": "back", "text": translator.get("Back to certificate menu")},
    ]
    logger.debug(f"LetsEncrypt management menu choices: {choices}")

    choice_texts = [choice["text"] for choice in choices]
    selected_text = questionary.select(
        translator.get("Let's Encrypt Certificate Management"),
        choices=choice_texts,
        style=custom_style,
    ).ask()
    logger.info(f"User selected: {selected_text}")

    for choice in choices:
        if choice["text"] == selected_text:
            logger.debug(f"Returning action id: {choice['id']}")
            return choice["id"]

    logger.debug("Returning default action id: back")
    return "back"


def request_letsencrypt_certificate(
    config, translator, lets_encrypt_manager, staging=False, mode="webroot"
):
    """
    Request Let's Encrypt certificate.

    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        lets_encrypt_manager: The Let's Encrypt manager instance
        staging: Whether to use staging environment
        mode: Authentication mode, "webroot" or "standalone"
    """
    logger.debug(f"Entering request_letsencrypt_certificate. staging={staging}, mode={mode}")
    domain = config["nginx"]["domain"]
    logger.debug(f"Domain: {domain}")

    use_email = questionary.confirm(
        translator.get(
            "Would you like to receive email notifications about certificate expiry?"
        ),
        default=True,
        style=custom_style,
    ).ask()
    logger.info(f"User chose to use email: {use_email}")

    email = None
    if use_email:
        email = questionary.text(
            translator.get("Enter your email address:"),
            validate=lambda e: re.match(r"[^@]+@[^@]+\.[^@]+", e) is not None,
            style=custom_style,
        ).ask()
        logger.debug(f"User entered email: {email}")

    additional_domains = []
    add_sans = questionary.confirm(
        translator.get(
            "Would you like to add additional domain names (SANs) to the certificate?"
        ),
        default=False,
        style=custom_style,
    ).ask()
    logger.info(f"User chose to add SANs: {add_sans}")

    if add_sans:
        adding_domains = True
        while adding_domains:
            san = questionary.text(
                translator.get("Enter additional domain name (leave empty to finish):"),
                style=custom_style,
            ).ask()
            logger.debug(f"User entered SAN: {san}")
            if not san:
                adding_domains = False
            else:
                additional_domains.append(san)
                console.print(f"[green]{translator.get('Added domain:')} {san}[/]")

    staging_str = translator.get("staging") if staging else translator.get("production")
    mode_str = mode
    logger.info(f"Requesting {staging_str} certificate using {mode_str} mode for domain {domain}.")
    console.print(
        f"[bold cyan]{translator.get('Requesting')} {staging_str} {translator.get('certificate using')} {mode_str} {translator.get('mode')}...[/]"
    )
    console.print(f"[cyan]{translator.get('Primary domain:')} {domain}[/]")

    if additional_domains:
        logger.info(f"Additional domains: {additional_domains}")
        console.print(
            f"[cyan]{translator.get('Additional domains:')} {', '.join(additional_domains)}[/]"
        )

    if email:
        logger.info(f"Email: {email}")
        console.print(f"[cyan]{translator.get('Email:')} {email}[/]")

    result = lets_encrypt_manager.request_certificate(
        domain=domain,
        mode=mode,
        staging=staging,
        email=email,
        additional_domains=additional_domains,
    )
    logger.debug(f"LetsEncrypt certificate request result: {result}")

    if result:
        cert_type = (
            translator.get("Staging") if staging else translator.get("Production")
        )
        success_msg = f"{cert_type} {translator.get('certificate requested successfully for')} {domain}"
        logger.success(success_msg)
        console.print(f"[bold green]{success_msg}[/]")
    else:
        cert_type = (
            translator.get("staging") if staging else translator.get("production")
        )
        error_msg = f"{translator.get('Failed to request')} {cert_type} {translator.get('certificate')}"
        logger.error(error_msg)
        console.print(f"[bold red]{error_msg}[/]")


def refresh_letsencrypt_certificates(config, translator, lets_encrypt_manager):
    """
    Refresh Let's Encrypt certificates.

    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        lets_encrypt_manager: The Let's Encrypt manager instance
    """
    logger.debug("Entering refresh_letsencrypt_certificates.")
    domain = config["nginx"]["domain"]
    logger.debug(f"Domain: {domain}")

    use_email = questionary.confirm(
        translator.get(
            "Would you like to receive email notifications about certificate expiry?"
        ),
        default=True,
        style=custom_style,
    ).ask()
    logger.info(f"User chose to use email: {use_email}")

    email = None
    if use_email:
        email = questionary.text(
            translator.get("Enter your email address:"),
            validate=lambda e: re.match(r"[^@]+@[^@]+\.[^@]+", e) is not None,
            style=custom_style,
        ).ask()
        logger.debug(f"User entered email: {email}")

    additional_domains = []
    add_sans = questionary.confirm(
        translator.get(
            "Would you like to add additional domain names (SANs) to the certificate?"
        ),
        default=False,
        style=custom_style,
    ).ask()
    logger.info(f"User chose to add SANs: {add_sans}")

    if add_sans:
        adding_domains = True
        while adding_domains:
            san = questionary.text(
                translator.get("Enter additional domain name (leave empty to finish):"),
                style=custom_style,
            ).ask()
            logger.debug(f"User entered SAN: {san}")
            if not san:
                adding_domains = False
            else:
                additional_domains.append(san)
                console.print(f"[green]{translator.get('Added domain:')} {san}[/]")

    result = lets_encrypt_manager.force_refresh_certificates(
        domain=domain, email=email, additional_domains=additional_domains
    )
    logger.debug(f"LetsEncrypt force refresh result: {result}")

    if result:
        logger.success(f"Let's Encrypt certificates refreshed for {domain}")
        console.print(
            f"[bold green]{translator.get('Let\'s Encrypt certificates refreshed for')} {domain}[/]"
        )
    else:
        logger.error(f"Failed to refresh Let's Encrypt certificates for {domain}")
        console.print(
            f"[bold red]{translator.get('Failed to refresh Let\'s Encrypt certificates for')} {domain}[/]"
        )


def test_domain_for_letsencrypt(config, translator, lets_encrypt_manager):
    """
    Test domain for Let's Encrypt.

    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        lets_encrypt_manager: The Let's Encrypt manager instance
    """
    logger.debug("Entering test_domain_for_letsencrypt.")
    domain = config["nginx"]["domain"]
    logger.debug(f"Testing domain: {domain}")
    console.print(
        f"[bold yellow]{translator.get('Testing domain')} {domain} {translator.get('for Let\'s Encrypt...')}[/]"
    )
    result = lets_encrypt_manager.test_domain(domain)
    logger.debug(f"Test domain result: {result}")
    if result:
        logger.success(f"Domain {domain} is properly set up for Let's Encrypt.")
        console.print(
            f"[bold green]{translator.get('Success')}: {translator.get('Domain')} {domain} {translator.get('is properly set up for Let\'s Encrypt')}[/]"
        )
    else:
        logger.warning(f"Domain {domain} may not be properly set up for Let's Encrypt.")
        console.print(
            f"[bold red]{translator.get('Warning')}: {translator.get('Domain')} {domain} {translator.get('may not be properly set up for Let\'s Encrypt')}[/]"
        )
        console.print(
            f"[yellow]{translator.get('Please ensure the domain resolves to this server and ports 80 and 443 are accessible from the internet.')}[/]"
        )
