#!/usr/bin/env python3
"""
UI helpers for TeddyCloudStarter.
"""
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
import questionary
from ..utilities.validation import validate_config

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

def _show_validation_errors(table, translator, errors):
    """
    Helper function to display validation errors.
    
    Args:
        table: Rich table object to add error rows to
        translator: The translator instance to use for localization
        errors: List of error messages
    
    Returns:
        False to indicate configuration error
    """
    table.add_row(translator.get("Status"), f"[bold red]{translator.get('Corrupt Configuration')}")
    error_list = "\n".join([f"- {error}" for error in errors])
    table.add_row(translator.get("Validation Errors"), f"[red]{error_list}")
    console.print(table)
    console.print(Panel(
        f"[bold red]{translator.get('WARNING')}[/] - {translator.get('Configuration Validation Failed')}\n\n"
        f"{translator.get('Your configuration file contains errors:')}\n{error_list}\n\n"
        f"{translator.get('It is recommended to reset your configuration by choosing:')}\n"
        f"[bold white]{translator.get('Configuration management → Delete configuration and start over')}\n",
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
        # Display auth bypass IPs if they exist and security type is basic_auth
        if (nginx_config["security"]["type"] == "basic_auth" and 
            "auth_bypass_ips" in nginx_config["security"] and 
            nginx_config["security"]["auth_bypass_ips"]):
            table.add_row(translator.get("Auth Bypass IPs"), ", ".join(nginx_config["security"]["auth_bypass_ips"]))

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
    
    # Use the centralized validation system
    is_valid, errors = validate_config(config, translator)
    
    if not is_valid:
        return _show_validation_errors(table, translator, errors)
    
    # Display available configuration data
    table.add_row(translator.get("Mode"), config["mode"])

    # Display mode-specific configuration
    if config["mode"] == "direct":
        _display_direct_mode_config(table, config, translator)
    elif config["mode"] == "nginx" and "nginx" in config:
        _display_nginx_mode_config(table, config, translator)

    console.print(table)
    return True