#!/usr/bin/env python3
"""
File system utility functions for TeddyCloudStarter.
"""
import os
import platform
from pathlib import Path
import questionary
from typing import Optional, List
from rich.console import Console

# Global console instance for rich output
console = Console()

# Custom style for questionary (matching the wizard style)
custom_style = questionary.Style([
    ('qmark', 'fg:#673ab7 bold'),       # Purple question mark
    ('question', 'bold'),               # Bold question text
    ('answer', 'fg:#4caf50 bold'),      # Green answer text
    ('pointer', 'fg:#673ab7 bold'),     # Purple pointer
    ('highlighted', 'fg:#673ab7 bold'), # Purple highlighted option
    ('selected', 'fg:#4caf50'),         # Green selected option
    ('separator', 'fg:#673ab7'),        # Purple separator
    ('instruction', 'fg:#f44336'),      # Red instruction text
])

# Special directory marker for navigation
PARENT_DIR = ".."
CREATE_NEW = "[Create new folder]"
MANUAL_ENTRY = "[Enter path manually]"


def get_project_path(config_manager=None):
    """
    Get the project path from config or return None if not set.
    
    Args:
        config_manager: The configuration manager instance
        
    Returns:
        str: The project path, or None if not set
    """
    try:
        if config_manager and config_manager.config:
            return config_manager.config.get("environment", {}).get("path")
        return None
    except Exception:
        return None


def ensure_project_directories(project_path=None):
    """
    Create necessary directories in the project path if provided, otherwise in current working directory.
    
    Args:
        project_path: The path to the project directory
    """
    base_path = Path(project_path) if project_path else Path.cwd()
    (base_path / "data").mkdir(exist_ok=True)
    (base_path / "data" / "configurations").mkdir(exist_ok=True)
    (base_path / "data" / "backup").mkdir(exist_ok=True)


def normalize_path(path: str) -> str:
    """Normalize a file path by resolving ../ and ./ references.
    
    Args:
        path: The path to normalize
        
    Returns:
        str: The normalized path
    """
    return os.path.normpath(path)


def create_directory(path: str) -> bool:
    """Create a directory at the specified path.
    
    Args:
        path: The path where to create the directory
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        console.print(f"[bold red]Error creating directory: {e}[/]")
        return False


def get_directory_contents(path: str) -> List[str]:
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
                dirs.append(entry + os.sep)  # Add separator to indicate directory
            else:
                files.append(entry)
                
        # Sort alphabetically and put directories first
        return sorted(dirs) + sorted(files)
    except Exception as e:
        console.print(f"[bold red]Error listing directory: {e}[/]")
        return []


def validate_path(path: str) -> bool:
    """Validate that a path exists and is a directory.
    
    Args:
        path: The path to validate
        
    Returns:
        bool: True if the path is valid, False otherwise
    """
    return os.path.isdir(path)


# Get common root directories based on operating system
def get_common_roots() -> List[str]:
    """Get a list of common root directories based on the OS.
    
    Returns:
        List[str]: List of common root directories
    """
    system = platform.system()
    
    if system == "Windows":
        import string
        # Get all available drive letters
        drives = []
        for drive in string.ascii_uppercase:
            if os.path.exists(f"{drive}:"):
                drives.append(f"{drive}:")
        return drives
    
    elif system == "Darwin":  # macOS
        return ["/", "/Users", "/Applications", "/Volumes"]
    
    else:  # Linux and others
        return ["/", "/home", "/mnt", "/media"]


def browse_directory(start_path: Optional[str] = None, 
                     translator=None, 
                     title: Optional[str] = None) -> Optional[str]:
    """Browse directories and select one.
    
    Args:
        start_path: Starting directory. If None, common roots will be shown.
        translator: Translator instance for internationalization
        title: Optional title to display above the browser
        
    Returns:
        Optional[str]: The selected directory path or None if cancelled
    """
    # Set default title if not provided
    if title is None:
        title = "Select a directory"
    
    # Default translation function
    _ = lambda text: text
    if translator is not None:
        _ = lambda text: translator.get(text) or text
    
    # If no start path, show common roots
    if not start_path:
        choices = get_common_roots()
        choices.append(MANUAL_ENTRY)
        
        selection = questionary.select(
            _(title),
            choices=choices,
            style=custom_style
        ).ask()
        
        if selection == MANUAL_ENTRY:
            # Allow manual entry of a path
            path = questionary.text(
                _("Enter a path:"),
                style=custom_style,
            ).ask()
            
            if not path:
                return None
            
            # Normalize and validate the path
            path = normalize_path(path)
            if validate_path(path):
                return path
            
            # Path doesn't exist, ask to create it
            create_it = questionary.confirm(
                _("Path doesn't exist. Create it?"),
                default=True,
                style=custom_style
            ).ask()
            
            if create_it and create_directory(path):
                return path
            else:
                # Try again
                return browse_directory(None, translator, title)
        
        elif not selection:
            return None
        
        # Start browsing from the selected root
        start_path = selection
        # Fix for Windows drives - ensure they have a trailing slash to show root contents
        if platform.system() == "Windows" and len(start_path) == 2 and start_path[1] == ':':
            start_path = start_path + '\\'
    
    # Main directory browsing loop
    current_path = normalize_path(start_path)
    
    # Additional fix for Windows root paths that might have lost their trailing slash during normalization
    if platform.system() == "Windows" and len(current_path) == 2 and current_path[1] == ':':
        current_path = current_path + '\\'
        
    while True:
        # Check if the path exists
        if not os.path.exists(current_path):
            console.print(f"[bold red]{_('Path does not exist')}: {current_path}[/]")
            return browse_directory(None, translator, title)
        
        # Get directory contents
        contents = get_directory_contents(current_path)
        
        # Add navigation and action options
        choices = [f"[{_('SELECT THIS DIRECTORY')}] {current_path}"]
        
        if os.path.dirname(current_path) != current_path:  # Not at root
            choices.append(f"{PARENT_DIR} ({os.path.dirname(current_path)})")
        
        choices.append(CREATE_NEW)
        choices.append(MANUAL_ENTRY)
        choices.append(f"[{_('CANCEL')}]")
        
        # Add directory contents
        for item in contents:
            if item.endswith(os.sep):  # Directory
                choices.insert(len(choices) - 3, item)
        
        # Prompt user for selection
        selection = questionary.select(
            _("Current directory") + f": {current_path}",
            choices=choices,
            style=custom_style,
        ).ask()
        
        if not selection:
            return None
        
        if selection.startswith(f"[{_('SELECT THIS DIRECTORY')}]"):
            # User selected current directory
            return current_path
        
        if selection.startswith(f"[{_('CANCEL')}]"):
            # User cancelled
            return None
        
        if selection.startswith(PARENT_DIR):
            # Navigate to parent directory
            current_path = os.path.dirname(current_path)
            continue
        
        if selection == CREATE_NEW:
            # Create new directory
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
            # Allow manual entry of a path
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
                # Path doesn't exist, ask to create it
                create_it = questionary.confirm(
                    _("Path doesn't exist. Create it?"),
                    default=True,
                    style=custom_style
                ).ask()
                
                if create_it and create_directory(path):
                    current_path = path
            continue
        
        # Navigate into selected directory
        new_path = os.path.join(current_path, selection.rstrip(os.sep))
        if os.path.isdir(new_path):
            current_path = new_path
