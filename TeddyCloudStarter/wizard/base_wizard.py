#!/usr/bin/env python3
"""
Base wizard class for TeddyCloudStarter.
"""
from pathlib import Path
from ..config_manager import ConfigManager
from ..docker_manager import DockerManager
from ..translator import Translator
from ..certificates import CertificateManager
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
        self.cert_manager = CertificateManager(translator=self.translator)
        self.templates = TEMPLATES