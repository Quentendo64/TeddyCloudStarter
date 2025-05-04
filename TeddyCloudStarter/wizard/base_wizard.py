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


class BaseWizard:
    """Base class for wizard functionality."""

    def __init__(self, locales_dir: Path):
        """
        Initialize the base wizard with required managers and components.

        Args:
            locales_dir: Path to the localization directory
        """
        self.translator = Translator(locales_dir)
        self.config_manager = ConfigManager(translator=self.translator)
        self.docker_manager = DockerManager(translator=self.translator)

        self.project_path = None

        self.ca_manager = CertificateAuthority(
            base_dir=self.project_path, translator=self.translator
        )
        self.client_cert_manager = ClientCertificateManager(
            base_dir=self.project_path, translator=self.translator
        )
        self.lets_encrypt_manager = LetsEncryptManager(
            base_dir=self.project_path, translator=self.translator
        )
        self.basic_auth_manager = BasicAuthManager(translator=self.translator)
        self.ip_restrictions_manager = IPRestrictionsManager(translator=self.translator)
        self.auth_bypass_manager = AuthBypassIPManager(translator=self.translator)

        self.templates = TEMPLATES
