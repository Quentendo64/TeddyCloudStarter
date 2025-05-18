#!/usr/bin/env python3
"""
IP restrictions functionality for TeddyCloudStarter.
Handles configuration and validation of IP restrictions.
"""

from rich.console import Console
from ..utilities.logger import logger

from ..ui.ip_restrictions_ui import (  # Auth bypass specific UI functions
    confirm_clear_auth_bypass_ips,
    confirm_clear_ip_restrictions,
    confirm_enable_auth_bypass,
    confirm_no_ips_continue,
    confirm_restrict_by_ip,
    display_auth_bypass_input_instructions,
    display_auth_bypass_status,
    display_current_auth_bypass_ips,
    display_current_ip_restrictions,
    display_ip_added,
    display_ip_already_exists,
    display_ip_input_instructions,
    display_ip_restrictions_status,
    prompt_auth_bypass_management_action,
    prompt_for_auth_bypass_ip,
    prompt_for_ip_address,
    prompt_ip_management_action,
    select_ip_to_remove,
)

# Re-export console to ensure compatibility
console = Console()


class IPRestrictionsManager:
    """Manage IP address restrictions for TeddyCloud."""

    def __init__(self, translator=None):
        """
        Initialize the IP restrictions manager.

        Args:
            translator: The translator instance for localization
        """
        self.translator = translator

    def configure_ip_restrictions(self, nginx_config):
        """
        Configure IP address restrictions for Nginx.

        Args:
            nginx_config: The nginx configuration dictionary
        """
        # Initialize allowed_ips if it doesn't exist
        if "allowed_ips" not in nginx_config["security"]:
            nginx_config["security"]["allowed_ips"] = []

        current_restrictions = nginx_config["security"]["allowed_ips"]

        # Display current IP restrictions
        display_current_ip_restrictions(current_restrictions, self.translator)

        # Ask if user wants IP restrictions
        enable_restrictions = confirm_restrict_by_ip(
            bool(current_restrictions), self.translator
        )

        if enable_restrictions:
            # Use menu-based approach for IP management
            self._manage_ip_restrictions(nginx_config)
        else:
            # Clear any existing restrictions
            nginx_config["security"]["allowed_ips"] = []
            display_ip_restrictions_status(0, self.translator, enabled=False)

    def _manage_ip_restrictions(self, nginx_config):
        """
        Manage IP restrictions with a menu-based interface.

        Args:
            nginx_config: The nginx configuration dictionary
        """
        while True:
            # Get selected action using the identifier-based approach
            action = prompt_ip_management_action(self.translator)

            # Process action based on the returned identifier
            if action == "show":
                display_current_ip_restrictions(
                    nginx_config["security"]["allowed_ips"], self.translator
                )

            elif action == "add":
                self._add_ip_address(nginx_config)

            elif action == "remove":
                self._remove_ip_address(nginx_config)

            elif action == "clear":
                self._clear_ip_restrictions(nginx_config)

            elif action == "save":
                # Save is handled implicitly as we're modifying the dict directly
                display_ip_restrictions_status(
                    len(nginx_config["security"]["allowed_ips"]),
                    self.translator,
                    enabled=bool(nginx_config["security"]["allowed_ips"]),
                )
                break

    def _add_ip_address(self, nginx_config):
        """
        Add IP addresses to the restriction list.

        Args:
            nginx_config: The nginx configuration dictionary
        """
        display_ip_input_instructions(self.translator)

        # Loop to add multiple IP addresses
        adding_ips = True
        while adding_ips:
            ip = prompt_for_ip_address(self.translator)

            if not ip:
                adding_ips = False

                # If no IPs have been added, confirm
                if not nginx_config["security"][
                    "allowed_ips"
                ] and not confirm_no_ips_continue(self.translator):
                    continue
            else:
                # Check if IP is already in the list
                if ip in nginx_config["security"]["allowed_ips"]:
                    display_ip_already_exists(ip, self.translator)
                else:
                    nginx_config["security"]["allowed_ips"].append(ip)
                    display_ip_added(ip, self.translator)

    def _remove_ip_address(self, nginx_config):
        """
        Remove IP addresses from the restriction list.

        Args:
            nginx_config: The nginx configuration dictionary
        """
        ip = select_ip_to_remove(
            nginx_config["security"]["allowed_ips"], self.translator
        )

        if ip:
            nginx_config["security"]["allowed_ips"].remove(ip)
            console.print(f"[yellow]{self.translator.get('Removed IP')} {ip}[/]")

    def _clear_ip_restrictions(self, nginx_config):
        """
        Clear all IP restrictions.

        Args:
            nginx_config: The nginx configuration dictionary
        """
        if confirm_clear_ip_restrictions(self.translator):
            nginx_config["security"]["allowed_ips"] = []
            console.print(
                f"[bold yellow]{self.translator.get('All IP restrictions cleared.')}[/]"
            )


class AuthBypassIPManager:
    """Manage IP addresses that can bypass basic auth."""

    def __init__(self, translator=None):
        """
        Initialize the auth bypass IP manager.

        Args:
            translator: The translator instance for localization
        """
        self.translator = translator

    def configure_auth_bypass_ips(self, nginx_config):
        """
        Configure authentication bypass IP addresses.

        Args:
            nginx_config: The nginx configuration dictionary
        """
        # Initialize auth_bypass_ips if it doesn't exist
        if "auth_bypass_ips" not in nginx_config["security"]:
            nginx_config["security"]["auth_bypass_ips"] = []

        current_bypass_ips = nginx_config["security"]["auth_bypass_ips"]

        # Display current auth bypass IPs
        display_current_auth_bypass_ips(current_bypass_ips, self.translator)

        # Ask if user wants to enable IP-based auth bypass
        enable_bypass = confirm_enable_auth_bypass(
            bool(current_bypass_ips), self.translator
        )

        if enable_bypass:
            # Use menu-based approach for IP management
            self._manage_auth_bypass_ips(nginx_config)
        else:
            # Clear any existing bypass IPs
            nginx_config["security"]["auth_bypass_ips"] = []
            display_auth_bypass_status(0, self.translator, enabled=False)

    def _manage_auth_bypass_ips(self, nginx_config):
        """
        Manage auth bypass IPs with a menu-based interface.

        Args:
            nginx_config: The nginx configuration dictionary
        """
        while True:
            # Get selected action using the identifier-based approach
            action = prompt_auth_bypass_management_action(self.translator)

            # Process action based on the returned identifier
            if action == "show":
                display_current_auth_bypass_ips(
                    nginx_config["security"]["auth_bypass_ips"], self.translator
                )

            elif action == "add":
                self._add_auth_bypass_ip(nginx_config)

            elif action == "remove":
                self._remove_auth_bypass_ip(nginx_config)

            elif action == "clear":
                self._clear_auth_bypass_ips(nginx_config)

            elif action == "save":
                # Save is handled implicitly as we're modifying the dict directly
                display_auth_bypass_status(
                    len(nginx_config["security"]["auth_bypass_ips"]),
                    self.translator,
                    enabled=bool(nginx_config["security"]["auth_bypass_ips"]),
                )
                break

    def _add_auth_bypass_ip(self, nginx_config):
        """
        Add IP addresses to the auth bypass list.

        Args:
            nginx_config: The nginx configuration dictionary
        """
        display_auth_bypass_input_instructions(self.translator)

        # Loop to add multiple IP addresses
        adding_ips = True
        while adding_ips:
            ip = prompt_for_auth_bypass_ip(self.translator)

            if not ip:
                adding_ips = False
            else:
                # Check if IP is already in the list
                if ip in nginx_config["security"]["auth_bypass_ips"]:
                    display_ip_already_exists(ip, self.translator)
                else:
                    nginx_config["security"]["auth_bypass_ips"].append(ip)
                    display_ip_added(ip, self.translator)

    def _remove_auth_bypass_ip(self, nginx_config):
        """
        Remove IP addresses from the auth bypass list.

        Args:
            nginx_config: The nginx configuration dictionary
        """
        logger.debug("Prompting user to select an auth bypass IP to remove.")
        ip = select_ip_to_remove(
            nginx_config["security"]["auth_bypass_ips"], self.translator
        )
        if ip:
            logger.info(f"Removing auth bypass IP: {ip}")
            nginx_config["security"]["auth_bypass_ips"].remove(ip)
            logger.success(f"Removed auth bypass IP: {ip}")
            console.print(f"[yellow]{self.translator.get('Removed IP')} {ip}[/]")
        else:
            logger.debug("No auth bypass IP selected for removal.")

    def _clear_auth_bypass_ips(self, nginx_config):
        """
        Clear all auth bypass IP addresses.

        Args:
            nginx_config: The nginx configuration dictionary
        """
        logger.debug("Prompting user to confirm clearing all auth bypass IPs.")
        if confirm_clear_auth_bypass_ips(self.translator):
            logger.info("Clearing all auth bypass IPs.")
            nginx_config["security"]["auth_bypass_ips"] = []
            logger.success("All authentication bypass IPs cleared.")
            console.print(
                f"[bold yellow]{self.translator.get('All authentication bypass IPs cleared.')}[/]"
            )
        else:
            logger.debug("User cancelled clearing of auth bypass IPs.")
