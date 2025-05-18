#!/usr/bin/env python3
"""
File system utility functions for TeddyCloudStarter.
"""
import os
import platform
from pathlib import Path
from typing import List, Optional

import questionary
from rich.console import Console
from ..utilities.logger import logger

console = Console()

custom_style = questionary.Style(
    [
        ("qmark", "fg:#673ab7 bold"),
        ("question", "bold"),
        ("answer", "fg:#4caf50 bold"),
        ("pointer", "fg:#673ab7 bold"),
        ("highlighted", "fg:#673ab7 bold"),
        ("selected", "fg:#4caf50"),
        ("separator", "fg:#673ab7"),
        ("instruction", "fg:#f44336"),
    ]
)

PARENT_DIR = ".."
CREATE_NEW = "[Create new folder]"
MANUAL_ENTRY = "[Enter path manually]"


def get_project_path(config_manager=None, translator=None) -> Optional[str]:
    logger.debug("Entering get_project_path.")
    """
    Get the project path from config or prompt the user to set it if not set.

    Args:
        config_manager: The configuration manager instance
        translator: Translator instance for internationalization

    Returns:
        Optional[str]: The project path, or None if not set
    """
    try:
        _ = lambda text: text
        if translator is not None:
            _ = lambda text: translator.get(text) or text

        if config_manager and config_manager.config:
            logger.debug("Config manager and config attribute found.")
            project_path = config_manager.config.get("environment", {}).get("path")
            logger.debug(f"Project path from config: {project_path}")
            if project_path and validate_path(project_path):
                return project_path

        logger.warning("Config manager or config attribute missing.")
        console.print(
            f"[bold yellow]{_('No project path is set. Please select a project path.')}[/]"
        )
        project_path = browse_directory(
            title=_("Select Project Path"), translator=translator
        )

        if project_path:
            if config_manager:
                config_manager.config.setdefault("environment", {})[
                    "path"
                ] = project_path
                config_manager.save()
            return project_path

        console.print(f"[bold red]{_('A project path must be set. Exiting.')}[/]")
        exit(1)

    except Exception as e:
        logger.error(f"Error in get_project_path: {e}")
        console.print(f"[bold red]{_('Error retrieving project path')}: {e}[/]")
        exit(1)


def ensure_project_directories(project_path):
    logger.debug(f"Entering ensure_project_directories with project_path: {project_path}")
    """
    Create necessary directories in the project path.

    Args:
        project_path: The path to the project directory (must not be None)
    """
    if not project_path:
        raise ValueError("project_path must not be None")

    base_path = Path(project_path)
    (base_path / "data").mkdir(exist_ok=True)
    (base_path / "data" / "configurations").mkdir(exist_ok=True)
    (base_path / "data" / "backup").mkdir(exist_ok=True)


def normalize_path(path: str) -> str:
    logger.debug(f"Entering normalize_path with path: {path}")
    """Normalize a file path by resolving ../ and ./ references.

    Args:
        path: The path to normalize

    Returns:
        str: The normalized path
    """
    try:
        norm = os.path.normpath(path)
        logger.debug(f"Normalized path: {norm}")
        return norm
    except Exception as e:
        logger.error(f"Error in normalize_path: {e}")
        return path


def create_directory(path: str) -> bool:
    logger.debug(f"Entering create_directory with path: {path}")
    """Create a directory at the specified path.

    Args:
        path: The path where to create the directory

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        logger.info(f"Directory created: {path}")
        return True
    except Exception as e:
        logger.error(f"Error creating directory: {e}")
        console.print(f"[bold red]Error creating directory: {e}[/]")
        return False


def get_directory_contents(path: str) -> List[str]:
    logger.debug(f"Entering get_directory_contents with path: {path}")
    """Get contents of a directory, separated into directories and files.

    Args:
        path: The directory path to list

    Returns:
        List[str]: List of directory entries, directories first followed by files
    """
    try:
        entries = os.listdir(path)
        dirs = []
        files = []

        for entry in entries:
            full_path = os.path.join(path, entry)
            if os.path.isdir(full_path):
                dirs.append(entry + os.sep)
            else:
                files.append(entry)

        logger.debug(f"Directory contents: {dirs + files}")
        return sorted(dirs) + sorted(files)
    except Exception as e:
        logger.error(f"Error listing directory: {e}")
        console.print(f"[bold red]Error listing directory: {e}[/]")
        return []


def validate_path(path: str) -> bool:
    logger.debug(f"Entering validate_path with path: {path}")
    """Validate that a path exists and is a directory.

    Args:
        path: The path to validate

    Returns:
        bool: True if the path is valid, False otherwise
    """
    try:
        is_valid = os.path.isdir(path)
        logger.debug(f"Path is valid: {is_valid}")
        return is_valid
    except Exception as e:
        logger.error(f"Error in validate_path: {e}")
        return False


def get_common_roots() -> List[str]:
    logger.debug("Entering get_common_roots.")
    """Get a list of common root directories based on the OS.

    Returns:
        List[str]: List of common root directories
    """
    try:
        system = platform.system()
        logger.debug(f"Detected system: {system}")

        if system == "Windows":
            import string

            drives = []
            for drive in string.ascii_uppercase:
                if os.path.exists(f"{drive}:"):
                    drives.append(f"{drive}:")
            logger.debug(f"Windows drives: {drives}")
            return drives

        elif system == "Darwin":
            roots = ["/", "/Users", "/Applications", "/Volumes"]
            logger.debug(f"Mac roots: {roots}")
            return roots

        else:
            roots = ["/", "/home", "/mnt", "/media"]
            logger.debug(f"Linux roots: {roots}")
            return roots
    except Exception as e:
        logger.error(f"Error in get_common_roots: {e}")
        return []


def browse_directory(
    start_path: Optional[str] = None, translator=None, title: Optional[str] = None
) -> Optional[str]:
    logger.debug(f"Entering browse_directory with start_path: {start_path}, title: {title}")
    """Browse directories and select one.

    Args:
        start_path: Starting directory. Ignored as we always start from root directories.
        translator: Translator instance for internationalization
        title: Optional title to display above the browser

    Returns:
        Optional[str]: The selected directory path or None if cancelled
    """
    if title is None:
        title = "Select a directory"

    _ = lambda text: text
    if translator is not None:
        _ = lambda text: translator.get(text) or text

    # Always start from root directories using get_common_roots()
    choices = get_common_roots()
    choices.append(MANUAL_ENTRY)

    selection = questionary.select(_(title), choices=choices, style=custom_style).ask()

    if selection == MANUAL_ENTRY:
        path = questionary.text(
            _("Enter a path:"),
            style=custom_style,
        ).ask()

        if not path:
            return None

        path = normalize_path(path)
        if validate_path(path):
            return path

        create_it = questionary.confirm(
            _("Path doesn't exist. Create it?"), default=True, style=custom_style
        ).ask()

        if create_it and create_directory(path):
            return path
        else:
            return browse_directory(None, translator, title)

    elif not selection:
        return None

    current_path = selection
    if (
        platform.system() == "Windows"
        and len(current_path) == 2
        and current_path[1] == ":"
    ):
        current_path = current_path + "\\"

    while True:
        if not os.path.exists(current_path):
            console.print(f"[bold red]{_('Path does not exist')}: {current_path}[/]")
            return browse_directory(None, translator, title)

        contents = get_directory_contents(current_path)

        choices = [f"[{_('SELECT THIS DIRECTORY')}] {current_path}"]

        if os.path.dirname(current_path) != current_path:
            choices.append(f"{PARENT_DIR} ({os.path.dirname(current_path)})")

        choices.append(CREATE_NEW)
        choices.append(MANUAL_ENTRY)
        choices.append(f"[{_('CANCEL')}]")

        for item in contents:
            if item.endswith(os.sep):
                choices.insert(len(choices) - 3, item)

        selection = questionary.select(
            _("Current directory") + f": {current_path}",
            choices=choices,
            style=custom_style,
        ).ask()

        if not selection:
            return None

        if selection.startswith(f"[{_('SELECT THIS DIRECTORY')}]"):
            return current_path

        if selection.startswith(f"[{_('CANCEL')}]"):
            return None

        if selection.startswith(PARENT_DIR):
            current_path = os.path.dirname(current_path)
            continue

        if selection == CREATE_NEW:
            dir_name = questionary.text(
                _("Enter new directory name:"),
                style=custom_style,
            ).ask()

            if not dir_name:
                continue

            new_dir_path = os.path.join(current_path, dir_name)
            if create_directory(new_dir_path):
                current_path = new_dir_path
            continue

        if selection == MANUAL_ENTRY:
            path = questionary.text(
                _("Enter a path:"),
                default=current_path,
                style=custom_style,
            ).ask()

            if not path:
                continue

            path = normalize_path(path)
            if validate_path(path):
                current_path = path
            else:
                create_it = questionary.confirm(
                    _("Path doesn't exist. Create it?"),
                    default=True,
                    style=custom_style,
                ).ask()

                if create_it and create_directory(path):
                    current_path = path
            continue

        new_path = os.path.join(current_path, selection.rstrip(os.sep))
        if os.path.isdir(new_path):
            current_path = new_path
