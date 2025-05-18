#!/usr/bin/env python3
"""
UI module for IP restrictions configuration in TeddyCloudStarter.
"""
import questionary

from ..utilities.validation import validate_ip_address
from ..wizard.ui_helpers import console, custom_style
from ..utilities.logger import logger


def display_current_ip_restrictions(ip_list, translator):
    """
    Display current IP restrictions.

    Args:
        ip_list: List of allowed IPs
        translator: The translator instance for localization
    """
    logger.debug(f"Displaying current IP restrictions: {ip_list}")
    if ip_list:
        console.print(f"[bold cyan]{translator.get('Current allowed IPs')}:[/]")
        for ip in ip_list:
            console.print(f"  - {ip}")
    else:
        logger.info("No current IP restrictions to display.")


def confirm_restrict_by_ip(has_current_restrictions, translator):
    """
    Ask user if they want to restrict access by IP address.

    Args:
        has_current_restrictions: Whether there are existing IP restrictions
        translator: The translator instance for localization

    Returns:
        bool: True if user wants to restrict by IP, False otherwise
    """
    logger.debug(f"Prompting user to restrict by IP. Current restrictions: {has_current_restrictions}")
    result = questionary.confirm(
        translator.get("Do you want to restrict access to the Server by IP address?"),
        default=has_current_restrictions,
        style=custom_style,
    ).ask()
    logger.info(f"User chose to restrict by IP: {result}")
    return result


def display_ip_input_instructions(translator):
    """
    Display instructions for entering IP addresses.

    Args:
        translator: The translator instance for localization
    """
    logger.debug("Displaying instructions for entering allowed IP addresses.")
    console.print(
        f"[bold cyan]{translator.get('Enter IP addresses to allow (leave empty to finish)')}"
    )
    console.print(
        f"[cyan]{translator.get('You can use individual IPs (e.g., 192.168.1.10) or CIDR notation (e.g., 192.168.1.0/24)')}[/]"
    )


def prompt_for_ip_address(translator):
    """
    Prompt user to enter an IP address or CIDR range.

    Args:
        translator: The translator instance for localization

    Returns:
        str: The entered IP address or empty string to finish
    """
    logger.debug("Prompting user to enter an IP address or CIDR range.")
    result = questionary.text(
        translator.get("Enter IP address or CIDR range (leave empty to finish):"),
        style=custom_style,
        validate=lambda ip: validate_ip_address(ip) if ip else True,
    ).ask()
    logger.info(f"User entered IP address or CIDR range: {result}")
    return result


def confirm_no_ips_continue(translator):
    """
    Ask user if they want to continue with no IP restrictions.

    Args:
        translator: The translator instance for localization

    Returns:
        bool: True if user wants to continue, False otherwise
    """
    logger.debug("Prompting user to confirm continuation with no IP restrictions.")
    result = questionary.confirm(
        translator.get("No IP addresses added. This will allow all IPs. Continue?"),
        default=False,
        style=custom_style,
    ).ask()
    logger.info(f"User chose to continue with no IP restrictions: {result}")
    return result


def display_ip_added(ip_address, translator):
    """
    Display message that an IP address was added.

    Args:
        ip_address: The added IP address
        translator: The translator instance for localization
    """
    logger.debug(f"Displaying message for added IP address: {ip_address}")
    console.print(f"[green]{translator.get('Added IP')} {ip_address}[/]")


def display_ip_already_exists(ip_address, translator):
    """
    Display message that an IP address already exists in the list.

    Args:
        ip_address: The duplicate IP address
        translator: The translator instance for localization
    """
    logger.debug(f"Displaying message for duplicate IP address: {ip_address}")
    console.print(
        f"[yellow]{translator.get('IP already in list, skipping')} {ip_address}[/]"
    )


def display_ip_restrictions_status(count, translator, enabled=True):
    """
    Display status of IP restrictions.

    Args:
        count: Number of IP addresses in restrictions
        translator: The translator instance for localization
        enabled: Whether restrictions are enabled
    """
    logger.debug(f"Displaying IP restrictions status. Count: {count}, Enabled: {enabled}")
    if enabled and count:
        console.print(
            f"[bold green]{translator.get('IP restrictions enabled for')} {count} {translator.get('addresses')}.[/]"
        )
    else:
        console.print(f"[bold cyan]{translator.get('IP restrictions disabled.')}[/]")


def display_invalid_ip_error(ip_address, translator):
    """
    Display error for invalid IP address.

    Args:
        ip_address: The invalid IP address
        translator: The translator instance for localization
    """
    logger.debug(f"Displaying error for invalid IP address: {ip_address}")
    console.print(
        f"[bold red]{translator.get('Invalid IP address or CIDR range')}: {ip_address}[/]"
    )


def prompt_ip_management_action(translator):
    """
    Display menu for IP address management options.

    Args:
        translator: The translator instance for localization

    Returns:
        str: The selected action identifier ('show', 'add', 'remove', 'clear', or 'save')
    """
    logger.debug("Prompting user for IP management action.")
    choices = [
        {"id": "show", "text": translator.get("Show current IP restrictions")},
        {"id": "add", "text": translator.get("Add IP address")},
        {"id": "remove", "text": translator.get("Remove IP address")},
        {"id": "clear", "text": translator.get("Clear all IP restrictions")},
        {"id": "save", "text": translator.get("Save and return")},
    ]

    choice_texts = [choice["text"] for choice in choices]
    selected_text = questionary.select(
        translator.get("IP Address Filtering Management"),
        choices=choice_texts,
        style=custom_style,
    ).ask()

    for choice in choices:
        if choice["text"] == selected_text:
            logger.info(f"User selected IP management action: {choice['id']}")
            return choice["id"]

    logger.info("User defaulted to 'show' action.")
    return "show"


def select_ip_to_remove(ip_list, translator):
    """
    Prompt user to select an IP address to remove from the list.

    Args:
        ip_list: List of IP addresses to choose from
        translator: The translator instance for localization

    Returns:
        str: The selected IP address or None if canceled
    """
    logger.debug(f"Prompting user to select IP to remove. IP list: {ip_list}")
    if not ip_list:
        console.print(f"[yellow]{translator.get('No IP restrictions to remove')}[/]")
        logger.info("No IP restrictions available to remove.")
        return None

    choices = ip_list + [translator.get("Cancel")]

    selected = questionary.select(
        translator.get("Select IP address to remove"),
        choices=choices,
        style=custom_style,
    ).ask()

    if selected == translator.get("Cancel"):
        logger.info("User canceled IP removal.")
        return None

    logger.info(f"User selected IP to remove: {selected}")
    return selected


def confirm_clear_ip_restrictions(translator):
    """
    Confirm with the user if they want to clear all IP restrictions.

    Args:
        translator: The translator instance for localization

    Returns:
        bool: True if confirmed, False otherwise
    """
    logger.debug("Prompting user to confirm clearing all IP restrictions.")
    result = questionary.confirm(
        translator.get(
            "Are you sure you want to remove all IP restrictions? This will allow access from any IP address."
        ),
        default=False,
        style=custom_style,
    ).ask()
    logger.info(f"User confirmed clearing all IP restrictions: {result}")
    return result


def display_current_auth_bypass_ips(ip_list, translator):
    """
    Display current IPs that bypass basic authentication.

    Args:
        ip_list: List of IPs that bypass auth
        translator: The translator instance for localization
    """
    logger.debug(f"Displaying current auth bypass IPs: {ip_list}")
    if ip_list:
        console.print(
            f"[bold cyan]{translator.get('Current IPs that bypass authentication')}:[/]"
        )
        for ip in ip_list:
            console.print(f"  - {ip}")
    else:
        logger.info("No current auth bypass IPs to display.")


def confirm_enable_auth_bypass(has_current_bypass, translator):
    """
    Ask user if they want to enable IP-based authentication bypass.

    Args:
        has_current_bypass: Whether there are existing bypass IPs
        translator: The translator instance for localization

    Returns:
        bool: True if user wants to enable bypass, False otherwise
    """
    logger.debug(f"Prompting user to enable auth bypass. Current bypass: {has_current_bypass}")
    result = questionary.confirm(
        translator.get("Do you want to enable IP-based authentication bypass?"),
        default=has_current_bypass,
        style=custom_style,
    ).ask()
    logger.info(f"User chose to enable auth bypass: {result}")
    return result


def display_auth_bypass_input_instructions(translator):
    """
    Display instructions for entering IPs that will bypass authentication.

    Args:
        translator: The translator instance for localization
    """
    logger.debug("Displaying instructions for entering auth bypass IPs.")
    console.print(
        f"[bold cyan]{translator.get('Enter IP addresses that will bypass authentication (leave empty to finish)')}"
    )
    console.print(
        f"[cyan]{translator.get('Connections from these IPs will not require username/password')}[/]"
    )


def prompt_for_auth_bypass_ip(translator):
    """
    Prompt user to enter an IP address that will bypass authentication.

    Args:
        translator: The translator instance for localization

    Returns:
        str: The entered IP address or empty string to finish
    """
    logger.debug("Prompting user to enter auth bypass IP address.")
    result = questionary.text(
        translator.get(
            "Enter IP address or CIDR range to bypass auth (leave empty to finish):"
        ),
        style=custom_style,
        validate=lambda ip: validate_ip_address(ip) if ip else True,
    ).ask()
    logger.info(f"User entered auth bypass IP address: {result}")
    return result


def display_auth_bypass_status(count, translator, enabled=True):
    """
    Display status of authentication bypass.

    Args:
        count: Number of IP addresses that can bypass auth
        translator: The translator instance for localization
        enabled: Whether auth bypass is enabled
    """
    logger.debug(f"Displaying auth bypass status. Count: {count}, Enabled: {enabled}")
    if enabled and count:
        console.print(
            f"[bold green]{translator.get('Authentication bypass enabled for')} {count} {translator.get('addresses')}.[/]"
        )
    else:
        console.print(
            f"[bold cyan]{translator.get('No IPs will bypass authentication.')}[/]"
        )


def confirm_clear_auth_bypass_ips(translator):
    """
    Confirm with the user if they want to clear all auth bypass IPs.

    Args:
        translator: The translator instance for localization

    Returns:
        bool: True if confirmed, False otherwise
    """
    logger.debug("Prompting user to confirm clearing all auth bypass IPs.")
    result = questionary.confirm(
        translator.get(
            "Are you sure you want to remove all authentication bypass IPs? This will require authentication for all connections."
        ),
        default=False,
        style=custom_style,
    ).ask()
    logger.info(f"User confirmed clearing all auth bypass IPs: {result}")
    return result


def prompt_auth_bypass_management_action(translator):
    """
    Display menu for auth bypass IP management options.

    Args:
        translator: The translator instance for localization

    Returns:
        str: The selected action identifier ('show', 'add', 'remove', 'clear', or 'save')
    """
    logger.debug("Prompting user for auth bypass management action.")
    choices = [
        {"id": "show", "text": translator.get("Show current bypass IPs")},
        {"id": "add", "text": translator.get("Add bypass IP address")},
        {"id": "remove", "text": translator.get("Remove bypass IP address")},
        {"id": "clear", "text": translator.get("Clear all bypass IPs")},
        {"id": "save", "text": translator.get("Save and return")},
    ]

    choice_texts = [choice["text"] for choice in choices]
    selected_text = questionary.select(
        translator.get("Authentication Bypass IP Management"),
        choices=choice_texts,
        style=custom_style,
    ).ask()

    for choice in choices:
        if choice["text"] == selected_text:
            logger.info(f"User selected auth bypass management action: {choice['id']}")
            return choice["id"]

    logger.info("User defaulted to 'show' action.")
    return "show"
