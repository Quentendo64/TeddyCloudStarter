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
    
    def __init__(self, project_path=None, docker_manager=None, config_manager=None):
        self.project_path = project_path or os.getcwd()
        self.docker_manager = docker_manager
        self.config_manager = config_manager
        self.temp_dir = None
    
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
        
        if output_path:
            output_file = Path(output_path) / filename
        else:
            output_file = Path(self.project_path) / filename
        
        # Create a temporary directory to store files
        try:
            self.temp_dir = tempfile.mkdtemp(prefix="teddycloud_support_")
            
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
        """Collect log files from Docker containers by copying them directly using docker cp."""
        log_dir = Path(self.temp_dir) / "logs"
        log_dir.mkdir(exist_ok=True)
        
        services = ["nginx-edge", "nginx-auth", "teddycloud-app"]
        log_paths = {
            "nginx-edge": "/var/log/nginx/error.log",
            "nginx-auth": "/var/log/nginx/error.log",
            "teddycloud-app": "/var/log/teddycloud.log"
        }
        
        # Create a temporary directory for each service
        for service in services:
            service_temp_dir = log_dir / service
            service_temp_dir.mkdir(exist_ok=True)
            
            try:
                # Check if container exists and is running
                container_check = subprocess.run(
                    ["docker", "ps", "--filter", f"name={service}", "--format", "{{.Names}}"],
                    capture_output=True, text=True, check=False
                )
                
                if service in container_check.stdout:
                    # Container exists and is running, copy the log file
                    log_path = log_paths.get(service, "/var/log/")
                    
                    # First try to copy the specific log file
                    try:
                        copy_result = subprocess.run(
                            ["docker", "cp", f"{service}:{log_path}", f"{service_temp_dir}/"],
                            capture_output=True, text=True, check=False
                        )
                        
                        if copy_result.returncode == 0:
                            # Find the copied file(s) and move them to the log directory with appropriate naming
                            for root, _, files in os.walk(service_temp_dir):
                                for file in files:
                                    src_file = os.path.join(root, file)
                                    dest_file = log_dir / f"{service}_{file}"
                                    shutil.move(src_file, dest_file)
                        else:
                            # If specific file copy fails, try to copy the entire /var/log directory
                            console.print(f"[yellow]Specific log file not found for {service}, trying to copy all logs...[/]")
                            
                            fallback_copy_result = subprocess.run(
                                ["docker", "cp", f"{service}:/var/log/", f"{service_temp_dir}/"],
                                capture_output=True, text=True, check=False
                            )
                            
                            if fallback_copy_result.returncode == 0:
                                # Create a combined log file from all available logs
                                with open(log_dir / f"{service}.log", 'w') as combined_log:
                                    combined_log.write(f"--- Combined logs from {service} ---\n\n")
                                    
                                    # Find all log files and append their contents
                                    log_files_found = []
                                    for root, _, files in os.walk(service_temp_dir):
                                        for file in files:
                                            if file.endswith('.log'):
                                                log_files_found.append(os.path.join(root, file))
                                    
                                    # Sort log files to ensure consistent order
                                    log_files_found.sort()
                                    
                                    # Append contents of each log file
                                    for log_file in log_files_found:
                                        rel_path = os.path.relpath(log_file, service_temp_dir)
                                        combined_log.write(f"\n--- {rel_path} ---\n")
                                        try:
                                            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                                                combined_log.write(f.read())
                                        except Exception as e:
                                            combined_log.write(f"Error reading log file: {e}\n")
                            else:
                                # Fall back to docker logs command
                                self._fallback_to_docker_logs(service, log_dir)
                    except Exception as e:
                        # Use docker logs command as a fallback
                        console.print(f"[yellow]Failed to copy log files from {service}: {e}[/]")
                        self._fallback_to_docker_logs(service, log_dir)
                else:
                    console.print(f"[yellow]Container {service} not running, using docker logs as fallback[/]")
                    self._fallback_to_docker_logs(service, log_dir)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not collect logs for {service}: {e}[/]")
            
            # Clean up temporary directory for this service
            try:
                shutil.rmtree(service_temp_dir)
            except Exception:
                pass
    
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
        elif os.path.exists("config.json"):
            shutil.copy("config.json", config_dir / "config.json")
        
        # Copy TeddyCloud app config from Docker volume if possible
        try:
            # Create a temporary container to access the config volume
            temp_container = "temp_support_config_access"
            
            # Check if container already exists
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
            
            # Use temporary directory to store volume content
            volume_temp_dir = Path(self.temp_dir) / "volume_temp"
            volume_temp_dir.mkdir(exist_ok=True)
            
            # Extract files from container
            files_to_extract = ["config.yaml", "tonies.custom.json"]
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
            with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(self.temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, self.temp_dir)
                        zipf.write(file_path, rel_path)
        except Exception as e:
            console.print(f"[bold red]Error creating zip archive: {e}[/]")
            raise