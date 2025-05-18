#!/usr/bin/env python3
"""
Configuration management UI module for TeddyCloudStarter.
"""
import os

import questionary

from ..configuration.direct_mode import (
    modify_http_port,
    modify_https_port,
    modify_teddycloud_port,
)
from ..configuration.nginx_mode import (
    modify_domain_name,
    modify_https_mode,
    modify_ip_restrictions,
    modify_security_settings,
)
from ..configuration.reset_operations import perform_reset_operations
from ..docker.manager import DockerManager
from ..wizard.ui_helpers import console, custom_style
from ..utilities.logger import logger


def show_configuration_management_menu(
    wizard, config_manager, translator, security_managers=None
):
    logger.debug("Entering show_configuration_management_menu.")
    
    # Initialize security_managers if not provided
    if security_managers is None:
        security_managers = {}
        # Import here to avoid circular imports
        from ..security.basic_auth import BasicAuthManager
        from ..security.certificate_authority import CertificateAuthority
        from ..security.client_certificates import ClientCertificateManager
        from ..security.ip_restrictions import IPRestrictionsManager, AuthBypassIPManager
        from ..security.lets_encrypt import LetsEncryptManager
        
        # Initialize security managers
        security_managers["basic_auth_manager"] = BasicAuthManager(translator=translator)
        security_managers["ca_manager"] = CertificateAuthority(translator=translator)
        security_managers["client_cert_manager"] = ClientCertificateManager(translator=translator)
        security_managers["ip_restrictions_manager"] = IPRestrictionsManager(translator=translator)
        security_managers["auth_bypass_manager"] = AuthBypassIPManager(translator=translator)
        security_managers["lets_encrypt_manager"] = LetsEncryptManager(translator=translator)
        
        logger.debug("Initialized security managers")
    
    while True:
        logger.debug("Displaying Configuration Management menu header.")
        console.print(f"[bold cyan]{translator.get('Configuration Management')}[/]")

        current_config = config_manager.config
        logger.debug(f"Current config: {current_config}")
        current_mode = current_config.get("mode", "direct")
        logger.debug(f"Current mode: {current_mode}")

        # Check auto-update status to display appropriate menu option
        auto_update_enabled = current_config.get("app_settings", {}).get(
            "auto_update", False
        )
        logger.debug(f"Auto-update enabled: {auto_update_enabled}")

        # Build menu choices with IDs and translated texts
        choices = [
            {"id": "change_mode", "text": translator.get("Change deployment mode")},
            {"id": "change_path", "text": translator.get("Change project path")},
            {
                "id": "toggle_update",
                "text": (
                    translator.get("Disable auto-update")
                    if auto_update_enabled
                    else translator.get("Enable auto-update")
                ),
            },
            {"id": "change_tc_branch", "text": translator.get("Change TeddyCloud image branch")},
            {"id": "reset", "text": translator.get("Reset TeddyCloudStarter")},
            {"id": "refresh", "text": translator.get("Refresh server configuration")},
            {"id": "back", "text": translator.get("Back to main menu")},
        ]
        logger.debug(f"Base menu choices: {choices}")

        # Add mode-specific options
        mode_specific_choices = []
        if current_mode == "direct":
            logger.debug("Adding direct mode specific choices.")
            mode_specific_choices = [
                {"id": "modify_http_port", "text": translator.get("Modify HTTP port")},
                {
                    "id": "modify_https_port",
                    "text": translator.get("Modify HTTPS port"),
                },
                # {'id': 'modify_tc_port', 'text': translator.get("Modify TeddyCloud port")}
            ]
        elif current_mode == "nginx":
            logger.debug("Adding nginx mode specific choices.")
            mode_specific_choices = [
                {"id": "modify_domain", "text": translator.get("Modify domain name")},
                # {'id': 'modify_https', 'text': translator.get("Modify HTTPS configuration")},
                {
                    "id": "modify_security",
                    "text": translator.get("Modify security settings"),
                },
                {
                    "id": "modify_ip_filtering",
                    "text": translator.get("Configure IP address filtering"),
                },
            ]

            # Add basic auth bypass option if basic auth is configured
            if (
                current_config.get("nginx", {}).get("security", {}).get("type")
                == "basic_auth"
            ):
                logger.debug("Adding basic auth bypass option.")
                mode_specific_choices.append(
                    {
                        "id": "modify_auth_bypass",
                        "text": translator.get("Configure basic auth bypass IPs"),
                    }
                )

        # Insert mode-specific options at position 3 (after change_path and toggle_update)
        for i, choice in enumerate(mode_specific_choices):
            choices.insert(3 + i, choice)
        logger.debug(f"Final menu choices: {choices}")

        # Show configuration management menu
        choice_texts = [choice["text"] for choice in choices]
        selected_text = questionary.select(
            translator.get("What would you like to do?"),
            choices=choice_texts,
            style=custom_style,
        ).ask()
        logger.info(f"User selected: {selected_text}")

        # Find the selected ID
        selected_id = "back"  # Default to back
        for choice in choices:
            if choice["text"] == selected_text:
                selected_id = choice["id"]
                break
        logger.debug(f"Selected menu id: {selected_id}")

        # Process action based on the selected ID
        if selected_id == "back":
            logger.info("User chose to return to main menu.")
            return False  # Return to main menu

        elif selected_id == "change_mode":
            logger.info("User chose to change deployment mode.")
            wizard.select_deployment_mode()
            config_manager.save()
            logger.debug("Deployment mode changed and config saved.")

            # --- Begin: Additional steps after deployment mode change ---
            from ..configuration.generator import (
                generate_docker_compose,
                generate_nginx_configs,
            )
            from ..configurations import TEMPLATES

            # Stop and remove old containers
            project_path = config_manager.config.get("environment", {}).get(
                "path", None
            )
            logger.debug(f"Project path for DockerManager: {project_path}")
            docker_manager = DockerManager(translator=translator)
            docker_manager.down_services(project_path=project_path)
            logger.debug("Old containers stopped and removed.")

            # Regenerate nginx and docker-compose configs
            generate_nginx_configs(config_manager.config, translator, TEMPLATES)
            generate_docker_compose(config_manager.config, translator, TEMPLATES)
            logger.debug("nginx and docker-compose configs regenerated.")

            # Ask to start services with new mode
            start = questionary.confirm(
                translator.get(
                    "Would you like to start the services with the new deployment mode?"
                ),
                default=True,
                style=custom_style,
            ).ask()
            logger.info(f"User chose to start services: {start}")
            if start:
                docker_manager.start_services(project_path=project_path)
                logger.debug("Services started with new deployment mode.")
            # --- End: Additional steps ---

        elif selected_id == "change_path":
            logger.info("User chose to change project path.")
            wizard.select_project_path()

        elif selected_id == "toggle_update":
            logger.info("User toggled auto-update.")
            config_manager.toggle_auto_update()

        elif selected_id == "change_tc_branch":
            logger.info("User chose to change TeddyCloud image branch.")
            # Prompt for new branch/tag
            current_tag = config_manager.config.get("teddycloud_image_tag", "latest")
            logger.debug(f"Current image tag: {current_tag}")
            new_tag = questionary.text(
                translator.get("Enter TeddyCloud image branch/tag (e.g. 'latest', 'develop')"),
                default=current_tag,
                style=custom_style,
            ).ask()
            logger.info(f"User entered new image tag: {new_tag}")
            if new_tag and new_tag != current_tag:
                config_manager.config["teddycloud_image_tag"] = new_tag
                config_manager.save()
                from ..configuration.generator import generate_docker_compose
                from ..configurations import TEMPLATES
                generate_docker_compose(config_manager.config, translator, TEMPLATES)
                logger.success("TeddyCloud image branch updated. User should restart container.")
                console.print(f"[green]{translator.get('TeddyCloud image branch updated. Please restart the container to apply changes.')}[/]")

        elif selected_id == "reset":
            logger.info("User chose to reset TeddyCloudStarter.")
            reset_options = handle_reset_wizard(translator, config_manager)
            logger.debug(f"Reset options: {reset_options}")
            if reset_options:
                perform_reset_operations(
                    reset_options, config_manager, wizard, translator
                )

        elif selected_id == "refresh":
            logger.info("User chose to refresh server configuration.")
            from ..configuration.generator import (
                generate_docker_compose,
                generate_nginx_configs,
            )
            from ..configurations import TEMPLATES

            generate_nginx_configs(config_manager.config, translator, TEMPLATES)
            generate_docker_compose(config_manager.config, translator, TEMPLATES)
            logger.debug("Server configuration refreshed.")

        # Direct mode specific options
        elif selected_id == "modify_http_port":
            logger.info("User chose to modify HTTP port.")
            modify_http_port(config_manager.config, translator)
            config_manager.save()

        elif selected_id == "modify_https_port":
            logger.info("User chose to modify HTTPS port.")
            modify_https_port(config_manager.config, translator)
            config_manager.save()

        elif selected_id == "modify_tc_port":
            logger.info("User chose to modify TeddyCloud port.")
            modify_teddycloud_port(config_manager.config, translator)
            config_manager.save()

        # Nginx mode specific options
        elif selected_id == "modify_domain":
            logger.info("User chose to modify domain name.")
            modify_domain_name(config_manager.config, translator)
            config_manager.save()

        elif selected_id == "modify_https":
            logger.info("User chose to modify HTTPS configuration.")
            modify_https_mode(config_manager.config, translator, security_managers)
            config_manager.save()

        elif selected_id == "modify_security":
            logger.info("User chose to modify security settings.")
            modify_security_settings(
                config_manager.config, translator, security_managers
            )
            config_manager.save()

        elif selected_id == "modify_ip_filtering":
            logger.info("User chose to configure IP address filtering.")
            modify_ip_restrictions(config_manager.config, translator, security_managers)
            config_manager.save()

        elif selected_id == "modify_auth_bypass":
            logger.info("User chose to configure basic auth bypass IPs.")
            from ..configuration.nginx_mode import configure_auth_bypass_ips

            configure_auth_bypass_ips(
                config_manager.config, translator, security_managers
            )
            config_manager.save()

        logger.debug("Returning to configuration management menu loop.")


def handle_reset_wizard(translator, config_manager=None):
    logger.debug("Entering handle_reset_wizard.")
    console.print(
        f"\n[bold yellow]{translator.get('Warning')}: {translator.get('This will reset selected TeddyCloudStarter settings')}[/]"
    )

    # Define the main options
    main_options = [
        {"name": translator.get("Remove teddycloud.json"), "value": "config_file"},
        {
            "name": translator.get("Remove ProjectPath data"),
            "value": "project_path_menu",
        },
        {
            "name": translator.get("Remove Docker Volumes"),
            "value": "docker_volumes_menu",
        },
    ]
    logger.debug(f"Main reset options: {main_options}")

    selected_main_options = questionary.checkbox(
        translator.get("Select items to reset:"),
        choices=[option["name"] for option in main_options],
        style=custom_style,
    ).ask()
    logger.info(f"User selected main reset options: {selected_main_options}")

    if not selected_main_options:
        logger.info("No reset options selected. Exiting reset wizard.")
        return None

    # Convert selected option names to their values
    selected_values = []
    for selected in selected_main_options:
        for option in main_options:
            if option["name"] == selected:
                selected_values.append(option["value"])
    logger.debug(f"Selected reset values: {selected_values}")

    # Initialize reset options dictionary
    reset_options = {
        "config_file": False,
        "project_path": False,
        "project_folders": [],
        "docker_all_volumes": False,
        "docker_volumes": [],
    }

    # Process each selected main option
    for value in selected_values:
        if value == "config_file":
            reset_options["config_file"] = True
        elif value == "project_path_menu":
            logger.debug("Handling project path reset submenu.")
            # Show project path submenu
            handle_project_path_reset(reset_options, translator, config_manager)
        elif value == "docker_volumes_menu":
            logger.debug("Handling docker volumes reset submenu.")
            # Show Docker volumes submenu
            handle_docker_volumes_reset(reset_options, translator)

    # If no options were selected in the submenus, return None
    if (
        not reset_options["config_file"]
        and not reset_options["project_path"]
        and not reset_options["project_folders"]
        and not reset_options["docker_all_volumes"]
        and not reset_options["docker_volumes"]
    ):
        logger.info("No reset options selected in submenus. Exiting reset wizard.")
        return None

    # Confirm the reset
    confirmed = questionary.confirm(
        translator.get(
            "Are you sure you want to reset these settings? This cannot be undone."
        ),
        default=False,
        style=custom_style,
    ).ask()
    logger.info(f"User confirmed reset: {confirmed}")

    if confirmed:
        logger.debug(f"Returning reset options: {reset_options}")
        return reset_options

    logger.info("User cancelled reset confirmation.")
    return None


def handle_project_path_reset(reset_options, translator, config_manager=None):
    logger.debug("Entering handle_project_path_reset.")

    # Get project path from config_manager
    project_path = None
    if config_manager and hasattr(config_manager, "config"):
        project_path = config_manager.config.get("environment", {}).get("path", None)
    logger.debug(f"Project path: {project_path}")
    data_dir = (
        os.path.normpath(os.path.join(project_path, "data")) if project_path else None
    )
    logger.debug(f"Data dir: {data_dir}")
    existing_folders = []
    if data_dir and os.path.isdir(data_dir):
        existing_folders = [
            f for f in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, f))
        ]
    logger.debug(f"Existing folders in data dir: {existing_folders}")
    # Always offer to reset the entire ProjectPath
    project_path_options = [
        {"name": translator.get("Reset entire ProjectPath"), "value": "entire_path"}
    ]
    # Add only existing folders for selection
    for folder in sorted(existing_folders):
        project_path_options.append(
            {"name": f"{translator.get('Subfolder:')} /{folder}", "value": folder}
        )

    if len(project_path_options) == 1:
        logger.info("No folders found in ProjectPath.")
        console.print(f"[yellow]{translator.get('No folders found in ProjectPath')}[/]")
        return

    selected_options = questionary.checkbox(
        translator.get("Select ProjectPath items to reset:"),
        choices=[option["name"] for option in project_path_options],
        style=custom_style,
    ).ask()
    logger.info(f"User selected project path reset options: {selected_options}")

    if not selected_options:
        logger.info("No project path reset options selected.")
        return

    # Process selected project path options
    for selected in selected_options:
        for option in project_path_options:
            if option["name"] == selected:
                if option["value"] == "entire_path":
                    reset_options["project_path"] = True
                else:
                    reset_options["project_folders"].append(option["value"])
    logger.debug(f"Updated reset_options after project path reset: {reset_options}")


def handle_docker_volumes_reset(reset_options, translator):
    logger.debug("Entering handle_docker_volumes_reset.")

    # Use DockerManager to get the list of available Docker volumes
    docker_manager = DockerManager(translator=translator)
    volume_names = docker_manager.get_volumes()
    logger.debug(f"Available Docker volumes: {volume_names}")

    # Define standard volume options to check for
    standard_volumes = [
        "teddycloudstarter_certs",
        "teddycloudstarter_config",
        "teddycloudstarter_content",
        "teddycloudstarter_library",
        "teddycloudstarter_custom_img",
        "teddycloudstarter_firmware",
        "teddycloudstarter_cache",
        "teddycloudstarter_certbot_conf",
        "teddycloudstarter_certbot_www",
    ]

    # Create options list with "if exist" for standard volumes
    docker_options = [
        {"name": translator.get("Remove all Docker volumes"), "value": "all_volumes"}
    ]

    # Add standard volumes that exist
    for vol in standard_volumes:
        if vol in volume_names:
            docker_options.append(
                {"name": f"{translator.get('Volume:')} ({vol})", "value": vol}
            )

    # Add any additional volumes found
    for vol in volume_names:
        if vol not in standard_volumes:
            docker_options.append({"name": vol, "value": vol})

    # If no Docker volumes exist, show message and return
    if len(docker_options) == 1 and not volume_names:
        logger.info("No Docker volumes found.")
        console.print(f"[yellow]{translator.get('No Docker volumes found')}[/]")
        return

    selected_options = questionary.checkbox(
        translator.get("Select Docker volumes to remove:"),
        choices=[option["name"] for option in docker_options],
        style=custom_style,
    ).ask()
    logger.info(f"User selected Docker volumes to remove: {selected_options}")

    if not selected_options:
        logger.info("No Docker volumes selected for removal.")
        return

    # Process selected Docker volume options
    for selected in selected_options:
        for option in docker_options:
            if option["name"] == selected:
                if option["value"] == "all_volumes":
                    reset_options["docker_all_volumes"] = True
                else:
                    reset_options["docker_volumes"].append(option["value"])
    logger.debug(f"Updated reset_options after docker volumes reset: {reset_options}")
