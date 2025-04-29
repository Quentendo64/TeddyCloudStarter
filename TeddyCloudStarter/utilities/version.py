#!/usr/bin/env python3
"""
Version handling utilities for TeddyCloudStarter.
"""

import json
import os
from urllib import request
from urllib.error import URLError
import sys
from rich.console import Console
from rich.panel import Panel
from rich import box
from rich.prompt import Confirm
import subprocess
from .. import __version__

# Global console instance for rich output
console = Console()


def get_pypi_version():
    """
    Get the latest version of TeddyCloudStarter from PyPI.
    
    Returns:
        tuple: (latest_version, None) on success, (current_version, error_message) on failure
    """
    try:
        # Fetch from PyPI
        with request.urlopen("https://pypi.org/pypi/TeddyCloudStarter/json", timeout=2) as response:
            pypi_data = json.loads(response.read().decode("utf-8"))
            latest_version = pypi_data["info"]["version"]
            return latest_version, None
            
    except (URLError, json.JSONDecodeError) as e:
        return __version__, f"Failed to check for updates: {str(e)}"
    except Exception as e:
        return __version__, f"Unexpected error checking for updates: {str(e)}"


def compare_versions(v1, v2):
    """
    Compare two version strings.
    
    Args:
        v1: First version string
        v2: Second version string
        
    Returns:
        int: -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
    """
    try:
        v1_parts = [int(x) for x in v1.split('.')]
        v2_parts = [int(x) for x in v2.split('.')]
        
        for i in range(max(len(v1_parts), len(v2_parts))):
            v1_part = v1_parts[i] if i < len(v1_parts) else 0
            v2_part = v2_parts[i] if i < len(v2_parts) else 0
            
            if v1_part < v2_part:
                return -1
            elif v1_part > v2_part:
                return 1
        
        return 0
    except Exception:
        # On error, assume versions are equal
        return 0


def check_for_updates(quiet=False):
    """
    Check if the current version of TeddyCloudStarter is the latest.
    
    Args:
        quiet: If True, will not display any information messages and skip user confirmation
        
    Returns:
        tuple: (is_latest, latest_version, message, update_confirmed)
            is_latest: boolean indicating if the current version is the latest
            latest_version: string with the latest version
            message: string message about the update status or error
            update_confirmed: boolean indicating if the user confirmed the update
    """
    current_version = __version__
    update_confirmed = False
    
    latest_version, error = get_pypi_version()
    
    if error:
        return True, current_version, error, update_confirmed
        
    compare_result = compare_versions(current_version, latest_version)
    is_latest = compare_result >= 0  # current >= latest
    
    if is_latest:
        message = f"You are using the latest version of TeddyCloudStarter ({current_version})"
    else:
        message = f"Update available! Current version: {current_version}, Latest version: {latest_version}"
        if not quiet:
            # Check if auto_update is enabled in config
            try:
                from ..config_manager import ConfigManager
                auto_update = ConfigManager.get_auto_update_setting()
            except (ImportError, AttributeError):
                auto_update = False
            
            console.print(Panel(
                f"[bold yellow]Update Available![/]\n\n"
                f"Current version: [cyan]{current_version}[/]\n"
                f"Latest version: [green]{latest_version}[/]",
                box=box.ROUNDED,
                border_style="yellow"
            ))
            
            if auto_update:
                update_confirmed = True
                console.print("[bold cyan]Auto-update is enabled. Installing update automatically...[/]")
            else:
                try:
                    update_confirmed = Confirm.ask(
                        f"Do you want to upgrade to TeddyCloudStarter {latest_version}?",
                        default=False
                    )
                except (EOFError, KeyboardInterrupt):
                    update_confirmed = False
            
            if update_confirmed:
                console.print("[bold cyan]Attempting to install update...[/]")
                if install_update():
                    console.print(f"[bold green]Successfully updated to TeddyCloudStarter {latest_version}[/]")
                    console.print("[cyan]Exiting program. Please restart TeddyCloudStarter to use the new version.[/]")
                    sys.exit(0)
                else:
                    console.print("[bold red]Failed to install update automatically[/]")
                    console.print("[yellow]Please update manually using: pip install --upgrade TeddyCloudStarter[/]")
                    sys.exit(1)
            else:
                console.print("[yellow]Update skipped by user.[/]")
    
    return is_latest, latest_version, message, update_confirmed


def install_update():
    """
    Try to install the update using pip, pip3, or pipx.
    
    Returns:
        bool: True if the update was successfully installed, False otherwise
    """
    package_name = "TeddyCloudStarter"
    commands = [
        [sys.executable, "-m", "pip", "install", "--upgrade", package_name],
        ["pip", "install", "--upgrade", package_name],
        ["pip3", "install", "--upgrade", package_name],
        ["pipx", "upgrade", package_name]
    ]
    
    for cmd in commands:
        try:
            console.print(f"[cyan]Attempting to install update using: {' '.join(cmd)}[/]")
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                return True
        except Exception:
            pass
    
    return False
