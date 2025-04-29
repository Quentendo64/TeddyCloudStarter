#!/usr/bin/env python3
"""
Base wizard class for TeddyCloudStarter.
"""
from pathlib import Path
from ..config_manager import ConfigManager
from ..docker.manager import DockerManager
from ..utilities.localization import Translator
from ..security import CertificateAuthority, ClientCertificateManager, LetsEncryptManager, BasicAuthManager, IPRestrictionsManager
from ..configurations import TEMPLATES

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
        
        # Replace CertificateManager with security module classes
        self.ca_manager = CertificateAuthority(translator=self.translator)
        self.client_cert_manager = ClientCertificateManager(translator=self.translator)
        self.lets_encrypt_manager = LetsEncryptManager(translator=self.translator)
        self.basic_auth_manager = BasicAuthManager(translator=self.translator)
        self.ip_restrictions_manager = IPRestrictionsManager(translator=self.translator)
        
        self.templates = TEMPLATES