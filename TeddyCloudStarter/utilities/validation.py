#!/usr/bin/env python3
"""
Validation module for TeddyCloudStarter.
Centralizes all validation logic for configuration data.
"""
import os
import subprocess
from typing import Any, Dict, List, Tuple

from .network import validate_domain_name, validate_ip_address
from .logger import logger


class ConfigValidator:
    """Provides validation methods for TeddyCloudStarter configuration."""

    def __init__(self, translator=None):
        """
        Initialize the validator.

        Args:
            translator: Optional translator instance for localized error messages
        """
        logger.debug(f"Initializing ConfigValidator with translator={translator}")
        self.translator = translator
        logger.info("ConfigValidator initialized.")

    def translate(self, message: str) -> str:
        """
        Translate a message if translator is available.

        Args:
            message: The message to translate

        Returns:
            str: The translated message, or the original if no translator
        """
        logger.debug(f"Translating message: {message}")
        if self.translator:
            translated = self.translator.get(message)
            logger.debug(f"Translated message: {translated}")
            return translated
        logger.debug("No translator provided, returning original message.")
        return message

    def validate_base_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate the base configuration requirements.

        Args:
            config: The configuration dictionary

        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_error_messages)
        """
        logger.debug(f"Validating base config: {config}")
        errors = []

        required_keys = ["mode"]
        missing_keys = [key for key in required_keys if key not in config]

        if missing_keys:
            logger.warning(f"Missing required configuration keys: {missing_keys}")
            errors.append(
                self.translate("Missing required configuration keys: {keys}").format(
                    keys=", ".join(missing_keys)
                )
            )
            return False, errors

        valid_modes = ["direct", "nginx"]
        if config["mode"] not in valid_modes:
            logger.warning(f"Invalid mode: {config['mode']}")
            errors.append(
                self.translate(
                    "Invalid mode: {mode}. Must be one of: {valid_modes}"
                ).format(mode=config["mode"], valid_modes=", ".join(valid_modes))
            )

        if config["mode"] == "direct":
            logger.debug("Validating direct mode configuration.")
            valid, mode_errors = self.validate_direct_mode(config)
            if not valid:
                logger.warning(f"Direct mode validation errors: {mode_errors}")
                errors.extend(mode_errors)

        elif config["mode"] == "nginx":
            logger.debug("Validating nginx mode configuration.")
            valid, mode_errors = self.validate_nginx_mode(config)
            if not valid:
                logger.warning(f"Nginx mode validation errors: {mode_errors}")
                errors.extend(mode_errors)

        logger.info(f"Base config validation result: {len(errors) == 0}, errors: {errors}")
        return len(errors) == 0, errors

    def validate_direct_mode(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate direct mode configuration.

        Args:
            config: The configuration dictionary

        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_error_messages)
        """
        logger.debug(f"Validating direct mode config: {config}")
        errors = []

        if "ports" not in config:
            logger.warning("Direct mode requires ports configuration.")
            errors.append(self.translate("Direct mode requires ports configuration"))
            return False, errors

        if not isinstance(config["ports"], dict):
            logger.warning("Ports configuration must be a dictionary.")
            errors.append(self.translate("Ports configuration must be a dictionary"))
        else:
            for port_name, port_value in config["ports"].items():
                if port_value is not None and not isinstance(port_value, int):
                    logger.warning(f"Port {port_name} must be an integer or null.")
                    errors.append(
                        self.translate(
                            "Port {port_name} must be an integer or null"
                        ).format(port_name=port_name)
                    )

        logger.info(f"Direct mode validation result: {len(errors) == 0}, errors: {errors}")
        return len(errors) == 0, errors

    def validate_nginx_mode(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate nginx mode configuration.

        Args:
            config: The configuration dictionary

        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_error_messages)
        """
        logger.debug(f"Validating nginx mode config: {config}")
        errors = []

        if "nginx" not in config:
            logger.warning("Nginx mode requires nginx configuration.")
            errors.append(self.translate("Nginx mode requires nginx configuration"))
            return False, errors

        nginx_config = config["nginx"]

        if "domain" not in nginx_config:
            logger.warning("Nginx configuration requires a domain.")
            errors.append(self.translate("Nginx configuration requires a domain"))
        elif not validate_domain_name(nginx_config["domain"]):
            logger.warning(f"Invalid domain name: {nginx_config['domain']}")
            errors.append(
                self.translate("Invalid domain name: {domain}").format(
                    domain=nginx_config["domain"]
                )
            )

        if "https_mode" not in nginx_config:
            logger.warning("Nginx configuration requires an HTTPS mode.")
            errors.append(self.translate("Nginx configuration requires an HTTPS mode"))
        elif nginx_config["https_mode"] not in [
            "letsencrypt",
            "self_signed",
            "user_provided",
            "none",
        ]:
            logger.warning(f"Invalid HTTPS mode: {nginx_config['https_mode']}")
            errors.append(
                self.translate("Invalid HTTPS mode: {mode}").format(
                    mode=nginx_config["https_mode"]
                )
            )

        if "security" not in nginx_config:
            logger.warning("Nginx configuration requires security settings.")
            errors.append(
                self.translate("Nginx configuration requires security settings")
            )
        else:
            security_config = nginx_config["security"]
            if "type" not in security_config:
                logger.warning("Security configuration requires a type.")
                errors.append(self.translate("Security configuration requires a type"))
            elif security_config["type"] not in [
                "none",
                "basic_auth",
                "client_cert",
                "ip_restriction",
            ]:
                logger.warning(f"Invalid security type: {security_config['type']}")
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
                    logger.warning("IP restriction requires at least one IP address.")
                    errors.append(
                        self.translate(
                            "IP restriction requires at least one IP address"
                        )
                    )
                else:
                    for ip in security_config["allowed_ips"]:
                        if not validate_ip_address(ip):
                            logger.warning(f"Invalid IP address or CIDR: {ip}")
                            errors.append(
                                self.translate(
                                    "Invalid IP address or CIDR: {ip}"
                                ).format(ip=ip)
                            )

        logger.info(f"Nginx mode validation result: {len(errors) == 0}, errors: {errors}")
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
        logger.debug(f"Validating certificates: cert_path={cert_path}, key_path={key_path}")
        if not os.path.exists(cert_path):
            logger.error(f"Certificate file does not exist: {cert_path}")
            return False, self.translate(
                "Certificate file does not exist: {path}"
            ).format(path=cert_path)

        if not os.path.exists(key_path):
            logger.error(f"Private key file does not exist: {key_path}")
            return False, self.translate(
                "Private key file does not exist: {path}"
            ).format(path=key_path)

        try:
            subprocess.run(
                ["openssl", "version"], check=True, capture_output=True, text=True
            )
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning("OpenSSL is not available. Certificate validation skipped.")
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
                logger.error(f"Invalid certificate: {cert_result.stderr}")
                return False, self.translate("Invalid certificate: {error}").format(
                    error=cert_result.stderr
                )

            if "X509v3" not in cert_result.stdout:
                logger.warning("Certificate is not an X509v3 certificate.")
                return False, self.translate(
                    "Certificate is not an X509v3 certificate, which might not be compatible with Nginx"
                )
        except Exception as e:
            logger.error(f"Error validating certificate: {e}")
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
                logger.error(f"Invalid private key: {key_result.stderr}")
                return False, self.translate("Invalid private key: {error}").format(
                    error=key_result.stderr
                )
        except Exception as e:
            logger.error(f"Error validating private key: {e}")
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
                logger.error("Certificate and private key do not match.")
                return False, self.translate("Certificate and private key do not match")
        except Exception as e:
            logger.error(f"Error checking if certificate and key match: {e}")
            return False, self.translate(
                "Error checking if certificate and key match: {error}"
            ).format(error=str(e))

        logger.info("Certificate and private key validation successful.")
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
    logger.debug(f"Validating config with translator={translator}")
    validator = ConfigValidator(translator)
    result = validator.validate_base_config(config)
    logger.info(f"validate_config result: {result}")
    return result
