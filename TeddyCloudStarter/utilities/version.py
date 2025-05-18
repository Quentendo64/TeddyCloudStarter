#!/usr/bin/env python3
"""
Version handling utilities for TeddyCloudStarter.
"""

import json
import subprocess
import sys
from urllib import request
from urllib.error import URLError
from packaging import version
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm


from .. import __version__
from ..utilities.logger import logger

console = Console()


def get_pypi_version():
    logger.debug("Checking latest version from PyPI.")
    try:
        with request.urlopen(
            "https://pypi.org/pypi/TeddyCloudStarter/json", timeout=2
        ) as response:
            logger.debug("Received response from PyPI.")
            pypi_data = json.loads(response.read().decode("utf-8"))
            latest_version = pypi_data["info"]["version"]
            logger.info(f"Latest version from PyPI: {latest_version}")
            return latest_version, None
    except (URLError, json.JSONDecodeError) as e:
        logger.error(f"Failed to check for updates: {str(e)}")
        return __version__, f"Failed to check for updates: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error checking for updates: {str(e)}")
        return __version__, f"Unexpected error checking for updates: {str(e)}"


def compare_versions(v1, v2):
    logger.debug(f"Comparing versions: v1={v1}, v2={v2}")
    try:
        parsed_v1 = version.parse(v1)
        parsed_v2 = version.parse(v2)
        logger.debug(f"Parsed versions: v1={parsed_v1}, v2={parsed_v2}")
        
        if parsed_v1 < parsed_v2:
            logger.info("v1 is less than v2")
            return -1
        elif parsed_v1 > parsed_v2:
            logger.info("v1 is greater than v2")
            return 1
        else:
            logger.info("Versions are equal")
            return 0
    except Exception as e:
        logger.error(f"Error comparing versions: {e}")
        return 0


def check_for_updates(quiet=False):
    """
    Check for updates to TeddyCloudStarter package on PyPI.
    
    Returns:
        bool: True if up to date, False if updates are available
    """
    logger.debug(f"Checking for updates. quiet={quiet}")
    current_version = __version__
    update_confirmed = False
    latest_version, error = get_pypi_version()
    logger.debug(f"Current version: {current_version}, Latest version: {latest_version}, Error: {error}")
    if error:
        logger.warning(f"Error while checking for updates: {error}")
        return True, current_version, error, update_confirmed
    compare_result = compare_versions(current_version, latest_version)
    is_latest = compare_result >= 0
    logger.debug(f"Compare result: {compare_result}, is_latest: {is_latest}")
    if is_latest:
        message = (
            f"You are using the latest version of TeddyCloudStarter ({current_version})"
        )
        logger.info(message)
    else:
        message = f"Update available! Current version: {current_version}, Latest version: {latest_version}"
        logger.info(message)
        if not quiet:
            try:
                from ..config_manager import ConfigManager
                auto_update = ConfigManager.get_auto_update_setting()
                logger.debug(f"Auto-update setting: {auto_update}")
            except (ImportError, AttributeError) as e:
                logger.warning(f"Could not get auto-update setting: {e}")
                auto_update = False
            console.print(
                Panel(
                    f"[bold yellow]Update Available![/]\n\n"
                    f"Current version: [cyan]{current_version}[/]\n"
                    f"Latest version: [green]{latest_version}[/]",
                    box=box.ROUNDED,
                    border_style="yellow",
                )
            )
            if auto_update:
                update_confirmed = True
                logger.info("Auto-update is enabled. Installing update automatically...")
                console.print(
                    "[bold cyan]Auto-update is enabled. Installing update automatically...[/]"
                )
            else:
                try:
                    update_confirmed = Confirm.ask(
                        f"Do you want to upgrade to TeddyCloudStarter {latest_version}?",
                        default=False,
                    )
                    logger.info(f"User update confirmation: {update_confirmed}")
                except (EOFError, KeyboardInterrupt):
                    update_confirmed = False
                    logger.warning("User cancelled update confirmation prompt.")
            if update_confirmed:
                console.print("[bold cyan]Attempting to install update...[/]")
                logger.info("Attempting to install update...")
                if install_update():
                    logger.info(f"Successfully updated to TeddyCloudStarter {latest_version}")
                    console.print(
                        f"[bold green]Successfully updated to TeddyCloudStarter {latest_version}[/]"
                    )
                    console.print(
                        "[cyan]Exiting program. Please restart TeddyCloudStarter to use the new version.[/]"
                    )
                    sys.exit(0)
                else:
                    logger.error("Failed to install update automatically.")
                    console.print("[bold red]Failed to install update automatically[/]")
                    console.print(
                        "[yellow]Please update manually using: pip install --upgrade TeddyCloudStarter[/]"
                    )
                    sys.exit(1)
            else:
                logger.info("Update skipped by user.")
                console.print("[yellow]Update skipped by user.[/]")
    return is_latest, latest_version, message, update_confirmed


def install_update():
    logger.debug("Attempting to install update using pip, pip3, or pipx.")
    package_name = "TeddyCloudStarter"
    commands = [
        [sys.executable, "-m", "pip", "install", "--upgrade", package_name],
        ["pip", "install", "--upgrade", package_name],
        ["pip3", "install", "--upgrade", package_name],
        ["pipx", "upgrade", package_name],
    ]
    for cmd in commands:
        try:
            logger.debug(f"Running update command: {' '.join(cmd)}")
            console.print(
                f"[cyan]Attempting to install update using: {' '.join(cmd)}[/]"
            )
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)
            logger.debug(f"Update command result: returncode={result.returncode}, stderr={result.stderr.strip()}")
            if result.returncode == 0:
                logger.info(f"Update command succeeded: {' '.join(cmd)}")
                return True
            else:
                logger.warning(f"Command failed with code {result.returncode}: {result.stderr}")
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {' '.join(cmd)}")
        except Exception as e:
            logger.error(f"Exception running update command {' '.join(cmd)}: {e}")
    
    logger.error("All update commands failed.")
    return False
