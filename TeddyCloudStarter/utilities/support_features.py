#!/usr/bin/env python3
"""
Support features utility module for TeddyCloudStarter.
Provides functionality to create support packages for troubleshooting.
"""
import datetime
import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

from rich.console import Console
from .logger import logger

console = Console()


class SupportPackageCreator:
    """Creates a consolidated support package with logs, configs, and directory structure."""

    def __init__(
        self,
        project_path=None,
        docker_manager=None,
        config_manager=None,
        anonymize=False,
    ):
        logger.debug(f"Initializing SupportPackageCreator with project_path={project_path}, anonymize={anonymize}")
        self.project_path = project_path or os.getcwd()
        self.docker_manager = docker_manager
        self.config_manager = config_manager
        self.temp_dir = None
        self.anonymize = anonymize
        logger.info("SupportPackageCreator initialized.")

    def create_support_package(self, output_path=None):
        logger.debug(f"Starting create_support_package with output_path={output_path}")
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"teddycloud_support_{timestamp}.zip"

        if output_path:
            output_dir = Path(output_path)
        else:
            output_dir = Path(self.project_path)

        output_file = output_dir / filename
        logger.debug(f"Output directory: {output_dir}, Output file: {output_file}")

        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            temp_dir_name = f"temp_support_{timestamp}"
            self.temp_dir = str(output_dir / temp_dir_name)
            os.makedirs(self.temp_dir, exist_ok=True)
            logger.debug(f"Temporary directory created: {self.temp_dir}")

            self._collect_logs()
            self._collect_configs()
            self._collect_directory_tree()

            self._create_zip_archive(output_file)
            logger.info(f"Support package created at {output_file}")

            return str(output_file)
        except Exception as e:
            logger.error(f"Error creating support package: {e}")
            raise
        finally:
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logger.debug(f"Temporary directory removed: {self.temp_dir}")

    def _collect_logs(self):
        logger.debug("Collecting logs from Docker services.")
        log_dir = Path(self.temp_dir) / "logs"
        log_dir.mkdir(exist_ok=True)

        services = ["nginx-edge", "nginx-auth", "teddycloud", "teddycloud-certbot"]

        for service in services:
            try:
                log_path = log_dir / f"{service}.log"
                console.print(f"[cyan]Collecting logs for {service}...[/]")

                original_dir = os.getcwd()

                try:
                    data_dir = os.path.join(self.project_path, "data")
                    if not os.path.exists(data_dir):
                        console.print(
                            f"[yellow]Warning: data directory not found at {data_dir}[/]"
                        )
                        continue

                    os.chdir(data_dir)

                    compose_cmd = ["docker", "compose"]
                    try:
                        subprocess.run(
                            ["docker", "compose", "version"],
                            check=True,
                            capture_output=True,
                            text=True,
                        )
                    except (subprocess.SubprocessError, FileNotFoundError):
                        compose_cmd = ["docker-compose"]

                    result = subprocess.run(
                        compose_cmd + ["logs", "--no-color", service],
                        capture_output=True,
                        text=True,
                    )

                    if result.returncode == 0:
                        with open(log_path, "w", encoding="utf-8") as log_file:
                            log_file.write(f"--- Logs from {service} ---\n\n")
                            log_file.write(result.stdout)
                        console.print(
                            f"[green]Successfully collected logs for {service}[/]"
                        )
                        logger.info(f"Logs collected for service: {service}")

                        if self.anonymize:
                            console.print(f"[cyan]Anonymizing logs for {service}...[/]")
                            self._anonymize_log_file(log_path)
                            logger.debug(f"Logs anonymized for service: {service}")
                    else:
                        console.print(
                            f"[yellow]docker-compose logs failed for {service}, trying docker logs directly...[/]"
                        )
                        self._fallback_to_docker_logs(service, log_dir)
                finally:
                    os.chdir(original_dir)

            except Exception as e:
                console.print(
                    f"[yellow]Warning: Could not collect logs for {service}: {e}[/]"
                )
                logger.error(f"Error collecting logs for service {service}: {e}")
                self._fallback_to_docker_logs(service, log_dir)

    def _fallback_to_docker_logs(self, service, log_dir):
        logger.debug(f"Fallback to docker logs for service: {service}")
        try:
            log_path = log_dir / f"{service}.log"
            result = subprocess.run(
                ["docker", "logs", service], capture_output=True, text=True
            )

            if result.returncode == 0:
                with open(log_path, "w", encoding="utf-8") as log_file:
                    log_file.write(result.stdout)

                if self.anonymize:
                    console.print(
                        f"[cyan]Anonymizing logs for {service} (fallback method)...[/]"
                    )
                    self._anonymize_log_file(log_path)
                    logger.debug(f"Logs anonymized for service {service} using fallback method")
            else:
                with open(log_path, "w", encoding="utf-8") as log_file:
                    log_file.write(f"Error collecting logs: {result.stderr}")
                logger.error(f"Error collecting logs for service {service}: {result.stderr}")
        except Exception as e:
            console.print(
                f"[yellow]Warning: Could not collect logs for {service} using fallback method: {e}[/]"
            )
            logger.error(f"Error collecting logs for service {service} using fallback method: {e}")

    def _collect_configs(self):
        logger.debug("Collecting configuration files.")
        config_dir = Path(self.temp_dir) / "configs"
        config_dir.mkdir(exist_ok=True)

        if self.config_manager and self.config_manager.config:
            config_path = config_dir / "config.json"
            with open(config_path, "w") as f:
                json.dump(self.config_manager.config, f, indent=2)

            if self.anonymize:
                console.print("[cyan]Anonymizing TeddyCloudStarter config.json...[/]")
                self._anonymize_config_json(config_path)
                logger.debug("TeddyCloudStarter config.json anonymized.")
        elif os.path.exists("config.json"):
            shutil.copy("config.json", config_dir / "config.json")

            if self.anonymize:
                console.print("[cyan]Anonymizing copied config.json...[/]")
                self._anonymize_config_json(config_dir / "config.json")
                logger.debug("Copied config.json anonymized.")

        docker_compose_path = os.path.join(
            self.project_path, "data", "docker-compose.yml"
        )
        if os.path.exists(docker_compose_path):
            console.print(
                "[cyan]Including docker-compose.yml in support package...[/]"
            )
            shutil.copy(docker_compose_path, config_dir / "docker-compose.yml")
            logger.info("docker-compose.yml included in support package.")

        nginx_config_dir = os.path.join(self.project_path, "data", "configurations")
        if os.path.exists(nginx_config_dir):
            for nginx_file in ["nginx-edge.conf", "nginx-auth.conf"]:
                nginx_file_path = os.path.join(nginx_config_dir, nginx_file)
                if os.path.exists(nginx_file_path):
                    console.print(
                        f"[cyan]Including {nginx_file} in support package...[/]"
                    )
                    shutil.copy(nginx_file_path, config_dir / nginx_file)
                    logger.info(f"{nginx_file} included in support package.")

        try:
            teddycloud_container = "teddycloud-app"
            volume_temp_dir = Path(self.temp_dir) / "volume_temp"
            volume_temp_dir.mkdir(exist_ok=True)

            check_result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "--filter",
                    f"name={teddycloud_container}",
                    "--format",
                    "{{.Names}}",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            files_to_extract = ["config.ini"]

            if teddycloud_container in check_result.stdout:
                console.print(
                    "[cyan]Found running teddycloud container, copying config files directly...[/]"
                )
                logger.info("Found running teddycloud container, copying config files directly.")

                for file in files_to_extract:
                    try:
                        dest_path = volume_temp_dir / file
                        copy_result = subprocess.run(
                            [
                                "docker",
                                "cp",
                                f"{teddycloud_container}:/teddycloud/config/{file}",
                                str(dest_path),
                            ],
                            check=True,
                            capture_output=True,
                            text=True,
                        )

                        if os.path.exists(dest_path):
                            shutil.copy(dest_path, config_dir / file)

                            if self.anonymize and file == "config.ini":
                                console.print("[cyan]Anonymizing config.ini...[/]")
                                self._anonymize_config_ini(config_dir / file)
                                logger.debug("config.ini anonymized.")
                    except Exception as e:
                        console.print(
                            f"[yellow]Could not copy {file} from container: {e}[/]"
                        )
                        logger.error(f"Could not copy {file} from container: {e}")
            else:
                console.print(
                    "[yellow]Teddycloud container not running, accessing volume directly...[/]"
                )
                logger.info("Teddycloud container not running, accessing volume directly.")

                temp_container = "temp_support_config_access"

                check_result = subprocess.run(
                    [
                        "docker",
                        "ps",
                        "-a",
                        "--filter",
                        f"name={temp_container}",
                        "--format",
                        "{{.Names}}",
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )

                if temp_container in check_result.stdout:
                    subprocess.run(["docker", "rm", "-f", temp_container], check=True)

                try:
                    create_result = subprocess.run(
                        [
                            "docker",
                            "create",
                            "--name",
                            temp_container,
                            "-v",
                            "teddycloudstarter_config:/config",
                            "nginx:stable-alpine",
                        ],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                except subprocess.CalledProcessError:
                    create_result = subprocess.run(
                        [
                            "docker",
                            "create",
                            "--name",
                            temp_container,
                            "-v",
                            "config:/config",
                            "nginx:stable-alpine",
                        ],
                        check=True,
                        capture_output=True,
                        text=True,
                    )

                for file in files_to_extract:
                    try:
                        dest_path = volume_temp_dir / file
                        copy_result = subprocess.run(
                            [
                                "docker",
                                "cp",
                                f"{temp_container}:/config/{file}",
                                str(dest_path),
                            ],
                            check=True,
                            capture_output=True,
                            text=True,
                        )

                        if os.path.exists(dest_path):
                            shutil.copy(dest_path, config_dir / file)

                            if self.anonymize and file == "config.ini":
                                console.print("[cyan]Anonymizing config.ini...[/]")
                                self._anonymize_config_ini(config_dir / file)
                                logger.debug("config.ini anonymized.")
                    except Exception:
                        pass

                subprocess.run(["docker", "rm", "-f", temp_container], check=True)

        except Exception as e:
            console.print(
                f"[yellow]Warning: Could not collect TeddyCloud app config: {e}[/]"
            )
            logger.error(f"Could not collect TeddyCloud app config: {e}")

    def _collect_directory_tree(self):
        logger.debug("Collecting directory tree of the ./data folder.")
        data_dir = Path(self.project_path) / "data"
        tree_file = Path(self.temp_dir) / "directory_structure.txt"

        if os.path.exists(data_dir):
            try:
                with open(tree_file, "w") as f:
                    f.write(f"Directory tree for: {data_dir}\n")
                    f.write("=" * 50 + "\n\n")

                    for root, dirs, files in os.walk(data_dir):
                        level = root.replace(str(data_dir), "").count(os.sep)
                        indent = " " * 4 * level
                        rel_path = os.path.relpath(root, start=str(data_dir))
                        if rel_path == ".":
                            rel_path = ""
                        f.write(f"{indent}{os.path.basename(root)}/\n")

                        sub_indent = " " * 4 * (level + 1)
                        for file in files:
                            if file.endswith(".key"):
                                f.write(
                                    f"{sub_indent}{file} [key file - not included]\n"
                                )
                            else:
                                f.write(f"{sub_indent}{file}\n")
                logger.info("Directory tree collected successfully.")
            except Exception as e:
                console.print(
                    f"[yellow]Warning: Could not collect directory tree: {e}[/]"
                )
                logger.error(f"Could not collect directory tree: {e}")
        else:
            with open(tree_file, "w") as f:
                f.write(f"Directory {data_dir} does not exist.\n")
            logger.warning(f"Directory {data_dir} does not exist.")

    def _create_zip_archive(self, output_file):
        logger.debug(f"Creating zip archive at {output_file}")
        try:
            volume_temp_path = os.path.join(self.temp_dir, "volume_temp")

            with zipfile.ZipFile(output_file, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(self.temp_dir):
                    if os.path.commonpath([root, volume_temp_path]) == volume_temp_path:
                        continue

                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, self.temp_dir)
                        zipf.write(file_path, rel_path)

            if os.path.exists(volume_temp_path):
                shutil.rmtree(volume_temp_path)
                logger.debug(f"Temporary volume path removed: {volume_temp_path}")

            logger.info(f"Zip archive created successfully at {output_file}")
        except Exception as e:
            console.print(f"[bold red]Error creating zip archive: {e}[/]")
            logger.error(f"Error creating zip archive: {e}")
            raise

    def _anonymize_text(self, text, patterns_and_replacements):
        logger.debug("Anonymizing text with provided patterns.")
        import re

        anonymized = text
        for pattern, replacement in patterns_and_replacements:
            anonymized = re.sub(pattern, replacement, anonymized)

        return anonymized

    def _anonymize_log_file(self, file_path):
        logger.debug(f"Anonymizing log file: {file_path}")
        try:
            patterns = [
                (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "xxx.xxx.xxx.xxx"),
                (
                    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                    "anonymized@email.com",
                ),
                (r"https?://([a-zA-Z0-9.-]+)", r"https://anonymized-domain.com"),
                (r"\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b", "xx:xx:xx:xx:xx:xx"),
                (
                    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
                    "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                ),
                (r"\b[A-Z0-9]{8,}\b", "ANONYMIZED-SERIAL"),
                (
                    r'\buser(?:name)?[:=]\s*["\'](.*?)["\']\b',
                    r'username: "anonymized-user"',
                ),
                (
                    r'\bhost(?:name)?[:=]\s*["\'](.*?)["\']\b',
                    r'hostname: "anonymized-host"',
                ),
            ]

            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            anonymized_content = self._anonymize_text(content, patterns)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(anonymized_content)

            logger.info(f"Log file anonymized: {file_path}")
        except Exception as e:
            console.print(
                f"[yellow]Warning: Could not anonymize log file {file_path}: {e}[/]"
            )
            logger.error(f"Could not anonymize log file {file_path}: {e}")

    def _anonymize_config_ini(self, file_path):
        logger.debug(f"Anonymizing config.ini file: {file_path}")
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            sensitive_fields = [
                "mqtt.hostname",
                "mqtt.username",
                "mqtt.password",
                "mqtt.identification",
                "mqtt.topic",
                "core.host_url",
                "core.server.bind_ip",
                "core.allowOrigin",
                "core.flex_uid",
                "cloud.remote_hostname",
                "hass.name",
                "hass.id",
                "core.server_cert.data.ca",
                "toniebox.field2",
                "toniebox.field6",
            ]

            anonymized_lines = []
            for line in lines:
                if line.strip() == "" or line.strip().startswith(";"):
                    anonymized_lines.append(line)
                    continue

                parts = line.split("=", 1)
                if len(parts) == 2:
                    field_name = parts[0].strip()

                    should_anonymize = False
                    for sensitive_field in sensitive_fields:
                        if field_name.lower() == sensitive_field.lower():
                            should_anonymize = True
                            break

                    if (
                        field_name.startswith("core.server_cert.data.")
                        or field_name.startswith("core.client_cert.data.")
                        or ".key" in field_name
                    ):
                        should_anonymize = True

                    if should_anonymize:
                        anonymized_lines.append(f"{field_name}=ANONYMIZED\n")
                    else:
                        anonymized_lines.append(line)
                else:
                    anonymized_lines.append(line)

            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(anonymized_lines)

            console.print("[green]Successfully anonymized config.ini file[/]")
            logger.info(f"config.ini file anonymized: {file_path}")
        except Exception as e:
            console.print(
                f"[yellow]Warning: Could not anonymize config.ini file {file_path}: {e}[/]"
            )
            logger.error(f"Could not anonymize config.ini file {file_path}: {e}")

    def _anonymize_config_json(self, file_path):
        logger.debug(f"Anonymizing config.json file: {file_path}")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            if "nginx" in config and "domain" in config["nginx"]:
                config["nginx"]["domain"] = "anonymized-domain.com"

            if "user_info" in config:
                config["user_info"] = {
                    "name": "Anonymized User",
                    "email": "anonymized@email.com",
                }

            if "environment" in config and "hostname" in config["environment"]:
                config["environment"]["hostname"] = "anonymized-hostname"

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)

            logger.info(f"config.json file anonymized: {file_path}")
        except Exception as e:
            console.print(
                f"[yellow]Warning: Could not anonymize config.json file {file_path}: {e}[/]"
            )
            logger.error(f"Could not anonymize config.json file {file_path}: {e}")
