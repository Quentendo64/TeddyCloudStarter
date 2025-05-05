#!/usr/bin/env python3
"""
Let's Encrypt helper functions for TeddyCloudStarter.
"""

from ..utilities.network import check_domain_resolvable
from ..wizard.ui_helpers import console
from ..utilities.logger import logger


def check_domain_suitable_for_letsencrypt(domain, translator, current_mode=None):
    """
    Check if a domain is suitable for Let's Encrypt (publicly resolvable).

    Args:
        domain: The domain name to check
        translator: The translator instance for localization
        current_mode: The current HTTPS mode (if any)

    Returns:
        bool: True if domain is suitable for Let's Encrypt, False otherwise
    """
    from ..ui.nginx_mode_ui import (
        confirm_switch_to_self_signed,
        display_letsencrypt_not_available_warning,
    )

    logger.info(f"Checking if domain '{domain}' is suitable for Let's Encrypt.")
    domain_resolvable = check_domain_resolvable(domain)
    logger.debug(f"Domain '{domain}' resolvable: {domain_resolvable}")

    if not domain_resolvable:
        logger.warning(f"Domain '{domain}' is not publicly resolvable. Let's Encrypt not available.")
        display_letsencrypt_not_available_warning(domain, translator)

        if current_mode == "letsencrypt":
            logger.info("Current mode is 'letsencrypt'. Asking user to switch to self-signed.")
            return confirm_switch_to_self_signed(translator)

        return False

    logger.success(f"Domain '{domain}' is suitable for Let's Encrypt.")
    return True


def handle_letsencrypt_setup(nginx_config, translator, lets_encrypt_manager):
    """
    Handle Let's Encrypt setup process.

    Args:
        nginx_config: The nginx configuration dictionary
        translator: The translator instance for localization
        lets_encrypt_manager: The Let's Encrypt manager instance

    Returns:
        bool: True if setup was successful, False otherwise
    """
    from ..ui.nginx_mode_ui import (
        confirm_letsencrypt_requirements,
        confirm_test_certificate,
        display_letsencrypt_requirements,
        display_letsencrypt_rate_limit_disclaimer,
    )

    domain = nginx_config.get("domain", "")

    logger.info(f"Starting Let's Encrypt setup for domain: {domain}")
    if not domain:
        logger.error("No domain specified for Let's Encrypt.")
        console.print(
            f"[bold red]{translator.get('Error: No domain specified for Let\'s Encrypt')}[/]"
        )
        return False

    # Check if domain is publicly resolvable
    if not check_domain_suitable_for_letsencrypt(
        domain, translator, nginx_config["https_mode"]
    ):
        logger.warning(f"Domain '{domain}' is not suitable for Let's Encrypt. Aborting setup.")
        return False

    # Display Let's Encrypt requirements
    logger.info("Displaying Let's Encrypt requirements and rate limit disclaimer.")
    display_letsencrypt_requirements(translator)
    display_letsencrypt_rate_limit_disclaimer(translator)

    # Confirm the user meets the requirements
    if not confirm_letsencrypt_requirements(translator):
        logger.warning("User did not confirm Let's Encrypt requirements.")
        console.print(
            f"[bold yellow]{translator.get('Let\'s Encrypt requires these prerequisites to function properly.')}[/]"
        )
        return False

    # Ask if the user wants to test if Let's Encrypt can issue a certificate
    if confirm_test_certificate(translator):
        logger.info("User requested Let's Encrypt test certificate.")
        console.print(
            f"[bold cyan]{translator.get('Testing Let\'s Encrypt certificate request in staging environment...')}[/]"
        )

        # Test certificate request
        if lets_encrypt_manager:
            logger.debug("Testing certificate request with Let's Encrypt manager.")
            success = lets_encrypt_manager.test_certificate_request(domain)

            if success:
                logger.success("Let's Encrypt test successful. Domain is properly configured.")
                console.print(
                    f"[bold green]{translator.get('Let\'s Encrypt test successful! Your domain is properly configured.')}[/]"
                )
                return True
            else:
                logger.error("Let's Encrypt test failed. Domain may not be properly configured.")
                console.print(
                    f"[bold red]{translator.get('Let\'s Encrypt test failed. Your domain may not be properly configured.')}[/]"
                )
                console.print(
                    f"[yellow]{translator.get('Switching to self-signed certificates as a fallback.')}[/]"
                )
                return False

        else:
            logger.warning("Let's Encrypt manager not available. Skipping test.")
            console.print(
                f"[bold yellow]{translator.get('Let\'s Encrypt manager not available. Skipping test.')}[/]"
            )

    logger.success("Let's Encrypt setup completed successfully.")
    return True


def switch_to_letsencrypt_https_mode(config, translator, lets_encrypt_manager):
    """
    Switch from another HTTPS mode to Let's Encrypt mode.

    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        lets_encrypt_manager: The Let's Encrypt manager instance

    Returns:
        bool: True if switch was successful, False otherwise
    """
    nginx_config = config["nginx"]
    domain = nginx_config.get("domain", "")

    logger.info(f"Switching HTTPS mode to Let's Encrypt for domain: {domain}")
    if not domain:
        logger.error("No domain specified for Let's Encrypt.")
        console.print(
            f"[bold red]{translator.get('Error: No domain specified for Let\'s Encrypt')}[/]"
        )
        return False

    # The actual switch is just changing the config value, but we need to ensure prerequisites are met
    result = handle_letsencrypt_setup(nginx_config, translator, lets_encrypt_manager)

    if result:
        nginx_config["https_mode"] = "letsencrypt"
        logger.success("HTTPS mode successfully switched to Let's Encrypt.")
        console.print(
            f"[bold green]{translator.get('HTTPS mode successfully switched to Let\'s Encrypt')}[/]"
        )

        # Configure certbot settings
        if lets_encrypt_manager:
            logger.debug("Configuring certbot settings via Let's Encrypt manager.")
            lets_encrypt_manager.configure_certbot_settings(config)

        return True

    logger.warning("Failed to switch HTTPS mode to Let's Encrypt.")
    return False
