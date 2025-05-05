#!/usr/bin/env python3
"""
Configuration generators for TeddyCloudStarter.
"""
import os

import jinja2

from ..wizard.ui_helpers import console
from ..utilities.logger import logger


def generate_docker_compose(config, translator, templates):
    """
    Generate docker-compose.yml based on configuration.

    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        templates: The templates dictionary containing templates

    Returns:
        bool: True if generation was successful, False otherwise
    """
    try:
        logger.info("Starting Docker Compose generation.")
        env = jinja2.Environment(autoescape=True)

        template = env.from_string(templates.get("docker-compose", ""))

        project_path = config.get("environment", {}).get("path", "")
        if not project_path:
            logger.warning(translator.get('No project path set. Using current directory.'))
            console.print(
                f"[bold yellow]{translator.get('Warning')}: {translator.get('No project path set. Using current directory.')}[/]"
            )
            project_path = os.getcwd()

        data_dir = os.path.join(project_path, "data")
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
            logger.success(f"{translator.get('Created data directory at')}: {data_dir}")
            console.print(
                f"[green]{translator.get('Created data directory at')}: {data_dir}[/]"
            )

        context = {"mode": config["mode"]}
        context["teddycloud_image_tag"] = config.get("teddycloud_image_tag", "latest")

        if config["mode"] == "direct":
            context.update(
                {
                    "admin_http": config["ports"]["admin_http"],
                    "admin_https": config["ports"]["admin_https"],
                    "teddycloud": config["ports"]["teddycloud"],
                }
            )
        else:
            crl_file = os.path.exists(
                os.path.join(data_dir, "client_certs", "crl", "ca.crl")
            )

            # Prepare boxes as a list of (crt_fingerprint_no_colon, macaddress) tuples
            raw_boxes = config.get("boxes", [])
            boxes = []
            if isinstance(raw_boxes, list):
                for box in raw_boxes:
                    crt_fp = box.get("crt_fingerprint", "").replace(":", "").lower()
                    mac = box.get("macaddress", "")
                    if crt_fp and mac:
                        boxes.append((crt_fp, mac))
            elif isinstance(raw_boxes, dict):
                # fallback for dict type
                for box in raw_boxes.values():
                    crt_fp = box.get("crt_fingerprint", "").replace(":", "").lower()
                    mac = box.get("macaddress", "")
                    if crt_fp and mac:
                        boxes.append((crt_fp, mac))

            context.update(
                {
                    "domain": config["nginx"]["domain"],
                    "https_mode": config["nginx"]["https_mode"],
                    "security_type": config["nginx"]["security"]["type"],
                    "allowed_ips": config["nginx"]["security"]["allowed_ips"],
                    "crl_file": crl_file,
                    "nginx_type": config["nginx"].get("nginx_type", "standard"),
                    "boxes": boxes,
                }
            )
            logger.debug(f"boxes for docker-compose: {boxes}")
            print("[DEBUG] boxes for docker-compose:", boxes)

            if config["nginx"]["https_mode"] == "user_provided":
                server_certs_path = os.path.join(data_dir, "server_certs")
                if not os.path.exists(server_certs_path):
                    os.makedirs(server_certs_path, exist_ok=True)
                    logger.success(f"{translator.get('Created server_certs directory at')}: {server_certs_path}")
                    console.print(
                        f"[green]{translator.get('Created server_certs directory at')}: {server_certs_path}[/]"
                    )

                context.update({"cert_path": "./server_certs:/etc/nginx/certificates"})
            elif config["nginx"]["https_mode"] == "self_signed":
                context.update({"cert_path": "./server_certs:/etc/nginx/certificates"})
            elif config["nginx"]["https_mode"] == "user_provided":
                context.update({"cert_path": "./server_certs:/etc/nginx/certificates"})

        rendered = template.render(**context)
        with open(os.path.join(data_dir, "docker-compose.yml"), "w") as f:
            f.write(rendered)

        logger.success("Docker Compose configuration generated successfully.")
        console.print(
            "[bold green]Docker Compose configuration generated successfully.[/]"
        )
        return True
    except Exception as e:
        logger.error(f"Error generating Docker Compose file: {e}")
        console.print(f"[bold red]Error generating Docker Compose file: {e}[/]")
        return False


def generate_nginx_configs(config, translator, templates):
    """
    Generate nginx configuration files.

    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        templates: The templates dictionary containing templates

    Returns:
        bool: True if generation was successful, False otherwise
    """
    try:
        logger.info("Starting Nginx configuration generation.")
        env = jinja2.Environment(autoescape=True)

        project_path = config.get("environment", {}).get("path", "")
        if not project_path:
            logger.warning(translator.get('No project path set. Using current directory.'))
            console.print(
                f"[bold yellow]{translator.get('Warning')}: {translator.get('No project path set. Using current directory.')}[/]"
            )
            project_path = os.getcwd()

        data_dir = os.path.join(project_path, "data")
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
            logger.success(f"{translator.get('Created data directory at')}: {data_dir}")
            console.print(
                f"[green]{translator.get('Created data directory at')}: {data_dir}[/]"
            )

        config_dir = os.path.join(data_dir, "configurations")
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
            logger.success(f"{translator.get('Created configurations directory at')}: {config_dir}")
            console.print(
                f"[green]{translator.get('Created configurations directory at')}: {config_dir}[/]"
            )

        edge_template = env.from_string(templates.get("nginx-edge", ""))
        edge_context = {
            "domain": config["nginx"]["domain"],
            "https_mode": config["nginx"]["https_mode"],
            "security_type": config["nginx"]["security"]["type"],
            "allowed_ips": config["nginx"]["security"]["allowed_ips"],
            "nginx_type": config["nginx"].get("nginx_type", "standard"),
        }

        with open(os.path.join(config_dir, "nginx-edge.conf"), "w") as f:
            f.write(edge_template.render(**edge_context))

        logger.debug("nginx-edge.conf generated.")

        auth_template = env.from_string(templates.get("nginx-auth", ""))
        raw_boxes = config.get("boxes", [])
        boxes = []
        if isinstance(raw_boxes, list):
            for box in raw_boxes:
                crt_fp = box.get("crt_fingerprint", "").replace(":", "").lower()
                mac = box.get("macaddress", "")
                if crt_fp and mac:
                    boxes.append((crt_fp, mac))
        elif isinstance(raw_boxes, dict):
            for box in raw_boxes.values():
                crt_fp = box.get("crt_fingerprint", "").replace(":", "").lower()
                mac = box.get("macaddress", "")
                if crt_fp and mac:
                    boxes.append((crt_fp, mac))

        auth_context = {
            "domain": config["nginx"]["domain"],
            "https_mode": config["nginx"]["https_mode"],
            "security_type": config["nginx"]["security"]["type"],
            "allowed_ips": config["nginx"]["security"]["allowed_ips"],
            "auth_bypass_ips": config["nginx"]["security"].get("auth_bypass_ips", []),
            "crl_file": os.path.exists(
                os.path.join(data_dir, "client_certs", "crl", "ca.crl")
            ),
            "nginx_type": config["nginx"].get("nginx_type", "standard"),
            "boxes": boxes,
        }
        logger.debug(f"boxes for nginx-auth: {boxes}")
        print("[DEBUG] boxes for nginx-auth:", boxes)

        with open(os.path.join(config_dir, "nginx-auth.conf"), "w") as f:
            f.write(auth_template.render(**auth_context))

        logger.success("Nginx configurations generated successfully.")
        console.print("[bold green]Nginx configurations generated successfully.[/]")
        return True
    except Exception as e:
        logger.error(f"Error generating Nginx configurations: {e}")
        console.print(f"[bold red]Error generating Nginx configurations: {e}[/]")
        return False
