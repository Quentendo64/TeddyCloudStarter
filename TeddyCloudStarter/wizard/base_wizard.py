#!/usr/bin/env python3
"""
Base wizard class for TeddyCloudStarter.
"""
from pathlib import Path

from ..config_manager import ConfigManager
from ..configurations import TEMPLATES
from ..docker.manager import DockerManager
from ..security import (
    AuthBypassIPManager,
    BasicAuthManager,
    CertificateAuthority,
    ClientCertificateManager,
    IPRestrictionsManager,
    LetsEncryptManager,
)
from ..utilities.localization import Translator
from ..utilities.logger import logger


class BaseWizard:
    """Base class for wizard functionality."""

    def __init__(self, locales_dir: Path):
        """
        Initialize the base wizard with required managers and components.

        Args:
            locales_dir: Path to the localization directory
        """
        logger.debug(f"Initializing BaseWizard with locales_dir={locales_dir}")
        self.translator = Translator(locales_dir)
        logger.debug("Translator initialized.")
        self.config_manager = ConfigManager(translator=self.translator)
        logger.debug("ConfigManager initialized.")
        self.docker_manager = DockerManager(translator=self.translator)
        logger.debug("DockerManager initialized.")

        self.project_path = None
        logger.debug(f"Project path set to {self.project_path}")

        self.ca_manager = CertificateAuthority(
            base_dir=self.project_path, translator=self.translator
        )
        logger.debug("CertificateAuthority manager initialized.")
        self.client_cert_manager = ClientCertificateManager(
            base_dir=self.project_path, translator=self.translator
        )
        logger.debug("ClientCertificateManager initialized.")
        self.lets_encrypt_manager = LetsEncryptManager(
            base_dir=self.project_path, translator=self.translator
        )
        logger.debug("LetsEncryptManager initialized.")
        self.basic_auth_manager = BasicAuthManager(translator=self.translator)
        logger.debug("BasicAuthManager initialized.")
        self.ip_restrictions_manager = IPRestrictionsManager(translator=self.translator)
        logger.debug("IPRestrictionsManager initialized.")
        self.auth_bypass_manager = AuthBypassIPManager(translator=self.translator)
        logger.debug("AuthBypassIPManager initialized.")

        self.templates = TEMPLATES
        logger.info("BaseWizard initialized successfully.")
