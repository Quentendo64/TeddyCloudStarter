#!/usr/bin/env python3
"""
Configuration management for TeddyCloudStarter.
"""
import datetime
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict

from rich.console import Console

from . import __version__
from .utilities.logger import logger

console = Console()

DEFAULT_CONFIG_PATH = os.path.join(
    str(Path.home()), ".teddycloudstarter", "config.json"
)


class ConfigManager:
    """Manages the configuration for TeddyCloudStarter."""

    def __init__(self, config_path=DEFAULT_CONFIG_PATH, translator=None):
        logger.debug(f"Initializing ConfigManager with config_path={config_path}, translator={translator}")
        self.config_path = config_path
        self.translator = translator
        self.config = self._load_config()
        logger.info("ConfigManager initialized.")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or return defaults.

        Returns:
            Dict[str, Any]: The configuration dictionary
        """
        logger.debug(f"Loading configuration from {self.config_path}")
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    config = json.load(f)
                    logger.info(f"Configuration loaded from {self.config_path}")
                    return config
            except json.JSONDecodeError:
                error_msg = "Error loading config file. Using defaults."
                logger.error(error_msg)
                if self.translator:
                    error_msg = self.translator.get(error_msg)
                console.print(f"[bold red]{error_msg}[/]")

        hostname = (
            os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or "unknown"
        )
        current_user = os.environ.get("USERNAME") or os.environ.get("USER") or "unknown"
        logger.debug(f"Using hostname={hostname}, current_user={current_user} for default config.")
        default_config = {
            "version": __version__,
            "last_modified": datetime.datetime.now().isoformat(),
            "user_info": {
                "created_by": os.environ.get("USERNAME")
                or os.environ.get("USER")
                or "unknown",
            },
            "environment": {
                "type": "development",
                "path": "",
                "hostname": hostname,
                "creation_date": datetime.datetime.now().isoformat(),
            },
            "app_settings": {"log_level": "info", "log_path": "", "auto_update": True},
            "metadata": {
                "config_version": "1.0",
                "description": "TeddyCloudStarter configuration",
            },
            "language": "en",
        }
        logger.info("Default configuration loaded.")
        return default_config

    def save(self):
        """Save current configuration to file."""
        logger.debug(f"Saving configuration to {self.config_path}")
        self.config["version"] = __version__
        self.config["last_modified"] = datetime.datetime.now().isoformat()
        if "metadata" not in self.config:
            logger.debug("Adding default metadata to config.")
            self.config["metadata"] = {
                "config_version": "1.0",
                "description": "TeddyCloudStarter configuration",
            }
        if "environment" not in self.config:
            logger.debug("Adding default environment to config.")
            hostname = (
                os.environ.get("COMPUTERNAME")
                or os.environ.get("HOSTNAME")
                or "unknown"
            )
            self.config["environment"] = {
                "type": "development",
                "hostname": hostname,
                "creation_date": datetime.datetime.now().isoformat(),
            }
        if "user_info" not in self.config:
            logger.debug("Adding default user_info to config.")
            current_user = (
                os.environ.get("USERNAME") or os.environ.get("USER") or "unknown"
            )
            self.config["user_info"] = {"modified_by": current_user}
        if "app_settings" not in self.config:
            logger.debug("Adding default app_settings to config.")
            self.config["app_settings"] = {
                "log_level": "critical",
                "log_console": True,
                "log_path": "",
                "auto_update": True,
            }
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2)
        logger.info(f"Configuration saved to {self.config_path}")
        save_msg = f"Configuration saved to {self.config_path}"
        if self.translator:
            save_msg = self.translator.get(save_msg)
        console.print(f"[bold green]{save_msg}[/]")
        self.config = self._load_config()

    def backup(self):
        """Create a backup of the current configuration."""
        logger.debug(f"Creating backup for configuration at {self.config_path}")
        if os.path.exists(self.config_path):
            backup_path = f"{self.config_path}.backup.{int(time.time())}"
            shutil.copy2(self.config_path, backup_path)
            logger.info(f"Backup created at {backup_path}")
            backup_msg = f"Backup created at {backup_path}"
            if self.translator:
                backup_msg = self.translator.get("Backup created at {path}").format(
                    path=backup_path
                )
            console.print(f"[bold green]{backup_msg}[/]")
        else:
            logger.warning(f"No configuration file found at {self.config_path} to backup.")

    def delete(self):
        """Delete the configuration file."""
        logger.debug(f"Deleting configuration file at {self.config_path}")
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
            logger.info(f"Configuration file {self.config_path} deleted")
            delete_msg = f"Configuration file {self.config_path} deleted"
            if self.translator:
                delete_msg = self.translator.get(
                    "Configuration file {path} deleted"
                ).format(path=self.config_path)
            console.print(f"[bold red]{delete_msg}[/]")
            self.config = self._load_config()
        else:
            logger.warning(f"No configuration file found at {self.config_path} to delete.")

    @staticmethod
    def get_auto_update_setting(config_path=DEFAULT_CONFIG_PATH):
        """
        Get the auto_update setting from the configuration file.

        Args:
            config_path: Path to the configuration file. Defaults to DEFAULT_CONFIG_PATH.

        Returns:
            bool: True if auto_update is enabled, False otherwise
        """
        logger.debug(f"Getting auto_update setting from {config_path}")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
                    logger.debug("Configuration file loaded for auto_update setting.")
                    if (
                        "app_settings" in config
                        and "auto_update" in config["app_settings"]
                    ):
                        logger.info(f"auto_update setting found: {config['app_settings']['auto_update']}")
                        return config["app_settings"]["auto_update"]
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Error reading auto_update setting: {e}")
        else:
            logger.warning(f"No configuration file found at {config_path} for auto_update setting.")
        logger.info("auto_update setting not found, returning False.")
        return False

    def toggle_auto_update(self):
        """
        Toggle the auto_update setting in the configuration.

        Returns:
            bool: The new auto_update setting value
        """
        logger.debug("Toggling auto_update setting.")
        if "app_settings" not in self.config:
            logger.debug("app_settings not found in config, adding default.")
            self.config["app_settings"] = {
                "log_level": "info",
                "log_path": "",
                "auto_update": False,
            }
        elif "auto_update" not in self.config["app_settings"]:
            logger.debug("auto_update not found in app_settings, setting to False.")
            self.config["app_settings"]["auto_update"] = False

        current_value = self.config["app_settings"]["auto_update"]
        new_value = not current_value
        logger.info(f"Changing auto_update from {current_value} to {new_value}")
        self.config["app_settings"]["auto_update"] = new_value

        # Save the configuration
        self.save()

        toggle_msg = f"Auto-update {'enabled' if new_value else 'disabled'}"
        if self.translator:
            if new_value:
                toggle_msg = self.translator.get("Auto-update enabled")
            else:
                toggle_msg = self.translator.get("Auto-update disabled")
        console.print(f"[bold {'green' if new_value else 'yellow'}]{toggle_msg}[/]")
        logger.info(f"Auto-update toggled. New value: {new_value}")

        return new_value

    def reset_config(self):
        """Reset the configuration to default values."""
        logger.debug("Resetting configuration to default values.")
        self.config = self._load_config()

        reset_msg = "Configuration reset to defaults"
        if self.translator:
            reset_msg = self.translator.get(reset_msg)
        console.print(f"[bold yellow]{reset_msg}[/]")
        logger.info("Configuration reset to defaults.")

        return True

    def invalidate_client_certificate(self, cert_serial, client_cert_manager=None):
        """Invalidate a client certificate in the configuration.

        Args:
            cert_serial: The serial number of the certificate to invalidate
            client_cert_manager: Optional ClientCertificateManager instance for actual revocation

        Returns:
            bool: True if successful, False otherwise
        """
        logger.debug(f"Invalidating client certificate with serial {cert_serial}")
        if (
            "security" not in self.config
            or "client_certificates" not in self.config["security"]
        ):
            error_msg = "No client certificates found in configuration."
            logger.error(error_msg)
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
                    already_revoked_msg = (
                        f"Certificate with serial {cert_serial} is already revoked."
                    )
                    logger.warning(already_revoked_msg)
                    if self.translator:
                        already_revoked_msg = self.translator.get(
                            "Certificate with serial {serial} is already revoked."
                        ).format(serial=cert_serial)
                    console.print(f"[bold yellow]{already_revoked_msg}[/]")
                    return True

                # If client_cert_manager is provided, properly revoke the certificate
                if client_cert_manager:
                    safe_name = cert.get("safe_name")
                    if safe_name:
                        success, _ = client_cert_manager.revoke_client_certificate(
                            cert_name=safe_name
                        )
                        if not success:
                            # If actual revocation fails, still mark as revoked in config
                            error_msg = "Certificate revocation process failed, but certificate will be marked as revoked in configuration."
                            logger.error(error_msg)
                            if self.translator:
                                error_msg = self.translator.get(error_msg)
                            console.print(f"[bold yellow]{error_msg}[/]")

                # Mark certificate as revoked in the configuration
                self.config["security"]["client_certificates"][i]["revoked"] = True
                self.config["security"]["client_certificates"][i][
                    "revocation_date"
                ] = datetime.datetime.now().strftime("%Y-%m-%d")
                self.save()

                success_msg = f"Certificate with serial {cert_serial} has been invalidated in configuration."
                logger.info(success_msg)
                if self.translator:
                    success_msg = self.translator.get(
                        "Certificate with serial {serial} has been invalidated in configuration."
                    ).format(serial=cert_serial)
                console.print(f"[bold green]{success_msg}[/]")

                return True

        if not cert_found:
            not_found_msg = (
                f"Certificate with serial {cert_serial} not found in configuration."
            )
            logger.error(not_found_msg)
            if self.translator:
                not_found_msg = self.translator.get(
                    "Certificate with serial {serial} not found in configuration."
                ).format(serial=cert_serial)
            console.print(f"[bold red]{not_found_msg}[/]")

        return cert_found
