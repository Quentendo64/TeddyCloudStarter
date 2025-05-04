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


def show_configuration_management_menu(
    wizard, config_manager, translator, security_managers=None
):
    """Show configuration management menu.

    Args:
        wizard: TeddyCloudWizard instance
        config_manager: ConfigManager instance
        translator: TranslationManager instance
        security_managers: Dictionary of security manager instances

    Returns:
        bool: True if configuration was modified, False otherwise
    """
    while True:
        console.print(f"[bold cyan]{translator.get('Configuration Management')}[/]")

        current_config = config_manager.config
        current_mode = current_config.get("mode", "direct")

        # Check auto-update status to display appropriate menu option
        auto_update_enabled = current_config.get("app_settings", {}).get(
            "auto_update", False
        )

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

        # Add mode-specific options
        mode_specific_choices = []
        if current_mode == "direct":
            mode_specific_choices = [
                {"id": "modify_http_port", "text": translator.get("Modify HTTP port")},
                {
                    "id": "modify_https_port",
                    "text": translator.get("Modify HTTPS port"),
                },
                # {'id': 'modify_tc_port', 'text': translator.get("Modify TeddyCloud port")}
            ]
        elif current_mode == "nginx":
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
                mode_specific_choices.append(
                    {
                        "id": "modify_auth_bypass",
                        "text": translator.get("Configure basic auth bypass IPs"),
                    }
                )

        # Insert mode-specific options at position 3 (after change_path and toggle_update)
        for i, choice in enumerate(mode_specific_choices):
            choices.insert(3 + i, choice)

        # Show configuration management menu
        choice_texts = [choice["text"] for choice in choices]
        selected_text = questionary.select(
            translator.get("What would you like to do?"),
            choices=choice_texts,
            style=custom_style,
        ).ask()

        # Find the selected ID
        selected_id = "back"  # Default to back
        for choice in choices:
            if choice["text"] == selected_text:
                selected_id = choice["id"]
                break

        # Process action based on the selected ID
        if selected_id == "back":
            return False  # Return to main menu

        elif selected_id == "change_mode":
            wizard.select_deployment_mode()
            config_manager.save()

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
            docker_manager = DockerManager(translator=translator)
            docker_manager.down_services(project_path=project_path)

            # Regenerate nginx and docker-compose configs
            generate_nginx_configs(config_manager.config, translator, TEMPLATES)
            generate_docker_compose(config_manager.config, translator, TEMPLATES)

            # Ask to start services with new mode
            start = questionary.confirm(
                translator.get(
                    "Would you like to start the services with the new deployment mode?"
                ),
                default=True,
                style=custom_style,
            ).ask()
            if start:
                docker_manager.start_services(project_path=project_path)
            # --- End: Additional steps ---

        elif selected_id == "change_path":
            wizard.select_project_path()

        elif selected_id == "toggle_update":
            config_manager.toggle_auto_update()

        elif selected_id == "change_tc_branch":
            # Prompt for new branch/tag
            current_tag = config_manager.config.get("teddycloud_image_tag", "latest")
            new_tag = questionary.text(
                translator.get("Enter TeddyCloud image branch/tag (e.g. 'latest', 'develop')"),
                default=current_tag,
                style=custom_style,
            ).ask()
            if new_tag and new_tag != current_tag:
                config_manager.config["teddycloud_image_tag"] = new_tag
                config_manager.save()
                from ..configuration.generator import generate_docker_compose
                from ..configurations import TEMPLATES
                generate_docker_compose(config_manager.config, translator, TEMPLATES)
                console.print(f"[green]{translator.get('TeddyCloud image branch updated. Please restart the container to apply changes.')}[/]")
        elif selected_id == "reset":
            reset_options = handle_reset_wizard(translator, config_manager)
            if reset_options:
                perform_reset_operations(
                    reset_options, config_manager, wizard, translator
                )

        elif selected_id == "refresh":
            from ..configuration.generator import (
                generate_docker_compose,
                generate_nginx_configs,
            )
            from ..configurations import TEMPLATES

            generate_nginx_configs(config_manager.config, translator, TEMPLATES)
            generate_docker_compose(config_manager.config, translator, TEMPLATES)

        # Direct mode specific options
        elif selected_id == "modify_http_port":
            modify_http_port(config_manager.config, translator)
            config_manager.save()

        elif selected_id == "modify_https_port":
            modify_https_port(config_manager.config, translator)
            config_manager.save()

        elif selected_id == "modify_tc_port":
            modify_teddycloud_port(config_manager.config, translator)
            config_manager.save()

        # Nginx mode specific options
        elif selected_id == "modify_domain":
            modify_domain_name(config_manager.config, translator)
            config_manager.save()

        elif selected_id == "modify_https":
            modify_https_mode(config_manager.config, translator, security_managers)
            config_manager.save()

        elif selected_id == "modify_security":
            modify_security_settings(
                config_manager.config, translator, security_managers
            )
            config_manager.save()

        elif selected_id == "modify_ip_filtering":
            modify_ip_restrictions(config_manager.config, translator, security_managers)
            config_manager.save()

        elif selected_id == "modify_auth_bypass":
            from ..configuration.nginx_mode import configure_auth_bypass_ips

            configure_auth_bypass_ips(
                config_manager.config, translator, security_managers
            )
            config_manager.save()

        # After any action, loop back to show the menu again


def handle_reset_wizard(translator, config_manager=None):
    """Handle the reset wizard with multiple options and subcategories.

    Args:
        translator: TranslationManager instance
        config_manager: ConfigManager instance (required for dynamic folder listing)

    Returns:
        dict: Dictionary of reset options or None if canceled
    """
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

    selected_main_options = questionary.checkbox(
        translator.get("Select items to reset:"),
        choices=[option["name"] for option in main_options],
        style=custom_style,
    ).ask()

    if not selected_main_options:
        return None

    # Convert selected option names to their values
    selected_values = []
    for selected in selected_main_options:
        for option in main_options:
            if option["name"] == selected:
                selected_values.append(option["value"])

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
            # Show project path submenu
            handle_project_path_reset(reset_options, translator, config_manager)
        elif value == "docker_volumes_menu":
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
        return None

    # Confirm the reset
    confirmed = questionary.confirm(
        translator.get(
            "Are you sure you want to reset these settings? This cannot be undone."
        ),
        default=False,
        style=custom_style,
    ).ask()

    if confirmed:
        return reset_options

    return None


def handle_project_path_reset(reset_options, translator, config_manager=None):
    """Handle the project path reset submenu.

    Args:
        reset_options: Dictionary to store reset options
        translator: TranslationManager instance
        config_manager: ConfigManager instance (required for dynamic folder listing)
    """
    # Get project path from config_manager
    project_path = None
    if config_manager and hasattr(config_manager, "config"):
        project_path = config_manager.config.get("environment", {}).get("path", None)

    # Debug output for project_path
    console.print(f"[cyan]DEBUG: Using project_path: {project_path}[/]")
    data_dir = (
        os.path.normpath(os.path.join(project_path, "data")) if project_path else None
    )
    console.print(f"[cyan]DEBUG: Checking data_dir: {data_dir}[/]")
    existing_folders = []
    if data_dir and os.path.isdir(data_dir):
        existing_folders = [
            f for f in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, f))
        ]
    console.print(f"[cyan]DEBUG: Found folders: {existing_folders}[/]")
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
        console.print(f"[yellow]{translator.get('No folders found in ProjectPath')}[/]")
        return

    selected_options = questionary.checkbox(
        translator.get("Select ProjectPath items to reset:"),
        choices=[option["name"] for option in project_path_options],
        style=custom_style,
    ).ask()

    if not selected_options:
        return

    # Process selected project path options
    for selected in selected_options:
        for option in project_path_options:
            if option["name"] == selected:
                if option["value"] == "entire_path":
                    reset_options["project_path"] = True
                else:
                    reset_options["project_folders"].append(option["value"])


def handle_docker_volumes_reset(reset_options, translator):
    """Handle the Docker volumes reset submenu.

    Args:
        reset_options: Dictionary to store reset options
        translator: TranslationManager instance
    """
    # Use DockerManager to get the list of available Docker volumes
    docker_manager = DockerManager(translator=translator)
    volume_names = docker_manager.get_volumes()

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
        console.print(f"[yellow]{translator.get('No Docker volumes found')}[/]")
        return

    selected_options = questionary.checkbox(
        translator.get("Select Docker volumes to remove:"),
        choices=[option["name"] for option in docker_options],
        style=custom_style,
    ).ask()

    if not selected_options:
        return

    # Process selected Docker volume options
    for selected in selected_options:
        for option in docker_options:
            if option["name"] == selected:
                if option["value"] == "all_volumes":
                    reset_options["docker_all_volumes"] = True
                else:
                    reset_options["docker_volumes"].append(option["value"])
