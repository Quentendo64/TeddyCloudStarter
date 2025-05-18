#!/usr/bin/env python3
"""
UI module for Direct mode configuration in TeddyCloudStarter.
"""
import questionary

from ..wizard.ui_helpers import console, custom_style
from ..utilities.logger import logger


def confirm_use_http(default_value, translator):
    """
    Ask user if they want to expose the admin interface on HTTP.

    Args:
        default_value: Default choice
        translator: The translator instance for localization

    Returns:
        bool: True if confirmed, False otherwise
    """
    logger.debug(f"Prompting user to expose admin interface on HTTP. Default: {default_value}")
    result = questionary.confirm(
        translator.get(
            "Would you like to expose the TeddyCloud Admin Web Interface on HTTP (port 80)?"
        ),
        default=default_value,
        style=custom_style,
    ).ask()
    logger.info(f"User chose to expose HTTP: {result}")
    return result


def confirm_custom_http_port(translator):
    """
    Ask user if they want to specify a different HTTP port.

    Args:
        translator: The translator instance for localization

    Returns:
        bool: True if confirmed, False otherwise
    """
    logger.debug("Prompting user to specify a different HTTP port.")
    result = questionary.confirm(
        translator.get("Would you like to specify a different port?"),
        default=True,
        style=custom_style,
    ).ask()
    logger.info(f"User chose custom HTTP port: {result}")
    return result


def prompt_for_http_port(default_port, translator):
    """
    Prompt user to enter HTTP port.

    Args:
        default_port: Default port value
        translator: The translator instance for localization

    Returns:
        str: The entered port
    """
    logger.debug(f"Prompting user to enter HTTP port. Default: {default_port}")
    result = questionary.text(
        translator.get("Enter HTTP port:"),
        default=default_port,
        validate=lambda p: p.isdigit() and 1 <= int(p) <= 65535,
        style=custom_style,
    ).ask()
    logger.info(f"User entered HTTP port: {result}")
    return result


def confirm_use_https(default_value, translator):
    """
    Ask user if they want to expose the admin interface on HTTPS.

    Args:
        default_value: Default choice
        translator: The translator instance for localization

    Returns:
        bool: True if confirmed, False otherwise
    """
    logger.debug(f"Prompting user to expose admin interface on HTTPS. Default: {default_value}")
    result = questionary.confirm(
        translator.get(
            "Would you like to expose the TeddyCloud Admin Web Interface on HTTPS (port 8443)?"
        ),
        default=default_value,
        style=custom_style,
    ).ask()
    logger.info(f"User chose to expose HTTPS: {result}")
    return result


def confirm_custom_https_port(translator):
    """
    Ask user if they want to specify a different HTTPS port.

    Args:
        translator: The translator instance for localization

    Returns:
        bool: True if confirmed, False otherwise
    """
    logger.debug("Prompting user to specify a different HTTPS port.")
    result = questionary.confirm(
        translator.get("Would you like to specify a different port?"),
        default=True,
        style=custom_style,
    ).ask()
    logger.info(f"User chose custom HTTPS port: {result}")
    return result


def prompt_for_https_port(default_port, translator):
    """
    Prompt user to enter HTTPS port.

    Args:
        default_port: Default port value
        translator: The translator instance for localization

    Returns:
        str: The entered port
    """
    logger.debug(f"Prompting user to enter HTTPS port. Default: {default_port}")
    result = questionary.text(
        translator.get("Enter HTTPS port:"),
        default=default_port,
        validate=lambda p: p.isdigit() and 1 <= int(p) <= 65535,
        style=custom_style,
    ).ask()
    logger.info(f"User entered HTTPS port: {result}")
    return result


def confirm_custom_teddycloud_port(translator):
    """
    Ask user if they want to specify a different port for TeddyCloud backend.

    Args:
        translator: The translator instance for localization

    Returns:
        bool: True if confirmed, False otherwise
    """
    logger.debug("Prompting user to specify a different TeddyCloud backend port.")
    result = questionary.confirm(
        translator.get(
            "Would you like to specify a different port for TeddyCloud backend (normally 443)?"
        ),
        default=True,
        style=custom_style,
    ).ask()
    logger.info(f"User chose custom TeddyCloud backend port: {result}")
    return result


def prompt_for_teddycloud_port(default_port, translator):
    """
    Prompt user to enter TeddyCloud backend port.

    Args:
        default_port: Default port value
        translator: The translator instance for localization

    Returns:
        str: The entered port
    """
    logger.debug(f"Prompting user to enter TeddyCloud backend port. Default: {default_port}")
    result = questionary.text(
        translator.get("Enter TeddyCloud backend port:"),
        default=default_port,
        validate=lambda p: p.isdigit() and 1 <= int(p) <= 65535,
        style=custom_style,
    ).ask()
    logger.info(f"User entered TeddyCloud backend port: {result}")
    return result


def confirm_port_usage_anyway(port, translator):
    """
    Ask user if they want to use a port that appears to be in use.

    Args:
        port: The port number
        translator: The translator instance for localization

    Returns:
        bool: True if confirmed, False otherwise
    """
    logger.debug(f"Prompting user to use port that appears in use: {port}")
    console.print(
        f"[bold yellow]{translator.get('Warning')}: {translator.get('Port')} {port} {translator.get('appears to be in use')}.[/]"
    )
    result = questionary.confirm(
        translator.get("Would you like to use this port anyway?"),
        default=False,
        style=custom_style,
    ).ask()
    logger.info(f"User chose to use port {port} anyway: {result}")
    return result


def confirm_no_admin_interface(translator):
    """
    Ask user to confirm if they want to continue without admin interface access.

    Args:
        translator: The translator instance for localization

    Returns:
        bool: True if confirmed, False otherwise
    """
    logger.debug("Prompting user to confirm no admin interface exposed.")
    console.print(
        f"[bold red]{translator.get('Warning')}: {translator.get('You have not exposed any ports for the admin interface')}.[/]"
    )
    result = questionary.confirm(
        translator.get(
            "Are you sure you want to continue without access to the admin interface?"
        ),
        default=False,
        style=custom_style,
    ).ask()
    logger.info(f"User confirmed no admin interface: {result}")
    return result
