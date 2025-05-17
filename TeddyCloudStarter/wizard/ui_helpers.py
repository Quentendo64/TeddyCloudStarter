#!/usr/bin/env python3
"""
UI helpers for TeddyCloudStarter.
"""
import questionary
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..utilities.validation import validate_config
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


def show_welcome_message(translator):
    logger.debug("Entering show_welcome_message.")
    from .. import __version__
    logger.debug(f"Using version: {__version__}")
    try:
        console.print(
            Panel(
                f"[bold blue]{translator.get('TeddyCloudStarter')}[/] -[bold green] v{__version__} [/]- {translator.get('Docker Setup Wizard for TeddyCloud')}\n\n"
                f"{translator.get('This wizard will help you set up TeddyCloud with Docker.')}",
                box=box.ROUNDED,
                border_style="cyan",
            )
        )
        logger.info("Welcome message displayed successfully.")
    except Exception as e:
        logger.error(f"Error displaying welcome message: {e}")


def show_development_message(translator):
    logger.debug("Entering show_development_message.")
    try:
        console.print(
            Panel(
                f"[bold red]{translator.get('WARNING')}[/] - {translator.get('Early development state')}\n\n"
                f"[bold white]{translator.get('Keep in mind that this project is not finished yet.')}\n"
                f"[bold white]{translator.get('But it should bring you the concept of how it will work. Soon™')}",
                box=box.ROUNDED,
                border_style="red",
            )
        )
        logger.info("Development message displayed successfully.")
    except Exception as e:
        logger.error(f"Error displaying development message: {e}")


def _show_config_error(table, translator, missing_key, error_message):
    logger.debug(f"Entering _show_config_error with missing_key={missing_key}, error_message={error_message}")
    try:
        table.add_row(
            translator.get("Status"), f"[bold red]{translator.get('Corrupt Configuration')}"
        )
        table.add_row(translator.get("Missing Keys"), f"[red]{missing_key}")
        console.print(table)
        console.print(
            Panel(
                f"[bold red]{translator.get('WARNING')}[/] - {translator.get('Corrupt Configuration Detected')}\n\n"
                f"{translator.get(error_message)}\n",
                box=box.ROUNDED,
                border_style="red",
            )
        )
        logger.info("Config error displayed successfully.")
    except Exception as e:
        logger.error(f"Error displaying config error: {e}")
    return False


def _show_validation_errors(table, translator, errors):
    logger.debug(f"Entering _show_validation_errors with errors={errors}")
    try:
        table.add_row(
            translator.get("Status"), f"[bold red]{translator.get('Corrupt Configuration')}"
        )
        error_list = "\n".join([f"- {error}" for error in errors])
        table.add_row(translator.get("Validation Errors"), f"[red]{error_list}")
        console.print(table)
        console.print(
            Panel(
                f"[bold red]{translator.get('WARNING')}[/] - {translator.get('Configuration Validation Failed')}\n\n"
                f"{translator.get('Your configuration file contains errors:')}\n{error_list}\n\n"
                f"{translator.get('It is recommended to reset your configuration by choosing:')}\n"
                f"[bold white]{translator.get('Configuration management → Delete configuration and start over')}\n",
                box=box.ROUNDED,
                border_style="red",
            )
        )
        logger.info("Validation errors displayed successfully.")
    except Exception as e:
        logger.error(f"Error displaying validation errors: {e}")
    return False


def _display_direct_mode_config(table, config, translator):
    logger.debug("Entering _display_direct_mode_config.")
    try:
        if "ports" in config:
            for port_name, port_value in config["ports"].items():
                if port_value:
                    table.add_row(f"{translator.get('Port')}: {port_name}", str(port_value))
        logger.info("Direct mode config displayed successfully.")
    except Exception as e:
        logger.error(f"Error displaying direct mode config: {e}")


def _display_nginx_mode_config(table, config, translator):
    logger.debug("Entering _display_nginx_mode_config.")
    try:
        nginx_config = config["nginx"]
        if "nginx_type" in nginx_config:
            table.add_row(translator.get("Type"), nginx_config["nginx_type"])
        if "domain" in nginx_config:
            table.add_row(translator.get("Domain"), nginx_config["domain"])
        if "https_mode" in nginx_config:
            table.add_row(translator.get("HTTPS Mode"), nginx_config["https_mode"])
        if "security" in nginx_config and "type" in nginx_config["security"]:
            table.add_row(translator.get("Security Type"), nginx_config["security"]["type"])
            if (
                "allowed_ips" in nginx_config["security"]
                and nginx_config["security"]["allowed_ips"]
            ):
                table.add_row(
                    translator.get("Allowed IPs"),
                    ", ".join(nginx_config["security"]["allowed_ips"]),
                )
            if (
                nginx_config["security"]["type"] == "basic_auth"
                and "auth_bypass_ips" in nginx_config["security"]
                and nginx_config["security"]["auth_bypass_ips"]
            ):
                table.add_row(
                    translator.get("Auth Bypass IPs"),
                    ", ".join(nginx_config["security"]["auth_bypass_ips"]),
                )
        logger.info("Nginx mode config displayed successfully.")
    except Exception as e:
        logger.error(f"Error displaying nginx mode config: {e}")


def display_configuration_table(config, translator):
    logger.debug("Entering display_configuration_table.")
    table = Table(title=translator.get("Current Configuration"), box=box.ROUNDED)
    table.add_column(translator.get("Setting"), style="cyan")
    table.add_column(translator.get("Value"), style="green")
    try:
        is_valid, errors = validate_config(config, translator)
        logger.debug(f"Validation result: is_valid={is_valid}, errors={errors}")
        if not is_valid:
            logger.warning("Configuration is not valid. Displaying validation errors.")
            return _show_validation_errors(table, translator, errors)
        table.add_row(translator.get("Mode"), config["mode"])
        if config["mode"] == "direct":
            _display_direct_mode_config(table, config, translator)
        elif config["mode"] == "nginx" and "nginx" in config:
            _display_nginx_mode_config(table, config, translator)
        console.print(table)
        logger.info("Configuration table displayed successfully.")
        return True
    except Exception as e:
        logger.error(f"Error displaying configuration table: {e}")
        return False
