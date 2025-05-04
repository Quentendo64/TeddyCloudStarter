#!/usr/bin/env python3
"""
Logging utilities for TeddyCloudStarter.
Provides standardized logging to console and file.
"""
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich import box
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.theme import Theme

# Create custom theme for Rich console
custom_theme = Theme(
    {
        "info": "bold cyan",
        "warning": "bold yellow",
        "error": "bold red",
        "critical": "bold white on red",
        "debug": "bold green",
        "success": "bold green",
    }
)

# Create console instance with custom theme
console = Console(theme=custom_theme)

# Define log levels mapping
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

# Default log directory within user's home directory
DEFAULT_LOG_DIR = os.path.join(str(Path.home()), ".teddycloudstarter", "logs")


class TeddyLogger:
    """
    Logger class for TeddyCloudStarter.

    Handles logging to console and file based on configured log level.
    """

    def __init__(
        self,
        name: str = "TeddyCloudStarter",
        config_manager=None,
        log_to_file: bool = True,
        log_path: Optional[str] = None,
        use_panels: bool = False,  # Default to in-line formatting
        use_inline: bool = True,  # Use in-line formatting
    ):
        """
        Initialize the logger.

        Args:
            name: Logger name
            config_manager: Optional ConfigManager instance to get settings
            log_to_file: Whether to log to file
            log_path: Custom log path (overrides config_manager setting)
            use_panels: Whether to use Rich panels for console output
            use_inline: Whether to use in-line formatting (prefix style)
        """
        self.name = name
        self.config_manager = config_manager
        self.log_to_file = log_to_file
        self._logger = None
        self.translator = getattr(config_manager, "translator", None)
        self.console = console
        self.use_panels = use_panels
        self.use_inline = use_inline

        # Get log level from config manager or default to info
        self.log_level = "info"
        if config_manager and hasattr(config_manager, "config"):
            if "app_settings" in config_manager.config:
                self.log_level = (
                    config_manager.config["app_settings"]
                    .get("log_level", "info")
                    .lower()
                )

                # Get log path from config if provided
                if not log_path and "log_path" in config_manager.config["app_settings"]:
                    log_path = config_manager.config["app_settings"].get("log_path")

        # Set up logger
        self._setup_logger(log_path)

    def _setup_logger(self, log_path: Optional[str] = None):
        """
        Set up the logger with console and file handlers.

        Args:
            log_path: Path to log file directory
        """
        # Create logger
        self._logger = logging.getLogger(self.name)
        self._logger.setLevel(LOG_LEVELS.get(self.log_level, logging.INFO))

        # Remove existing handlers
        for handler in self._logger.handlers[:]:
            self._logger.removeHandler(handler)

        # Configure console handler with Rich
        console_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=False,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
        )
        console_handler.setFormatter(logging.Formatter("%(message)s"))
        console_handler.setLevel(LOG_LEVELS.get(self.log_level, logging.INFO))
        self._logger.addHandler(console_handler)

        # Add file handler if logging to file is enabled
        if self.log_to_file:
            # Determine log directory
            if log_path and log_path.strip():
                log_dir = log_path
            else:
                log_dir = DEFAULT_LOG_DIR

            # Create log directory if it doesn't exist
            os.makedirs(log_dir, exist_ok=True)

            # Create log file with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(log_dir, f"teddy_cloud_{timestamp}.log")

            # Configure file handler
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(LOG_LEVELS.get(self.log_level, logging.INFO))
            self._logger.addHandler(file_handler)

    def _translate(self, text: str) -> str:
        """
        Translate text if translator is available.

        Args:
            text: Text to translate

        Returns:
            Translated text or original text if translator not available
        """
        if self.translator:
            return self.translator.get(text)
        return text

    def _handle_message(self, message):
        """
        Handle different message types including Rich Panel objects.

        Args:
            message: The message object to handle (string or Rich Panel)

        Returns:
            Processed string message suitable for logging
        """
        if isinstance(message, Panel):
            # If it's a Panel object, get its renderable content
            return (
                str(message.renderable)
                if hasattr(message, "renderable")
                else str(message)
            )
        return message

    def _create_panel(self, message: str, level: str = "info", title: str = None):
        """
        Create a Rich panel for the message with appropriate styling.

        Args:
            message: The message to display in the panel
            level: The log level (info, warning, error, etc)
            title: Optional panel title

        Returns:
            Rich Panel object
        """
        styles = {
            "info": "cyan",
            "warning": "yellow",
            "error": "red",
            "critical": "red",
            "debug": "green",
            "success": "green",
        }

        border_style = styles.get(level, "blue")

        if level in ["warning", "error", "critical"]:
            title_text = title or level.upper()
        else:
            title_text = title

        return Panel(
            message,
            title=title_text,
            border_style=border_style,
            box=box.ROUNDED,
            expand=False,
            padding=(1, 2),
        )

    def _create_inline_prefix(self, level: str, label: str = None):
        """
        Create an inline prefix for the message based on log level.

        Args:
            level: The log level (info, warning, error, etc)
            label: Optional custom label for the prefix

        Returns:
            Rich formatted prefix string
        """
        styles = {
            "info": "bold cyan",
            "warning": "bold yellow",
            "error": "bold red",
            "critical": "bold white on red",
            "debug": "bold green",
            "success": "bold green",
        }

        style = styles.get(level, "bold blue")

        if not label:
            if level == "info":
                label = "INFO"
            elif level == "warning":
                label = "WARNING"
            elif level == "error":
                label = "ERROR"
            elif level == "critical":
                label = "CRITICAL"
            elif level == "debug":
                label = "DEBUG"
            elif level == "success":
                label = "SUCCESS"

        return f"[{style}]{label}[/]"

    def debug(self, message, **kwargs):
        """Log a debug message."""
        message = self._handle_message(message)
        self._logger.debug(message, **kwargs)

    def info(self, message, **kwargs):
        """Log an info message."""
        message = self._handle_message(message)
        self._logger.info(message, **kwargs)

    def warning(self, message, **kwargs):
        """Log a warning message."""
        message = self._handle_message(message)
        self._logger.warning(message, **kwargs)

    def error(self, message, **kwargs):
        """Log an error message."""
        message = self._handle_message(message)
        self._logger.error(message, **kwargs)

    def critical(self, message, **kwargs):
        """Log a critical message."""
        message = self._handle_message(message)
        self._logger.critical(message, **kwargs)

    def success(self, message, **kwargs):
        """Log a success message (info level with success styling)."""
        # Use info level but with success styling for console
        message = self._handle_message(message)
        styled_message = f"[success]{message}[/]"
        self._logger.info(styled_message, **kwargs)

    # Methods with Rich formatting support for console output
    def print_info(self, message, title=None, label=None):
        """Print an info message with Rich formatting."""
        if isinstance(message, Panel):
            console.print(message)
            self._logger.info(self._handle_message(message))
        else:
            translated_message = self._translate(message)

            if self.use_panels:
                panel = self._create_panel(translated_message, "info", title)
                console.print(panel)
            elif self.use_inline:
                prefix = self._create_inline_prefix("info", label)
                console.print(f"{prefix} - {translated_message}")
            else:
                console.print(f"[info]{translated_message}[/]")

            self._logger.info(message)

    def print_warning(self, message, title=None, label=None):
        """Print a warning message with Rich formatting."""
        if isinstance(message, Panel):
            console.print(message)
            self._logger.warning(self._handle_message(message))
        else:
            translated_message = self._translate(message)

            if self.use_panels:
                panel = self._create_panel(
                    translated_message, "warning", title or "WARNING"
                )
                console.print(panel)
            elif self.use_inline:
                prefix = self._create_inline_prefix("warning", label or "WARNING")
                console.print(f"{prefix} - {translated_message}")
            else:
                console.print(f"[warning]{translated_message}[/]")

            self._logger.warning(message)

    def print_error(self, message, title=None, label=None):
        """Print an error message with Rich formatting."""
        if isinstance(message, Panel):
            console.print(message)
            self._logger.error(self._handle_message(message))
        else:
            translated_message = self._translate(message)

            if self.use_panels:
                panel = self._create_panel(
                    translated_message, "error", title or "ERROR"
                )
                console.print(panel)
            elif self.use_inline:
                prefix = self._create_inline_prefix("error", label or "ERROR")
                console.print(f"{prefix} - {translated_message}")
            else:
                console.print(f"[error]{translated_message}[/]")

            self._logger.error(message)

    def print_success(self, message, title=None, label=None):
        """Print a success message with Rich formatting."""
        if isinstance(message, Panel):
            console.print(message)
            self._logger.info(self._handle_message(message))
        else:
            translated_message = self._translate(message)

            if self.use_panels:
                panel = self._create_panel(
                    translated_message, "success", title or "SUCCESS"
                )
                console.print(panel)
            elif self.use_inline:
                prefix = self._create_inline_prefix("success", label or "SUCCESS")
                console.print(f"{prefix} - {translated_message}")
            else:
                console.print(f"[success]{translated_message}[/]")

            self._logger.info(message)

    def print_debug(self, message, title=None, label=None):
        """Print a debug message with Rich formatting."""
        if isinstance(message, Panel):
            console.print(message)
            self._logger.debug(self._handle_message(message))
        else:
            translated_message = self._translate(message)

            if self.use_panels:
                panel = self._create_panel(
                    translated_message, "debug", title or "DEBUG"
                )
                console.print(panel)
            elif self.use_inline:
                prefix = self._create_inline_prefix("debug", label or "DEBUG")
                console.print(f"{prefix} - {translated_message}")
            else:
                console.print(f"[debug]{translated_message}[/]")

            self._logger.debug(message)

    def print_critical(self, message, title=None, label=None):
        """Print a critical message with Rich formatting."""
        if isinstance(message, Panel):
            console.print(message)
            self._logger.critical(self._handle_message(message))
        else:
            translated_message = self._translate(message)

            if self.use_panels:
                panel = self._create_panel(
                    translated_message, "critical", title or "CRITICAL"
                )
                console.print(panel)
            elif self.use_inline:
                prefix = self._create_inline_prefix("critical", label or "CRITICAL")
                console.print(f"{prefix} - {translated_message}")
            else:
                console.print(f"[critical]{translated_message}[/]")

            self._logger.critical(message)

    def set_log_level(self, level: str):
        """
        Set the log level.

        Args:
            level: Log level (debug, info, warning, error, critical)
        """
        if level.lower() in LOG_LEVELS:
            self.log_level = level.lower()
            self._logger.setLevel(LOG_LEVELS[level.lower()])

            # Update handlers
            for handler in self._logger.handlers:
                handler.setLevel(LOG_LEVELS[level.lower()])

            # Update config manager if available
            if self.config_manager and hasattr(self.config_manager, "config"):
                if "app_settings" in self.config_manager.config:
                    self.config_manager.config["app_settings"][
                        "log_level"
                    ] = level.lower()
                    self.config_manager.save()

    def set_use_panels(self, use_panels: bool):
        """
        Set whether to use Rich panels for console output.

        Args:
            use_panels: Whether to use panels
        """
        self.use_panels = use_panels
        if use_panels:
            self.use_inline = False

    def set_use_inline(self, use_inline: bool):
        """
        Set whether to use in-line formatting for console output.

        Args:
            use_inline: Whether to use in-line formatting
        """
        self.use_inline = use_inline
        if use_inline:
            self.use_panels = False


# Create a default logger instance with in-line formatting
logger = TeddyLogger(use_panels=False, use_inline=True)


def get_logger(
    name: str = None,
    config_manager=None,
    log_to_file: bool = False,
    log_path: Optional[str] = None,
    use_panels: bool = False,
    use_inline: bool = True,
) -> TeddyLogger:
    """
    Get a logger instance.

    Args:
        name: Logger name
        config_manager: ConfigManager instance
        log_to_file: Whether to log to file
        log_path: Custom log path
        use_panels: Whether to use Rich panels for console output
        use_inline: Whether to use in-line formatting

    Returns:
        TeddyLogger instance
    """
    return TeddyLogger(
        name or "TeddyCloudStarter",
        config_manager,
        log_to_file,
        log_path,
        use_panels,
        use_inline,
    )
