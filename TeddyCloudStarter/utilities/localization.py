#!/usr/bin/env python3
"""
Localization utilities for TeddyCloudStarter.
"""
import os
import locale
import gettext
from pathlib import Path
from typing import Optional


class Translator:
    """Handles translations for TeddyCloudStarter."""
    
    def __init__(self, locales_dir: Path):
        self.translations = {}
        self.current_language = "en"
        self.locales_dir = locales_dir
        self.available_languages = ["en"]
        self._load_translations()
        
    def _load_translations(self):
        """Load all available translations."""
        
        if self.locales_dir.exists():
            for lang_dir in self.locales_dir.iterdir():
                if lang_dir.is_dir() and (lang_dir / "LC_MESSAGES" / "teddycloudstarter.mo").exists():
                    self.available_languages.append(lang_dir.name)
        
        # Try to get system language using modern methods
        try:
            # Set locale to user's default
            locale.setlocale(locale.LC_ALL, '')
            # Get the language code from current locale settings
            system_lang = locale.getlocale(locale.LC_MESSAGES)[0]
            if system_lang:
                lang_code = system_lang.split('_')[0]
                if lang_code in self.available_languages:
                    self.current_language = lang_code
        except (locale.Error, AttributeError, TypeError):
            pass
    
    def set_language(self, lang_code: str) -> bool:
        """Set the current language.
        
        Args:
            lang_code: The language code to set
            
        Returns:
            bool: True if language was set successfully, False otherwise
        """
        if lang_code in self.available_languages:
            self.current_language = lang_code
            return True
        return False
    
    def get(self, key: str, default: Optional[str] = None) -> str:
        """Get translation for a key.
        
        Args:
            key: The translation key to look up
            default: Default value if translation is not found
            
        Returns:
            str: The translated string or the default/key if not found
        """
        try:
            # Create a new translation object each time to ensure we get fresh translations
            translation = gettext.translation('teddycloudstarter', 
                                             localedir=str(self.locales_dir), 
                                             languages=[self.current_language],
                                             fallback=True)
            _ = translation.gettext
            return _(key)
        except (FileNotFoundError, OSError):
            return default if default is not None else key
