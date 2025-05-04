#!/usr/bin/env python3
"""
Validation module for TeddyCloudStarter.
Centralizes all validation logic for configuration data.
"""
import os
import subprocess
from typing import Any, Dict, List, Tuple

from .network import validate_domain_name, validate_ip_address


class ConfigValidator:
    """Provides validation methods for TeddyCloudStarter configuration."""

    def __init__(self, translator=None):
        """
        Initialize the validator.

        Args:
            translator: Optional translator instance for localized error messages
        """
        self.translator = translator

    def translate(self, message: str) -> str:
        """
        Translate a message if translator is available.

        Args:
            message: The message to translate

        Returns:
            str: The translated message, or the original if no translator
        """
        if self.translator:
            return self.translator.get(message)
        return message

    def validate_base_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate the base configuration requirements.

        Args:
            config: The configuration dictionary

        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_error_messages)
        """
        errors = []

        required_keys = ["mode"]
        missing_keys = [key for key in required_keys if key not in config]

        if missing_keys:
            errors.append(
                self.translate("Missing required configuration keys: {keys}").format(
                    keys=", ".join(missing_keys)
                )
            )
            return False, errors

        valid_modes = ["direct", "nginx"]
        if config["mode"] not in valid_modes:
            errors.append(
                self.translate(
                    "Invalid mode: {mode}. Must be one of: {valid_modes}"
                ).format(mode=config["mode"], valid_modes=", ".join(valid_modes))
            )

        if config["mode"] == "direct":
            valid, mode_errors = self.validate_direct_mode(config)
            if not valid:
                errors.extend(mode_errors)

        elif config["mode"] == "nginx":
            valid, mode_errors = self.validate_nginx_mode(config)
            if not valid:
                errors.extend(mode_errors)

        return len(errors) == 0, errors

    def validate_direct_mode(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate direct mode configuration.

        Args:
            config: The configuration dictionary

        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_error_messages)
        """
        errors = []

        if "ports" not in config:
            errors.append(self.translate("Direct mode requires ports configuration"))
            return False, errors

        if not isinstance(config["ports"], dict):
            errors.append(self.translate("Ports configuration must be a dictionary"))
        else:
            for port_name, port_value in config["ports"].items():
                if port_value is not None and not isinstance(port_value, int):
                    errors.append(
                        self.translate(
                            "Port {port_name} must be an integer or null"
                        ).format(port_name=port_name)
                    )

        return len(errors) == 0, errors

    def validate_nginx_mode(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate nginx mode configuration.

        Args:
            config: The configuration dictionary

        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_error_messages)
        """
        errors = []

        if "nginx" not in config:
            errors.append(self.translate("Nginx mode requires nginx configuration"))
            return False, errors

        nginx_config = config["nginx"]

        if "domain" not in nginx_config:
            errors.append(self.translate("Nginx configuration requires a domain"))
        elif not validate_domain_name(nginx_config["domain"]):
            errors.append(
                self.translate("Invalid domain name: {domain}").format(
                    domain=nginx_config["domain"]
                )
            )

        if "https_mode" not in nginx_config:
            errors.append(self.translate("Nginx configuration requires an HTTPS mode"))
        elif nginx_config["https_mode"] not in [
            "letsencrypt",
            "self_signed",
            "user_provided",
            "none",
        ]:
            errors.append(
                self.translate("Invalid HTTPS mode: {mode}").format(
                    mode=nginx_config["https_mode"]
                )
            )

        if "security" not in nginx_config:
            errors.append(
                self.translate("Nginx configuration requires security settings")
            )
        else:
            security_config = nginx_config["security"]
            if "type" not in security_config:
                errors.append(self.translate("Security configuration requires a type"))
            elif security_config["type"] not in [
                "none",
                "basic_auth",
                "client_cert",
                "ip_restriction",
            ]:
                errors.append(
                    self.translate("Invalid security type: {type}").format(
                        type=security_config["type"]
                    )
                )

            if security_config.get("type") == "ip_restriction":
                if (
                    "allowed_ips" not in security_config
                    or not security_config["allowed_ips"]
                ):
                    errors.append(
                        self.translate(
                            "IP restriction requires at least one IP address"
                        )
                    )
                else:
                    for ip in security_config["allowed_ips"]:
                        if not validate_ip_address(ip):
                            errors.append(
                                self.translate(
                                    "Invalid IP address or CIDR: {ip}"
                                ).format(ip=ip)
                            )

        return len(errors) == 0, errors

    def validate_certificates(self, cert_path: str, key_path: str) -> Tuple[bool, str]:
        """
        Validate SSL certificates for Nginx.

        Args:
            cert_path: Path to the SSL certificate file
            key_path: Path to the SSL private key file

        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if not os.path.exists(cert_path):
            return False, self.translate(
                "Certificate file does not exist: {path}"
            ).format(path=cert_path)

        if not os.path.exists(key_path):
            return False, self.translate(
                "Private key file does not exist: {path}"
            ).format(path=key_path)

        try:
            subprocess.run(
                ["openssl", "version"], check=True, capture_output=True, text=True
            )
        except (subprocess.SubprocessError, FileNotFoundError):
            return True, self.translate(
                "Warning: OpenSSL is not available. Certificate validation skipped."
            )

        try:
            cert_result = subprocess.run(
                ["openssl", "x509", "-in", cert_path, "-text", "-noout"],
                check=False,
                capture_output=True,
                text=True,
            )

            if cert_result.returncode != 0:
                return False, self.translate("Invalid certificate: {error}").format(
                    error=cert_result.stderr
                )

            if "X509v3" not in cert_result.stdout:
                return False, self.translate(
                    "Certificate is not an X509v3 certificate, which might not be compatible with Nginx"
                )
        except Exception as e:
            return False, self.translate(
                "Error validating certificate: {error}"
            ).format(error=str(e))

        try:
            key_result = subprocess.run(
                ["openssl", "rsa", "-in", key_path, "-check", "-noout"],
                check=False,
                capture_output=True,
                text=True,
            )

            if key_result.returncode != 0:
                return False, self.translate("Invalid private key: {error}").format(
                    error=key_result.stderr
                )
        except Exception as e:
            return False, self.translate(
                "Error validating private key: {error}"
            ).format(error=str(e))

        try:
            cert_modulus_result = subprocess.run(
                ["openssl", "x509", "-in", cert_path, "-modulus", "-noout"],
                check=False,
                capture_output=True,
                text=True,
            )

            key_modulus_result = subprocess.run(
                ["openssl", "rsa", "-in", key_path, "-modulus", "-noout"],
                check=False,
                capture_output=True,
                text=True,
            )

            if cert_modulus_result.stdout.strip() != key_modulus_result.stdout.strip():
                return False, self.translate("Certificate and private key do not match")
        except Exception as e:
            return False, self.translate(
                "Error checking if certificate and key match: {error}"
            ).format(error=str(e))

        return True, ""


def validate_config(config: Dict[str, Any], translator=None) -> Tuple[bool, List[str]]:
    """
    Convenience function to validate configuration.

    Args:
        config: The configuration dictionary
        translator: Optional translator instance

    Returns:
        Tuple[bool, List[str]]: (is_valid, list_of_error_messages)
    """
    validator = ConfigValidator(translator)
    return validator.validate_base_config(config)
