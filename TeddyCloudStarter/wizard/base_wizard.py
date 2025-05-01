#!/usr/bin/env python3
"""
Base wizard class for TeddyCloudStarter.
"""
from pathlib import Path
from ..config_manager import ConfigManager
from ..docker.manager import DockerManager
from ..utilities.localization import Translator
from ..utilities.file_system import get_project_path
from ..security import CertificateAuthority, ClientCertificateManager, LetsEncryptManager, BasicAuthManager, IPRestrictionsManager, AuthBypassIPManager
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
        
        # Initialize project path as None first - will be set after language selection
        self.project_path = None
        
        # Initialize security modules with project path as None initially
        self.ca_manager = CertificateAuthority(base_dir=self.project_path, translator=self.translator)
        self.client_cert_manager = ClientCertificateManager(base_dir=self.project_path, translator=self.translator)
        self.lets_encrypt_manager = LetsEncryptManager(base_dir=self.project_path, translator=self.translator)
        self.basic_auth_manager = BasicAuthManager(translator=self.translator)
        self.ip_restrictions_manager = IPRestrictionsManager(translator=self.translator)
        self.auth_bypass_manager = AuthBypassIPManager(translator=self.translator)
        
        self.templates = TEMPLATES