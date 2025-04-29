#!/usr/bin/env python3
"""
IP restrictions functionality for TeddyCloudStarter.
Handles configuration and validation of IP restrictions.
"""
import os
import questionary
from pathlib import Path
from rich.console import Console
from typing import List, Optional, Dict

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
        self.custom_style = questionary.Style([
            ('qmark', 'fg:cyan bold'),
            ('question', 'fg:cyan bold'),
            ('answer', 'fg:green bold'),
            ('pointer', 'fg:cyan bold'),
            ('highlighted', 'fg:cyan bold'),
            ('selected', 'fg:cyan bold'),
            ('separator', 'fg:cyan'),
            ('instruction', 'fg:gray'),
            ('text', ''),
            ('disabled', 'fg:gray'),
        ])
    
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
        
        # Show current IP restrictions if any
        if current_ips:
            console.print(f"[bold cyan]{self._translate('Current allowed IPs')}:[/]")
            for ip in current_ips:
                console.print(f"  - {ip}")
        
        # Ask if user wants to restrict access by IP
        restrict_by_ip = questionary.confirm(
            self._translate("Do you want to restrict access by IP address?"),
            default=bool(current_ips),
            style=self.custom_style
        ).ask()
        
        if not restrict_by_ip:
            # Clear any existing IP restrictions
            config["security"]["allowed_ips"] = []
            console.print(f"[bold cyan]{self._translate('IP restrictions disabled.')}[/]")
            return config
        
        # Manage IP restrictions
        new_ips = []
        
        # Add IP addresses
        console.print(f"[bold cyan]{self._translate('Enter IP addresses to allow (leave empty to finish)')}")
        console.print(f"[cyan]{self._translate('You can use individual IPs (e.g., 192.168.1.10) or CIDR notation (e.g., 192.168.1.0/24)')}[/]")
        
        from ..utilities.validation import validate_ip_address
        
        while True:
            ip_address = questionary.text(
                self._translate("Enter IP address or CIDR range (leave empty to finish):"),
                style=self.custom_style,
                validate=lambda ip: validate_ip_address(ip) if ip else True
            ).ask()
            
            if not ip_address:
                if not new_ips:
                    continue_anyway = questionary.confirm(
                        self._translate("No IP addresses added. This will allow all IPs. Continue?"),
                        default=False,
                        style=self.custom_style
                    ).ask()
                    
                    if continue_anyway:
                        break
                    else:
                        continue
                else:
                    break
            
            # Add the IP if not already in the list
            if ip_address not in new_ips:
                new_ips.append(ip_address)
                console.print(f"[green]{self._translate('Added IP')} {ip_address}[/]")
            else:
                console.print(f"[yellow]{self._translate('IP already in list, skipping')} {ip_address}[/]")
        
        # Update the config
        config["security"]["allowed_ips"] = new_ips
        
        if new_ips:
            console.print(f"[bold green]{self._translate('IP restrictions enabled for')} {len(new_ips)} {self._translate('addresses')}.[/]")
        else:
            console.print(f"[bold cyan]{self._translate('IP restrictions disabled.')}[/]")
            
        return config
    
    def validate_ip_restrictions(self, config: Dict) -> bool:
        """
        Validate that IP restrictions in the config are properly formatted.
        
        Args:
            config: Configuration dictionary containing security settings
            
        Returns:
            bool: True if restrictions are valid, False otherwise
        """
        from ..utilities.validation import validate_ip_address
        
        # Check if IP restrictions exist
        if "security" not in config or "allowed_ips" not in config["security"]:
            return True  # No restrictions to validate
            
        ip_list = config["security"]["allowed_ips"]
        if not ip_list:
            return True  # Empty list is valid (no restrictions)
            
        # Validate each IP address
        for ip in ip_list:
            if not validate_ip_address(ip):
                console.print(f"[bold red]{self._translate('Invalid IP address or CIDR range')}: {ip}[/]")
                return False
                
        return True
