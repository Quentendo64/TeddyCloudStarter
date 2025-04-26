#!/usr/bin/env python3
"""
UI helpers for TeddyCloudStarter.
"""
from rich.console import Console
from rich.panel import Panel
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

def display_configuration_table(config, translator):
    """
    Display current configuration in a table.
    
    Args:
        config: The current configuration dictionary
        translator: The translator instance to use for localization
    """
    from rich.table import Table
    
    table = Table(title=translator.get("Current Configuration"), box=box.ROUNDED)
    table.add_column(translator.get("Setting"), style="cyan")
    table.add_column(translator.get("Value"), style="green")
    
    # Check for required keys
    required_keys = ["mode"]
    missing_keys = [key for key in required_keys if key not in config]
    
    if missing_keys:
        # Configuration seems to be corrupt, show error
        table.add_row(translator.get("Status"), f"[bold red]{translator.get('Corrupt Configuration')}")
        table.add_row(translator.get("Missing Keys"), f"[red]{', '.join(missing_keys)}")
        console.print(table)
        
        # Show warning panel
        console.print(Panel(
            f"[bold red]{translator.get('WARNING')}[/] - {translator.get('Corrupt Configuration Detected')}\n\n"
            f"{translator.get('Your configuration file is missing critical data.')}\n"
            f"{translator.get('It is recommended to reset your configuration by choosing:')}\n"
            f"[bold white]{translator.get('Configuration management → Delete configuration and start over')}\n",
            box=box.ROUNDED,
            border_style="red"
        ))
        return False
    
    # Check other required keys based on mode
    if config["mode"] == "direct" and "ports" not in config:
        table.add_row(translator.get("Status"), f"[bold red]{translator.get('Corrupt Configuration')}")
        table.add_row(translator.get("Missing Keys"), f"[red]ports")
        console.print(table)
        console.print(Panel(
            f"[bold red]{translator.get('WARNING')}[/] - {translator.get('Corrupt Configuration Detected')}\n\n"
            f"{translator.get('Direct mode configuration is missing ports data.')}\n",
            box=box.ROUNDED,
            border_style="red"
        ))
        return False
    
    if config["mode"] == "nginx" and "nginx" not in config:
        table.add_row(translator.get("Status"), f"[bold red]{translator.get('Corrupt Configuration')}")
        table.add_row(translator.get("Missing Keys"), f"[red]nginx")
        console.print(table)
        console.print(Panel(
            f"[bold red]{translator.get('WARNING')}[/] - {translator.get('Corrupt Configuration Detected')}\n\n"
            f"{translator.get('Nginx mode configuration is missing nginx data.')}\n",
            box=box.ROUNDED,
            border_style="red"
        ))
        return False

    # Display available configuration data
    table.add_row(translator.get("Mode"), config["mode"])

    if config["mode"] == "direct":
        # Check if ports exist in config
        if "ports" in config:
            for port_name, port_value in config["ports"].items():
                if port_value:  # Only show ports that are set
                    table.add_row(f"{translator.get('Port')}: {port_name}", str(port_value))
    elif config["mode"] == "nginx" and "nginx" in config:
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

    console.print(table)
    return True