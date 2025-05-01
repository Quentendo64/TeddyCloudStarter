#!/usr/bin/env python3
"""
Support features utility module for TeddyCloudStarter.
Provides functionality to create support packages for troubleshooting.
"""
import os
import sys
import shutil
import tempfile
import json
import datetime
import zipfile
import subprocess
from pathlib import Path
from rich.console import Console

# Global console instance for rich output
console = Console()

class SupportPackageCreator:
    """Creates a consolidated support package with logs, configs, and directory structure."""
    
    def __init__(self, project_path=None, docker_manager=None, config_manager=None, anonymize=False):
        self.project_path = project_path or os.getcwd()
        self.docker_manager = docker_manager
        self.config_manager = config_manager
        self.temp_dir = None
        self.anonymize = anonymize  # Flag to control anonymization
    
    def create_support_package(self, output_path=None):
        """
        Create a support package with relevant information for troubleshooting.
        
        Args:
            output_path: Path where the support package will be saved
            
        Returns:
            str: Path to the created support package file
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"teddycloud_support_{timestamp}.zip"
        
        # Determine output directory
        if output_path:
            output_dir = Path(output_path)
        else:
            output_dir = Path(self.project_path)
            
        output_file = output_dir / filename
        
        # Make sure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a temporary directory under the output path
        try:
            temp_dir_name = f"temp_support_{timestamp}"
            self.temp_dir = str(output_dir / temp_dir_name)
            os.makedirs(self.temp_dir, exist_ok=True)
            
            # Collect information
            self._collect_logs()
            self._collect_configs()
            self._collect_directory_tree()
            
            # Create zip file
            self._create_zip_archive(output_file)
            
            return str(output_file)
        finally:
            # Clean up temporary directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
    
    def _collect_logs(self):
        """Collect log files from Docker services using docker-compose logs command."""
        log_dir = Path(self.temp_dir) / "logs"
        log_dir.mkdir(exist_ok=True)
        
        services = ["nginx-edge", "nginx-auth", "teddycloud","teddycloud-certbot" ]
        
        for service in services:
            try:
                log_path = log_dir / f"{service}.log"
                console.print(f"[cyan]Collecting logs for {service}...[/]")
                
                # Store current directory
                original_dir = os.getcwd()
                
                try:
                    # Change to the data directory where docker-compose.yml is located
                    data_dir = os.path.join(self.project_path, "data")
                    if not os.path.exists(data_dir):
                        console.print(f"[yellow]Warning: data directory not found at {data_dir}[/]")
                        continue
                        
                    os.chdir(data_dir)
                    
                    # Determine docker-compose command (v1 or v2)
                    compose_cmd = ["docker", "compose"]
                    try:
                        # Check if docker compose v2 is available
                        subprocess.run(
                            ["docker", "compose", "version"], 
                            check=True, capture_output=True, text=True
                        )
                    except (subprocess.SubprocessError, FileNotFoundError):
                        # Fall back to docker-compose v1
                        compose_cmd = ["docker-compose"]
                    
                    # Run docker-compose logs command
                    result = subprocess.run(
                        compose_cmd + ["logs", "--no-color", service], 
                        capture_output=True, text=True
                    )
                    
                    if result.returncode == 0:
                        with open(log_path, 'w', encoding='utf-8') as log_file:
                            log_file.write(f"--- Logs from {service} ---\n\n")
                            log_file.write(result.stdout)
                        console.print(f"[green]Successfully collected logs for {service}[/]")
                        
                        # Anonymize if requested
                        if self.anonymize:
                            console.print(f"[cyan]Anonymizing logs for {service}...[/]")
                            self._anonymize_log_file(log_path)
                    else:
                        # If docker-compose logs fails, try direct docker logs command
                        console.print(f"[yellow]docker-compose logs failed for {service}, trying docker logs directly...[/]")
                        self._fallback_to_docker_logs(service, log_dir)
                finally:
                    # Always return to original directory
                    os.chdir(original_dir)
                    
            except Exception as e:
                console.print(f"[yellow]Warning: Could not collect logs for {service}: {e}[/]")
                # Try fallback method if an error occurs
                self._fallback_to_docker_logs(service, log_dir)
    
    def _fallback_to_docker_logs(self, service, log_dir):
        """Use docker logs command as a fallback method."""
        try:
            log_path = log_dir / f"{service}.log"
            result = subprocess.run(
                ["docker", "logs", service], 
                capture_output=True, 
                text=True
            )
            
            if result.returncode == 0:
                with open(log_path, 'w', encoding='utf-8') as log_file:
                    log_file.write(result.stdout)
                
                # Anonymize if requested
                if self.anonymize:
                    console.print(f"[cyan]Anonymizing logs for {service} (fallback method)...[/]")
                    self._anonymize_log_file(log_path)
            else:
                with open(log_path, 'w', encoding='utf-8') as log_file:
                    log_file.write(f"Error collecting logs: {result.stderr}")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not collect logs for {service} using fallback method: {e}[/]")
    
    def _collect_configs(self):
        """Collect configuration files."""
        config_dir = Path(self.temp_dir) / "configs"
        config_dir.mkdir(exist_ok=True)
        
        # Save TeddyCloudStarter config
        if self.config_manager and self.config_manager.config:
            config_path = config_dir / "config.json"
            with open(config_path, 'w') as f:
                json.dump(self.config_manager.config, f, indent=2)
            
            # Anonymize the config.json if requested
            if self.anonymize:
                console.print(f"[cyan]Anonymizing TeddyCloudStarter config.json...[/]")
                self._anonymize_config_json(config_path)
        elif os.path.exists("config.json"):
            shutil.copy("config.json", config_dir / "config.json")
            
            # Anonymize the config.json if requested
            if self.anonymize:
                console.print(f"[cyan]Anonymizing copied config.json...[/]")
                self._anonymize_config_json(config_dir / "config.json")
        
        # Copy docker-compose.yml if it exists
        docker_compose_path = os.path.join(self.project_path, "data", "docker-compose.yml")
        if os.path.exists(docker_compose_path):
            console.print(f"[cyan]Including docker-compose.yml in support package...[/]")
            shutil.copy(docker_compose_path, config_dir / "docker-compose.yml")
            
        # Copy nginx configuration files if they exist
        nginx_config_dir = os.path.join(self.project_path, "data", "configurations")
        if os.path.exists(nginx_config_dir):
            for nginx_file in ["nginx-edge.conf", "nginx-auth.conf"]:
                nginx_file_path = os.path.join(nginx_config_dir, nginx_file)
                if os.path.exists(nginx_file_path):
                    console.print(f"[cyan]Including {nginx_file} in support package...[/]")
                    shutil.copy(nginx_file_path, config_dir / nginx_file)
        
        # Copy TeddyCloud app config from Docker container or volume
        try:
            # First check if the teddycloud container is running
            teddycloud_container = "teddycloud-app"
            volume_temp_dir = Path(self.temp_dir) / "volume_temp"
            volume_temp_dir.mkdir(exist_ok=True)
            
            check_result = subprocess.run(
                ["docker", "ps", "--filter", f"name={teddycloud_container}", "--format", "{{.Names}}"],
                check=True, capture_output=True, text=True
            )
            
            # Define files to extract
            files_to_extract = ["config.ini"]
            
            # If teddycloud container is running, use it directly
            if teddycloud_container in check_result.stdout:
                console.print(f"[cyan]Found running teddycloud container, copying config files directly...[/]")
                
                for file in files_to_extract:
                    try:
                        dest_path = volume_temp_dir / file
                        # Copy directly from the running container
                        copy_result = subprocess.run(
                            ["docker", "cp", f"{teddycloud_container}:/teddycloud/config/{file}", str(dest_path)],
                            check=True, capture_output=True, text=True
                        )
                        
                        # Copy to final destination if successful
                        if os.path.exists(dest_path):
                            shutil.copy(dest_path, config_dir / file)
                            
                            # Anonymize config.ini if requested
                            if self.anonymize and file == "config.ini":
                                console.print(f"[cyan]Anonymizing config.ini...[/]")
                                self._anonymize_config_ini(config_dir / file)
                    except Exception as e:
                        console.print(f"[yellow]Could not copy {file} from container: {e}[/]")
            else:
                # Container not running, fall back to using Docker volume
                console.print(f"[yellow]Teddycloud container not running, accessing volume directly...[/]")
                
                # Create a temporary container to access the config volume
                temp_container = "temp_support_config_access"
                
                # Check if temp container already exists
                check_result = subprocess.run(
                    ["docker", "ps", "-a", "--filter", f"name={temp_container}", "--format", "{{.Names}}"],
                    check=True, capture_output=True, text=True
                )
                
                if temp_container in check_result.stdout:
                    # Remove existing temp container
                    subprocess.run(["docker", "rm", "-f", temp_container], check=True)
                
                # Try with teddycloudstarter_config volume
                try:
                    create_result = subprocess.run(
                        ["docker", "create", "--name", temp_container, "-v", "teddycloudstarter_config:/config", "nginx:stable-alpine"],
                        check=True, capture_output=True, text=True
                    )
                except subprocess.CalledProcessError:
                    # Try with just 'config' volume name
                    create_result = subprocess.run(
                        ["docker", "create", "--name", temp_container, "-v", "config:/config", "nginx:stable-alpine"],
                        check=True, capture_output=True, text=True
                    )
                
                # Extract files from container
                for file in files_to_extract:
                    try:
                        dest_path = volume_temp_dir / file
                        copy_result = subprocess.run(
                            ["docker", "cp", f"{temp_container}:/config/{file}", str(dest_path)],
                            check=True, capture_output=True, text=True
                        )
                        
                        # Copy to final destination if successful
                        if os.path.exists(dest_path):
                            shutil.copy(dest_path, config_dir / file)
                            
                            # Anonymize config.ini if requested
                            if self.anonymize and file == "config.ini":
                                console.print(f"[cyan]Anonymizing config.ini...[/]")
                                self._anonymize_config_ini(config_dir / file)
                    except Exception:
                        # File might not exist, continue
                        pass
                
                # Clean up temp container
                subprocess.run(["docker", "rm", "-f", temp_container], check=True)
                
        except Exception as e:
            console.print(f"[yellow]Warning: Could not collect TeddyCloud app config: {e}[/]")
    
    def _collect_directory_tree(self):
        """Collect directory tree of the ./data folder."""
        data_dir = Path(self.project_path) / "data"
        tree_file = Path(self.temp_dir) / "directory_structure.txt"
        
        if os.path.exists(data_dir):
            try:
                with open(tree_file, 'w') as f:
                    f.write(f"Directory tree for: {data_dir}\n")
                    f.write("="*50 + "\n\n")
                    
                    # Traverse directory and write tree structure
                    for root, dirs, files in os.walk(data_dir):
                        level = root.replace(str(data_dir), '').count(os.sep)
                        indent = ' ' * 4 * level
                        rel_path = os.path.relpath(root, start=str(data_dir))
                        if rel_path == '.':
                            rel_path = ''
                        f.write(f"{indent}{os.path.basename(root)}/\n")
                        
                        sub_indent = ' ' * 4 * (level + 1)
                        for file in files:
                            # Don't include certificate private keys in the listing
                            if file.endswith('.key'):
                                f.write(f"{sub_indent}{file} [key file - not included]\n")
                            else:
                                f.write(f"{sub_indent}{file}\n")
            except Exception as e:
                console.print(f"[yellow]Warning: Could not collect directory tree: {e}[/]")
        else:
            with open(tree_file, 'w') as f:
                f.write(f"Directory {data_dir} does not exist.\n")
    
    def _create_zip_archive(self, output_file):
        """Create a zip archive from the collected files."""
        try:
            volume_temp_path = os.path.join(self.temp_dir, "volume_temp")
            
            with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(self.temp_dir):
                    # Skip the volume_temp directory
                    if os.path.commonpath([root, volume_temp_path]) == volume_temp_path:
                        continue
                        
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, self.temp_dir)
                        zipf.write(file_path, rel_path)
                        
            # Clean up volume_temp directory early
            if os.path.exists(volume_temp_path):
                shutil.rmtree(volume_temp_path)
                
        except Exception as e:
            console.print(f"[bold red]Error creating zip archive: {e}[/]")
            raise
    
    def _anonymize_text(self, text, patterns_and_replacements):
        """
        Anonymize sensitive information in text based on patterns.
        
        Args:
            text: The text content to anonymize
            patterns_and_replacements: List of tuples with (regex_pattern, replacement)
            
        Returns:
            str: Anonymized text
        """
        import re
        
        anonymized = text
        for pattern, replacement in patterns_and_replacements:
            anonymized = re.sub(pattern, replacement, anonymized)
        
        return anonymized
    
    def _anonymize_log_file(self, file_path):
        """
        Anonymize sensitive information in log files.
        
        Args:
            file_path: Path to the log file to anonymize
        """
        try:
            # Common patterns to anonymize in logs
            patterns = [
                # IP addresses
                (r'\b(?:\d{1,3}\.){3}\d{1,3}\b', 'xxx.xxx.xxx.xxx'),
                # Email addresses
                (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'anonymized@email.com'),
                # URLs with domains
                (r'https?://([a-zA-Z0-9.-]+)', r'https://anonymized-domain.com'),
                # MAC addresses (various formats)
                (r'\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b', 'xx:xx:xx:xx:xx:xx'),
                # UUIDs
                (r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b', 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'),
                # Serial numbers (common formats)
                (r'\b[A-Z0-9]{8,}\b', 'ANONYMIZED-SERIAL'),
                # Usernames in common formats 
                (r'\buser(?:name)?[:=]\s*["\'](.*?)["\']\b', r'username: "anonymized-user"'),
                # Hostnames
                (r'\bhost(?:name)?[:=]\s*["\'](.*?)["\']\b', r'hostname: "anonymized-host"')
            ]
            
            # Read the file
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                
            # Anonymize the content
            anonymized_content = self._anonymize_text(content, patterns)
            
            # Write back to the same file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(anonymized_content)
                
        except Exception as e:
            console.print(f"[yellow]Warning: Could not anonymize log file {file_path}: {e}[/]")

    def _anonymize_config_ini(self, file_path):
        """
        Anonymize sensitive information in config.ini files.
        
        Args:
            file_path: Path to the config.ini file to anonymize
        """
        try:
            # Read the file contents
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            
            # Fields to anonymize
            sensitive_fields = [
                # Network and connection related fields
                "mqtt.hostname", "mqtt.username", "mqtt.password", "mqtt.identification", "mqtt.topic", 
                "core.host_url", "core.server.bind_ip", "core.allowOrigin", "core.flex_uid",
                "cloud.remote_hostname",
                "hass.name", "hass.id",
                "core.server_cert.data.ca",
                "toniebox.field2", "toniebox.field6"
            ]
            
            # Process line by line
            anonymized_lines = []
            for line in lines:
                # Skip comments and empty lines
                if line.strip() == '' or line.strip().startswith(';'):
                    anonymized_lines.append(line)
                    continue
                
                # Check if this line contains a sensitive field
                parts = line.split('=', 1)
                if len(parts) == 2:
                    field_name = parts[0].strip()
                    
                    # Check if field needs to be anonymized
                    should_anonymize = False
                    for sensitive_field in sensitive_fields:
                        if field_name.lower() == sensitive_field.lower():
                            should_anonymize = True
                            break
                            
                    # Also check certificate data fields
                    if (field_name.startswith('core.server_cert.data.') or 
                        field_name.startswith('core.client_cert.data.') or 
                        '.key' in field_name):
                        should_anonymize = True
                    
                    if should_anonymize:
                        anonymized_lines.append(f"{field_name}=ANONYMIZED\n")
                    else:
                        anonymized_lines.append(line)
                else:
                    anonymized_lines.append(line)
            
            # Write back the anonymized content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(anonymized_lines)
                
            console.print(f"[green]Successfully anonymized config.ini file[/]")
                
        except Exception as e:
            console.print(f"[yellow]Warning: Could not anonymize config.ini file {file_path}: {e}[/]")
    
    def _anonymize_config_json(self, file_path):
        """
        Anonymize sensitive information in config.json files.
        
        Args:
            file_path: Path to the config.json file to anonymize
        """
        try:
            # Read the original json file
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Anonymize domain if it exists
            if 'nginx' in config and 'domain' in config['nginx']:
                config['nginx']['domain'] = 'anonymized-domain.com'
            
            # Anonymize user_info if it exists
            if 'user_info' in config:
                config['user_info'] = {
                    'name': 'Anonymized User',
                    'email': 'anonymized@email.com'
                }
            
            # Anonymize hostname if it exists
            if 'environment' in config and 'hostname' in config['environment']:
                config['environment']['hostname'] = 'anonymized-hostname'
            
            # Write the modified config back to the file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
                
        except Exception as e:
            console.print(f"[yellow]Warning: Could not anonymize config.json file {file_path}: {e}[/]")