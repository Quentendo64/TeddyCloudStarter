#!/usr/bin/env python3
"""
Configuration management for TeddyCloudStarter.
"""
import os
import json
import time
import shutil
import datetime
from typing import Dict, Any, Optional
from rich.console import Console
from pathlib import Path
from . import __version__ 
console = Console()

DEFAULT_CONFIG_PATH = os.path.join(str(Path.home()), ".teddycloudstarter", "config.json")


class ConfigManager:
    """Manages the configuration for TeddyCloudStarter."""
    
    def __init__(self, config_path=DEFAULT_CONFIG_PATH, translator=None):
        self.config_path = config_path
        self.translator = translator
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

        hostname = os.environ.get('COMPUTERNAME') or os.environ.get('HOSTNAME') or "unknown"
        current_user = os.environ.get('USERNAME') or os.environ.get('USER') or "unknown"
        return {
            "version": __version__,
            "last_modified": datetime.datetime.now().isoformat(),            
            "user_info": {
                "created_by": os.environ.get('USERNAME') or os.environ.get('USER') or "unknown",
            },
            "environment": {
                "type": "development",
                "path":"",
                "hostname": hostname,
                "creation_date": datetime.datetime.now().isoformat()
            },
            "app_settings": {
                "log_level": "info",
                "auto_update": True
            },
            "metadata": {
                "config_version": "1.0",
                "description": "Default TeddyCloudStarter configuration"
            },
            "language": "en"
        }
    
    def save(self):
        """Save current configuration to file."""
        self.config["version"] = __version__
        self.config["last_modified"] = datetime.datetime.now().isoformat()
        if "metadata" not in self.config:
            self.config["metadata"] = {
                "config_version": "1.0",
                "description": "TeddyCloudStarter configuration"
            }
        if "environment" not in self.config:
            hostname = os.environ.get('COMPUTERNAME') or os.environ.get('HOSTNAME') or "unknown"
            self.config["environment"] = {
                "type": "development",
                "hostname": hostname,
                "creation_date": datetime.datetime.now().isoformat()
            }
        if "user_info" not in self.config:
            current_user = os.environ.get('USERNAME') or os.environ.get('USER') or "unknown"
            self.config["user_info"] = {
                "modified_by": current_user
            }
        if "app_settings" not in self.config:
            self.config["app_settings"] = {
                "log_level": "info",
                "auto_update": True
            }
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
        
        save_msg = f"Configuration saved to {self.config_path}"
        if self.translator:
            save_msg = self.translator.get(save_msg) 
        console.print(f"[bold green]{save_msg}[/]")
    
    def backup(self):
        """Create a backup of the current configuration."""
        if os.path.exists(self.config_path):
            # Create backup filename with timestamp
            backup_filename = f"config.json.backup.{int(time.time())}"
            
            # Use the same directory as the config file for the backup
            backup_path = f"{self.config_path}.backup.{int(time.time())}"
            
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
    
    @staticmethod
    def get_auto_update_setting(config_path=DEFAULT_CONFIG_PATH):
        """
        Get the auto_update setting from the configuration file.
        
        Args:
            config_path: Path to the configuration file. Defaults to DEFAULT_CONFIG_PATH.
            
        Returns:
            bool: True if auto_update is enabled, False otherwise
        """
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    # Check if app_settings and auto_update setting exist
                    if "app_settings" in config and "auto_update" in config["app_settings"]:
                        return config["app_settings"]["auto_update"]
            except (json.JSONDecodeError, KeyError):
                pass
        
        # Default to False if config file doesn't exist or doesn't have the setting
        return False

    def invalidate_client_certificate(self, cert_serial, client_cert_manager=None):
        """Invalidate a client certificate in the configuration.
        
        Args:
            cert_serial: The serial number of the certificate to invalidate
            client_cert_manager: Optional ClientCertificateManager instance for actual revocation
            
        Returns:
            bool: True if successful, False otherwise
        """
        if "security" not in self.config or "client_certificates" not in self.config["security"]:
            error_msg = "No client certificates found in configuration."
            if self.translator:
                error_msg = self.translator.get(error_msg)
            console.print(f"[bold red]{error_msg}[/]")
            return False
        
        certificates = self.config["security"]["client_certificates"]
        cert_found = False
        
        for i, cert in enumerate(certificates):
            if cert.get("serial") == cert_serial:
                cert_found = True
                
                # Check if the certificate is already revoked
                if cert.get("revoked", False):
                    already_revoked_msg = f"Certificate with serial {cert_serial} is already revoked."
                    if self.translator:
                        already_revoked_msg = self.translator.get("Certificate with serial {serial} is already revoked.").format(serial=cert_serial)
                    console.print(f"[bold yellow]{already_revoked_msg}[/]")
                    return True
                
                # If client_cert_manager is provided, properly revoke the certificate
                if client_cert_manager:
                    safe_name = cert.get("safe_name")
                    if safe_name:
                        success, _ = client_cert_manager.revoke_client_certificate(cert_name=safe_name)
                        if not success:
                            # If actual revocation fails, still mark as revoked in config
                            error_msg = f"Certificate revocation process failed, but certificate will be marked as revoked in configuration."
                            if self.translator:
                                error_msg = self.translator.get(error_msg)
                            console.print(f"[bold yellow]{error_msg}[/]")
                
                # Mark certificate as revoked in the configuration
                self.config["security"]["client_certificates"][i]["revoked"] = True
                self.config["security"]["client_certificates"][i]["revocation_date"] = datetime.datetime.now().strftime("%Y-%m-%d")
                self.save()
                
                success_msg = f"Certificate with serial {cert_serial} has been invalidated in configuration."
                if self.translator:
                    success_msg = self.translator.get("Certificate with serial {serial} has been invalidated in configuration.").format(serial=cert_serial)
                console.print(f"[bold green]{success_msg}[/]")
                
                return True
        
        if not cert_found:
            not_found_msg = f"Certificate with serial {cert_serial} not found in configuration."
            if self.translator:
                not_found_msg = self.translator.get("Certificate with serial {serial} not found in configuration.").format(serial=cert_serial)
            console.print(f"[bold red]{not_found_msg}[/]")
            
        return cert_found