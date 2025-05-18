#!/usr/bin/env python3
"""
Localization utilities for TeddyCloudStarter.
"""
import gettext
import locale
from pathlib import Path
from typing import Optional
from ..utilities.logger import logger


class Translator:
    """Handles translations for TeddyCloudStarter."""

    def __init__(self, locales_dir: Path):
        logger.debug(f"Initializing Translator with locales_dir: {locales_dir}")
        self.translations = {}
        self.current_language = "en"
        self.locales_dir = locales_dir
        self.available_languages = ["en"]
        self._load_translations()
        logger.info(f"Translator initialized. Available languages: {self.available_languages}, Current language: {self.current_language}")

    def _load_translations(self):
        """Load all available translations."""
        logger.debug("Loading available translations.")
        if self.locales_dir.exists():
            for lang_dir in self.locales_dir.iterdir():
                logger.debug(f"Checking language directory: {lang_dir}")
                if (
                    lang_dir.is_dir()
                    and (lang_dir / "LC_MESSAGES" / "teddycloudstarter.mo").exists()
                ):
                    logger.info(f"Found translation for language: {lang_dir.name}")
                    self.available_languages.append(lang_dir.name)

        try:
            locale.setlocale(locale.LC_ALL, "")
            system_lang = locale.getlocale(locale.LC_MESSAGES)[0]
            logger.debug(f"System language detected: {system_lang}")
            if system_lang:
                lang_code = system_lang.split("_")[0]
                if lang_code in self.available_languages:
                    self.current_language = lang_code
                    logger.info(f"Set current language to system language: {lang_code}")
        except (locale.Error, AttributeError, TypeError) as e:
            logger.warning(f"Could not set locale from system: {e}")

    def set_language(self, lang_code: str) -> bool:
        """Set the current language.

        Args:
            lang_code: The language code to set

        Returns:
            bool: True if language was set successfully, False otherwise
        """
        logger.debug(f"Attempting to set language to: {lang_code}")
        if lang_code in self.available_languages:
            self.current_language = lang_code
            logger.info(f"Language set to: {lang_code}")
            return True
        logger.warning(f"Language {lang_code} not available.")
        return False

    def get(self, key: str, default: Optional[str] = None) -> str:
        """Get translation for a key.

        Args:
            key: The translation key to look up
            default: Default value if translation is not found

        Returns:
            str: The translated string or the default/key if not found
        """
        logger.debug(f"Getting translation for key: '{key}' with default: '{default}' in language: {self.current_language}")
        try:
            translation = gettext.translation(
                "teddycloudstarter",
                localedir=str(self.locales_dir),
                languages=[self.current_language],
                fallback=True,
            )
            _ = translation.gettext
            result = _(key)
            logger.debug(f"Translation result for key '{key}': '{result}'")
            return result
        except (FileNotFoundError, OSError) as e:
            logger.error(f"Translation file not found or error occurred: {e}")
            return default if default is not None else key
