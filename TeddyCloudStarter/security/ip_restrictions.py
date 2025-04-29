#!/usr/bin/env python3
"""
IP restrictions functionality for TeddyCloudStarter.
Handles configuration and validation of IP restrictions.
"""
import os
from pathlib import Path
from rich.console import Console
from typing import List, Optional, Dict
import questionary
from ..ui.ip_restrictions_ui import (
    display_current_ip_restrictions,
    confirm_restrict_by_ip,
    display_ip_input_instructions,
    prompt_for_ip_address,
    confirm_no_ips_continue,
    display_ip_added,
    display_ip_already_exists,
    display_ip_restrictions_status,
    display_invalid_ip_error,
    prompt_ip_management_action,
    select_ip_to_remove,
    confirm_clear_ip_restrictions,
    # Auth bypass specific UI functions
    display_current_auth_bypass_ips,
    confirm_enable_auth_bypass,
    display_auth_bypass_input_instructions,
    prompt_for_auth_bypass_ip,
    display_auth_bypass_status,
    confirm_clear_auth_bypass_ips,
    prompt_auth_bypass_management_action
)
from ..utilities.validation import validate_ip_address

# Re-export console to ensure compatibility
console = Console()

class IPRestrictionsManager:
    """
    Manages IP address restrictions for TeddyCloudStarter.
    Provides functionality to configure and validate IP restrictions.
    """
    
    def __init__(self, translator=None, base_dir=None):
        """
        Initialize the IP restrictions manager.
        
        Args:
            translator: Optional translator instance for localization
            base_dir: Optional base directory of the project
        """
        self.translator = translator
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
    
    def _translate(self, text: str) -> str:
        """
        Helper method to translate text if translator is available.
        
        Args:
            text: The text to translate
            
        Returns:
            str: Translated text if translator is available, otherwise original text
        """
        if self.translator:
            return self.translator.get(text)
        return text
    
    def configure_ip_restrictions(self, config: Dict) -> Dict:
        """
        Configure IP restrictions for service access.
        
        Args:
            config: Configuration dictionary containing security settings
            
        Returns:
            Dict: Updated configuration dictionary with IP restrictions
        """
        # Initialize allowed IPs list if it doesn't exist
        if "security" not in config:
            config["security"] = {}
        
        if "allowed_ips" not in config["security"]:
            config["security"]["allowed_ips"] = []
        
        # Get current allowed IPs
        current_ips = config["security"]["allowed_ips"]
        
        # Ask if user wants to restrict access by IP
        restrict_by_ip = confirm_restrict_by_ip(bool(current_ips), self.translator)
        
        if not restrict_by_ip:
            # Clear any existing IP restrictions
            config["security"]["allowed_ips"] = []
            display_ip_restrictions_status(0, self.translator, False)
            return config
            
        # Create a working copy of IPs
        working_ips = current_ips.copy()
        
        # Display current IP restrictions
        display_current_ip_restrictions(working_ips, self.translator)
        
        # Enter IP management menu loop
        while True:
            action = prompt_ip_management_action(self.translator)
            
            if action == self._translate("Show current IP restrictions"):
                display_current_ip_restrictions(working_ips, self.translator)
                
            elif action == self._translate("Add IP address"):
                self._add_ip_address(working_ips)
                
            elif action == self._translate("Remove IP address"):
                self._remove_ip_address(working_ips)
                
            elif action == self._translate("Clear all IP restrictions"):
                if confirm_clear_ip_restrictions(self.translator):
                    working_ips = []
                    console.print(f"[bold yellow]{self._translate('All IP restrictions cleared')}[/]")
                
            elif action == self._translate("Save and return"):
                # Update the config with our working copy
                config["security"]["allowed_ips"] = working_ips
                
                # Check if user didn't specify any IPs, warn that this will allow all
                if not working_ips and not confirm_no_ips_continue(self.translator):
                    # User chose not to continue, restart the loop
                    continue
                
                display_ip_restrictions_status(len(working_ips), self.translator, bool(working_ips))
                break
        
        return config
    
    def _add_ip_address(self, ip_list: List[str]) -> None:
        """
        Add an IP address to the list.
        
        Args:
            ip_list: List of allowed IPs to modify
        """
        display_ip_input_instructions(self.translator)
        
        while True:
            ip_address = prompt_for_ip_address(self.translator)
            
            if not ip_address:
                break
                
            # Validate the IP address
            if not validate_ip_address(ip_address):
                display_invalid_ip_error(ip_address, self.translator)
                continue
            
            # Add the IP if not already in the list
            if ip_address not in ip_list:
                ip_list.append(ip_address)
                display_ip_added(ip_address, self.translator)
            else:
                display_ip_already_exists(ip_address, self.translator)
    
    def _remove_ip_address(self, ip_list: List[str]) -> None:
        """
        Remove an IP address from the list.
        
        Args:
            ip_list: List of allowed IPs to modify
        """
        selected_ip = select_ip_to_remove(ip_list, self.translator)
        
        if selected_ip:
            ip_list.remove(selected_ip)
            console.print(f"[yellow]{self._translate('Removed IP')} {selected_ip}[/]")
    
    def validate_ip_restrictions(self, config: Dict) -> bool:
        """
        Validate that IP restrictions in the config are properly formatted.
        
        Args:
            config: Configuration dictionary containing security settings
            
        Returns:
            bool: True if restrictions are valid, False otherwise
        """
        # Check if IP restrictions exist
        if "security" not in config or "allowed_ips" not in config["security"]:
            return True  # No restrictions to validate
            
        ip_list = config["security"]["allowed_ips"]
        if not ip_list:
            return True  # Empty list is valid (no restrictions)
            
        # Validate each IP address
        for ip in ip_list:
            if not validate_ip_address(ip):
                display_invalid_ip_error(ip, self.translator)
                return False
                
        return True

class AuthBypassIPManager:
    """
    Manages authentication bypass IP addresses for TeddyCloudStarter.
    Provides functionality to configure which IPs can bypass basic authentication.
    """
    
    def __init__(self, translator=None, base_dir=None):
        """
        Initialize the auth bypass IP manager.
        
        Args:
            translator: Optional translator instance for localization
            base_dir: Optional base directory of the project
        """
        self.translator = translator
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        # Import here to avoid circular imports
        from ..wizard.ui_helpers import custom_style
        self.custom_style = custom_style
    
    def _translate(self, text: str) -> str:
        """
        Helper method to translate text if translator is available.
        
        Args:
            text: The text to translate
            
        Returns:
            str: Translated text if translator is available, otherwise original text
        """
        if self.translator:
            return self.translator.get(text)
        return text
    
    def configure_auth_bypass_ips(self, config: Dict) -> Dict:
        """
        Configure IP addresses that can bypass basic authentication.
        
        Args:
            config: Configuration dictionary containing security settings
            
        Returns:
            Dict: Updated configuration dictionary with auth bypass IPs
        """
        # Initialize auth bypass IPs list if it doesn't exist
        if "security" not in config:
            config["security"] = {}
        
        if "auth_bypass_ips" not in config["security"]:
            config["security"]["auth_bypass_ips"] = []
        
        # Get current bypass IPs
        current_ips = config["security"]["auth_bypass_ips"]
        
        # Ask if user wants to enable auth bypass by IP
        enable_bypass = confirm_enable_auth_bypass(bool(current_ips), self.translator)
        
        if not enable_bypass:
            # Clear any existing bypass IPs
            config["security"]["auth_bypass_ips"] = []
            display_auth_bypass_status(0, self.translator, False)
            return config
            
        # Create a working copy of IPs
        working_ips = current_ips.copy()
        
        # Display current bypass IPs
        display_current_auth_bypass_ips(working_ips, self.translator)
        
        # Enter IP management menu loop
        while True:
            action = prompt_auth_bypass_management_action(self.translator)
            
            if action == self._translate("Show current bypass IPs"):
                display_current_auth_bypass_ips(working_ips, self.translator)
                
            elif action == self._translate("Add bypass IP address"):
                self._add_bypass_ip(working_ips)
                
            elif action == self._translate("Remove bypass IP address"):
                self._remove_bypass_ip(working_ips)
                
            elif action == self._translate("Clear all bypass IPs"):
                if confirm_clear_auth_bypass_ips(self.translator):
                    working_ips = []
                    console.print(f"[bold yellow]{self._translate('All authentication bypass IPs cleared')}[/]")
                
            elif action == self._translate("Save and return"):
                # Update the config with our working copy
                config["security"]["auth_bypass_ips"] = working_ips
                
                display_auth_bypass_status(len(working_ips), self.translator, bool(working_ips))
                break
        
        return config
    
    def _add_bypass_ip(self, ip_list: List[str]) -> None:
        """
        Add an IP address to the bypass list.
        
        Args:
            ip_list: List of bypass IPs to modify
        """
        display_auth_bypass_input_instructions(self.translator)
        
        while True:
            ip_address = prompt_for_auth_bypass_ip(self.translator)
            
            if not ip_address:
                break
                
            # Validate the IP address
            if not validate_ip_address(ip_address):
                display_invalid_ip_error(ip_address, self.translator)
                continue
            
            # Add the IP if not already in the list
            if ip_address not in ip_list:
                ip_list.append(ip_address)
                console.print(f"[green]{self._translate('Added bypass IP')} {ip_address}[/]")
            else:
                console.print(f"[yellow]{self._translate('IP already in bypass list, skipping')} {ip_address}[/]")
    
    def _remove_bypass_ip(self, ip_list: List[str]) -> None:
        """
        Remove an IP address from the bypass list.
        
        Args:
            ip_list: List of bypass IPs to modify
        """
        if not ip_list:
            console.print(f"[yellow]{self._translate('No bypass IPs to remove')}[/]")
            return None
            
        choices = ip_list + [self._translate("Cancel")]
        
        selected = questionary.select(
            self._translate("Select IP address to remove from bypass list"),
            choices=choices,
            style=self.custom_style
        ).ask()
        
        if selected == self._translate("Cancel"):
            return
            
        if selected:
            ip_list.remove(selected)
            console.print(f"[yellow]{self._translate('Removed bypass IP')} {selected}[/]")
