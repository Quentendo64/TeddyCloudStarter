#!/usr/bin/env python3
"""
Direct mode configuration for TeddyCloudStarter.
"""
from ..ui.direct_mode_ui import (
    confirm_custom_http_port,
    confirm_custom_https_port,
    confirm_custom_teddycloud_port,
    confirm_no_admin_interface,
    confirm_port_usage_anyway,
    confirm_use_http,
    confirm_use_https,
    prompt_for_http_port,
    prompt_for_https_port,
    prompt_for_teddycloud_port,
)
from ..utilities.network import check_port_available
from ..wizard.ui_helpers import console
from ..utilities.logger import logger


def configure_direct_mode(config, translator):
    """
    Configure direct deployment mode settings.

    Args:
        config: The configuration dictionary
        translator: The translator instance for localization

    Returns:
        dict: The updated configuration dictionary
    """
    logger.info("Starting direct mode configuration.")
    if "ports" not in config:
        config["ports"] = {"admin_http": None, "admin_https": None, "teddycloud": None}
        logger.debug(f"Initialized ports in config: {config['ports']}")

    ports = config["ports"]

    logger.debug("Configuring HTTP port.")
    _configure_http_port(ports, translator)

    logger.debug("Configuring HTTPS port.")
    _configure_https_port(ports, translator)

    logger.debug("Configuring TeddyCloud backend port.")
    _configure_teddycloud_port(ports, translator)

    if not ports["admin_http"] and not ports["admin_https"]:
        logger.warning("No admin interface ports enabled. Asking user to confirm.")
        if not confirm_no_admin_interface(translator):
            logger.info("User chose to reconfigure admin interface ports.")
            return configure_direct_mode(config, translator)

    logger.success(f"Direct mode configuration complete: {ports}")
    return config


def _configure_http_port(ports, translator):
    """
    Configure HTTP port for direct mode.

    Args:
        ports: The ports configuration dictionary
        translator: The translator instance for localization
    """
    current_port = ports["admin_http"]
    logger.debug(f"Current HTTP port: {current_port}")

    use_http = confirm_use_http(True, translator)
    logger.info(f"User chose to {'enable' if use_http else 'disable'} HTTP interface.")

    if use_http:
        port_80_available = check_port_available(80)
        logger.debug(f"Port 80 available: {port_80_available}")
        if not port_80_available:
            logger.warning("Port 80 appears to be in use.")
            console.print(
                f"[bold yellow]{translator.get('Warning')}: {translator.get('Port 80 appears to be in use')}.[/]"
            )
            custom_port = confirm_custom_http_port(translator)
            logger.info(f"User chose to {'specify a custom HTTP port' if custom_port else 'use port 80 anyway'}.")

            if custom_port:
                http_port = prompt_for_http_port("8080", translator)
                logger.info(f"User specified custom HTTP port: {http_port}")
                ports["admin_http"] = int(http_port)
            else:
                ports["admin_http"] = 80
        else:
            ports["admin_http"] = 80
        logger.success(f"HTTP port set to {ports['admin_http']}")
    else:
        ports["admin_http"] = None
        logger.info("HTTP interface disabled.")


def _configure_https_port(ports, translator):
    """
    Configure HTTPS port for direct mode.

    Args:
        ports: The ports configuration dictionary
        translator: The translator instance for localization
    """
    use_https = confirm_use_https(True, translator)
    logger.info(f"User chose to {'enable' if use_https else 'disable'} HTTPS interface.")

    if use_https:
        port_8443_available = check_port_available(8443)
        logger.debug(f"Port 8443 available: {port_8443_available}")
        if not port_8443_available:
            logger.warning("Port 8443 appears to be in use.")
            console.print(
                f"[bold yellow]{translator.get('Warning')}: {translator.get('Port 8443 appears to be in use')}.[/]"
            )
            custom_port = confirm_custom_https_port(translator)
            logger.info(f"User chose to {'specify a custom HTTPS port' if custom_port else 'use port 8443 anyway'}.")

            if custom_port:
                https_port = prompt_for_https_port("8444", translator)
                logger.info(f"User specified custom HTTPS port: {https_port}")
                ports["admin_https"] = int(https_port)
            else:
                ports["admin_https"] = 8443
        else:
            ports["admin_https"] = 8443
        logger.success(f"HTTPS port set to {ports['admin_https']}")
    else:
        ports["admin_https"] = None
        logger.info("HTTPS interface disabled.")


def _configure_teddycloud_port(ports, translator):
    """
    Configure TeddyCloud backend port for direct mode.

    Args:
        ports: The ports configuration dictionary
        translator: The translator instance for localization
    """
    port_443_available = check_port_available(443)
    logger.debug(f"Port 443 available: {port_443_available}")
    if not port_443_available:
        logger.warning("Port 443 appears to be in use.")
        console.print(
            f"[bold yellow]{translator.get('Warning')}: {translator.get('Port 443 appears to be in use')}.[/]"
        )
        custom_port = confirm_custom_teddycloud_port(translator)
        logger.info(f"User chose to {'specify a custom TeddyCloud port' if custom_port else 'use port 443 anyway'}.")

        if custom_port:
            tc_port = prompt_for_teddycloud_port("4443", translator)
            logger.info(f"User specified custom TeddyCloud port: {tc_port}")
            ports["teddycloud"] = int(tc_port)
        else:
            ports["teddycloud"] = 443
    else:
        ports["teddycloud"] = 443
    logger.success(f"TeddyCloud backend port set to {ports['teddycloud']}")


def modify_http_port(config, translator):
    """
    Modify HTTP port for direct mode.

    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
    """
    ports = config["ports"]
    current_port = ports["admin_http"]

    logger.info(f"Modifying HTTP port. Current: {current_port}")
    console.print(
        f"[bold cyan]{translator.get('Current HTTP port')}: {current_port or translator.get('Not enabled')}[/]"
    )

    use_http = confirm_use_http(current_port is not None, translator)
    logger.info(f"User chose to {'enable' if use_http else 'disable'} HTTP interface.")

    if use_http:
        default_port = str(current_port) if current_port else "80"
        http_port = prompt_for_http_port(default_port, translator)
        logger.info(f"User specified HTTP port: {http_port}")

        new_port = int(http_port)
        if new_port != current_port and not check_port_available(new_port):
            logger.warning(f"Port {new_port} appears to be in use.")
            if not confirm_port_usage_anyway(new_port, translator):
                logger.info("User chose not to use the port. Restarting HTTP port modification.")
                return modify_http_port(config, translator)

        ports["admin_http"] = new_port
        logger.success(f"HTTP port updated to {new_port}")
        console.print(
            f"[bold green]{translator.get('HTTP port updated to')} {new_port}[/]"
        )
    else:
        ports["admin_http"] = None
        logger.info("HTTP interface disabled.")
        console.print(f"[bold green]{translator.get('HTTP interface disabled')}[/]")

    return config


def modify_https_port(config, translator):
    """
    Modify HTTPS port for direct mode.

    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
    """
    ports = config["ports"]
    current_port = ports["admin_https"]

    logger.info(f"Modifying HTTPS port. Current: {current_port}")
    console.print(
        f"[bold cyan]{translator.get('Current HTTPS port')}: {current_port or translator.get('Not enabled')}[/]"
    )

    use_https = confirm_use_https(current_port is not None, translator)
    logger.info(f"User chose to {'enable' if use_https else 'disable'} HTTPS interface.")

    if use_https:
        default_port = str(current_port) if current_port else "8443"
        https_port = prompt_for_https_port(default_port, translator)
        logger.info(f"User specified HTTPS port: {https_port}")

        new_port = int(https_port)
        if new_port != current_port and not check_port_available(new_port):
            logger.warning(f"Port {new_port} appears to be in use.")
            if not confirm_port_usage_anyway(new_port, translator):
                logger.info("User chose not to use the port. Restarting HTTPS port modification.")
                return modify_https_port(config, translator)

        ports["admin_https"] = new_port
        logger.success(f"HTTPS port updated to {new_port}")
        console.print(
            f"[bold green]{translator.get('HTTPS port updated to')} {new_port}[/]"
        )
    else:
        ports["admin_https"] = None
        logger.info("HTTPS interface disabled.")
        console.print(f"[bold green]{translator.get('HTTPS interface disabled')}[/]")

    if not ports["admin_http"] and not ports["admin_https"]:
        logger.warning("No admin interface ports enabled after HTTPS modification. Asking user to confirm.")
        if not confirm_no_admin_interface(translator):
            logger.info("User chose to reconfigure admin interface ports after HTTPS modification.")
            return modify_https_port(config, translator)

    return config


def modify_teddycloud_port(config, translator):
    """
    Modify TeddyCloud backend port for direct mode.

    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
    """
    ports = config["ports"]
    current_port = ports["teddycloud"]

    logger.info(f"Modifying TeddyCloud backend port. Current: {current_port}")
    console.print(
        f"[bold cyan]{translator.get('Current TeddyCloud backend port')}: {current_port}[/]"
    )

    default_port = str(current_port) if current_port else "443"
    tc_port = prompt_for_teddycloud_port(default_port, translator)
    logger.info(f"User specified TeddyCloud backend port: {tc_port}")

    new_port = int(tc_port)
    if new_port != current_port and not check_port_available(new_port):
        logger.warning(f"Port {new_port} appears to be in use.")
        if not confirm_port_usage_anyway(new_port, translator):
            logger.info("User chose not to use the port. Restarting TeddyCloud backend port modification.")
            return modify_teddycloud_port(config, translator)

    ports["teddycloud"] = new_port
    logger.success(f"TeddyCloud backend port updated to {new_port}")
    console.print(
        f"[bold green]{translator.get('TeddyCloud backend port updated to')} {new_port}[/]"
    )

    return config
