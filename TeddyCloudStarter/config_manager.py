#!/usr/bin/env python3
"""
Configuration management for TeddyCloudStarter.
"""
import os
import json
import time
import shutil
from typing import Dict, Any
from rich.console import Console

# Global console instance for rich output
console = Console()

# Constants
DEFAULT_CONFIG_PATH = "config.json"


class ConfigManager:
    """Manages the configuration for TeddyCloudStarter."""
    
    def __init__(self, config_path=DEFAULT_CONFIG_PATH, translator=None):
        self.config_path = config_path
        self.translator = translator  # Store translator instance
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or return defaults.
        
        Returns:
            Dict[str, Any]: The configuration dictionary
        """
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                error_msg = "Error loading config file. Using defaults."
                if self.translator:
                    error_msg = self.translator.get(error_msg)
                console.print(f"[bold red]{error_msg}[/]")
        
        return {
            "version": "1.0.0",
            "mode": "direct", 
            "ports": {
                "admin_http": 80,
                "admin_https": 8443,
                "teddycloud": 443
            },
            "nginx": {
                "domain": "",
                "https_mode": "custom",
                "security": {
                    "type": "none",
                    "allowed_ips": []
                }
            },
            "language": ""
        }
    
    def save(self):
        """Save current configuration to file."""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
        
        save_msg = f"Configuration saved to {self.config_path}"
        if self.translator:
            save_msg = self.translator.get(save_msg) 
        console.print(f"[bold green]{save_msg}[/]")
    
    def backup(self):
        """Create a backup of the current configuration."""
        if os.path.exists(self.config_path):
            # Ensure backup directory exists
            backup_dir = os.path.join("data", "backup")
            os.makedirs(backup_dir, exist_ok=True)
            
            # Create backup filename with timestamp
            backup_filename = f"config.json.backup.{int(time.time())}"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # Copy the configuration file to the backup location
            shutil.copy2(self.config_path, backup_path)
            
            backup_msg = f"Backup created at {backup_path}"
            if self.translator:
                backup_msg = self.translator.get("Backup created at {path}").format(path=backup_path)
            console.print(f"[bold green]{backup_msg}[/]")
    
    def delete(self):
        """Delete the configuration file."""
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
            
            delete_msg = f"Configuration file {self.config_path} deleted"
            if self.translator:
                delete_msg = self.translator.get("Configuration file {path} deleted").format(path=self.config_path)
            console.print(f"[bold red]{delete_msg}[/]")
            
            self.config = self._load_config()