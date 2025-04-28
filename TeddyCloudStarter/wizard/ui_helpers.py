#!/usr/bin/env python3
"""
UI helpers for TeddyCloudStarter.
"""
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
import questionary

# Global console instance for rich output
console = Console()

# Custom style for questionary
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

def show_welcome_message(translator):
    """
    Show welcome message.
    
    Args:
        translator: The translator instance to use for localization
    """
    from .. import __version__
    console.print(Panel(
        f"[bold blue]{translator.get('TeddyCloudStarter')}[/] -[bold green] v{__version__} [/]- {translator.get('Docker Setup Wizard for TeddyCloud')}\n\n"
        f"{translator.get('This wizard will help you set up TeddyCloud with Docker.')}",
        box=box.ROUNDED,
        border_style="cyan"
    ))

def show_development_message(translator):
    """
    Show developer message.
    
    Args:
        translator: The translator instance to use for localization
    """
    console.print(Panel(
        f"[bold red]{translator.get('WARNING')}[/] - {translator.get('Early development state')}\n\n"
        f"[bold white]{translator.get('Keep in mind that this project is not finished yet.')}\n"
        f"[bold white]{translator.get('But it should bring you the concept of how it will work. Soon™')}",
        box=box.ROUNDED,
        border_style="red"
    ))

def _show_config_error(table, translator, missing_key, error_message):
    """
    Helper function to display configuration errors.
    
    Args:
        table: Rich table object to add error rows to
        translator: The translator instance to use for localization
        missing_key: Key or keys that are missing from the configuration
        error_message: Specific error message to display
    
    Returns:
        False to indicate configuration error
    """
    table.add_row(translator.get("Status"), f"[bold red]{translator.get('Corrupt Configuration')}")
    table.add_row(translator.get("Missing Keys"), f"[red]{missing_key}")
    console.print(table)
    console.print(Panel(
        f"[bold red]{translator.get('WARNING')}[/] - {translator.get('Corrupt Configuration Detected')}\n\n"
        f"{translator.get(error_message)}\n",
        box=box.ROUNDED,
        border_style="red"
    ))
    return False

def _display_direct_mode_config(table, config, translator):
    """
    Display direct mode configuration in the table.
    
    Args:
        table: Rich table object to add rows to
        config: Configuration dictionary
        translator: The translator instance to use for localization
    """
    # Check if ports exist in config
    if "ports" in config:
        for port_name, port_value in config["ports"].items():
            if port_value:  # Only show ports that are set
                table.add_row(f"{translator.get('Port')}: {port_name}", str(port_value))

def _display_nginx_mode_config(table, config, translator):
    """
    Display nginx mode configuration in the table.
    
    Args:
        table: Rich table object to add rows to
        config: Configuration dictionary
        translator: The translator instance to use for localization
    """
    # Only access nginx data if the key exists
    nginx_config = config["nginx"]
    if "domain" in nginx_config:
        table.add_row(translator.get("Domain"), nginx_config["domain"])
    if "https_mode" in nginx_config:
        table.add_row(translator.get("HTTPS Mode"), nginx_config["https_mode"])
    if "security" in nginx_config and "type" in nginx_config["security"]:
        table.add_row(translator.get("Security Type"), nginx_config["security"]["type"])
        if "allowed_ips" in nginx_config["security"] and nginx_config["security"]["allowed_ips"]:
            table.add_row(translator.get("Allowed IPs"), ", ".join(nginx_config["security"]["allowed_ips"]))

def display_configuration_table(config, translator):
    """
    Display current configuration in a table.
    
    Args:
        config: The current configuration dictionary
        translator: The translator instance to use for localization
    
    Returns:
        True if configuration is valid and displayed, False otherwise
    """
    table = Table(title=translator.get("Current Configuration"), box=box.ROUNDED)
    table.add_column(translator.get("Setting"), style="cyan")
    table.add_column(translator.get("Value"), style="green")
    
    # Validate basic configuration
    required_keys = ["mode"]
    missing_keys = [key for key in required_keys if key not in config]
    
    if missing_keys:
        return _show_config_error(
            table, 
            translator, 
            ', '.join(missing_keys),
            'Your configuration file is missing critical data. It is recommended to reset your configuration by choosing: Configuration management → Delete configuration and start over'
        )
    
    # Check mode-specific required keys
    if config["mode"] == "direct" and "ports" not in config:
        return _show_config_error(table, translator, "ports", "Direct mode configuration is missing ports data.")
    
    if config["mode"] == "nginx" and "nginx" not in config:
        return _show_config_error(table, translator, "nginx", "Nginx mode configuration is missing nginx data.")

    # Display available configuration data
    table.add_row(translator.get("Mode"), config["mode"])

    # Display mode-specific configuration
    if config["mode"] == "direct":
        _display_direct_mode_config(table, config, translator)
    elif config["mode"] == "nginx" and "nginx" in config:
        _display_nginx_mode_config(table, config, translator)

    console.print(table)
    return True