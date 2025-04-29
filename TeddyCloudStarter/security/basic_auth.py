#!/usr/bin/env python3
"""
Basic authentication functionality for TeddyCloudStarter.
Handles generation and management of .htpasswd files.
"""
import os
import subprocess
import time
import socket
from pathlib import Path
from typing import List, Dict, Optional
import questionary
import getpass
from rich.console import Console
from rich.table import Table

# Re-export console to ensure compatibility
console = Console()

class BasicAuthManager:
    """
    Handles basic authentication operations for TeddyCloudStarter.
    Provides functionality to create and manage .htpasswd files.
    """
    
    def __init__(self, translator=None, base_dir=None):
        """
        Initialize the basic auth manager.
        
        Args:
            translator: Optional translator instance for localization
            base_dir: Optional base directory of the project
        """
        self.translator = translator
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.custom_style = questionary.Style([
            ('qmark', 'fg:cyan bold'),
            ('question', 'fg:cyan bold'),
            ('answer', 'fg:green bold'),
            ('pointer', 'fg:cyan bold'),
            ('highlighted', 'fg:cyan bold'),
            ('selected', 'fg:cyan bold'),
            ('separator', 'fg:cyan'),
            ('instruction', 'fg:gray'),  # Changed from 'brightblack' to 'gray'
            ('text', ''),
            ('disabled', 'fg:gray'),
        ])
    
    def _translate(self, text: str) -> str:
        """
        Helper method to translate text if translator is available.
        
        Args:
            text: The text to translate
            
        Returns:
            str: Translated text if translator is available, otherwise original text
        """
        if self.translator:
            return self.translator.get(text)
        return text
    
    def check_internet_connection(self) -> bool:
        """
        Check if we can connect to Docker Hub or other internet resources.
        Uses multiple methods to be more reliable than a simple ping.
        
        Returns:
            bool: True if internet connectivity is detected, False otherwise
        """
        # Method 1: Try DNS resolution first (doesn't require admin privileges)
        try:
            socket.gethostbyname("registry-1.docker.io")
            return True
        except Exception:
            pass
        
        # Method 2: Try a lightweight HTTP request if available
        try:
            import urllib.request
            urllib.request.urlopen("https://registry-1.docker.io/", timeout=2)
            return True
        except Exception:
            pass

        # Method 3: Try with Python's socket directly
        try:
            socket_obj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            socket_obj.settimeout(2)
            socket_obj.connect(("registry-1.docker.io", 443))
            socket_obj.close()
            return True
        except Exception:
            pass
            
        # Method 4: Fall back to checking if Docker command works with a simple image
        try:
            # Try to see if a Docker registry communication works
            result = subprocess.run(
                ["docker", "search", "--limit=1", "alpine"],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            pass
        
        # Method 5: Only use ping as a last resort
        try:
            # Try to connect to a reliable DNS first
            subprocess.run(["ping", "1.1.1.1", "-n", "1" if os.name == 'nt' else "-c", "1"], 
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
            return True
        except Exception:
            try:
                # Try an alternate reliable host
                subprocess.run(["ping", "8.8.8.8", "-n", "1" if os.name == 'nt' else "-c", "1"], 
                               check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
                return True
            except Exception:
                # All methods failed
                return False
    
    def generate_htpasswd_file(self, htpasswd_file_path: str) -> bool:
        """
        Generates a .htpasswd file using Docker httpd Alpine image.
        
        Args:
            htpasswd_file_path: Path where the .htpasswd file will be saved
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create a table for collecting user credentials
            table = Table(title=self._translate("User Authentication Setup"))
            table.add_column(self._translate("Username"), justify="left", style="cyan")
            table.add_column(self._translate("Password"), justify="left", style="green", no_wrap=True)
            table.add_column(self._translate("Status"), justify="right", style="bold")
            
            # Collect user credentials
            users = []
            
            console.print(f"[bold cyan]{self._translate('Enter user credentials for basic authentication')}[/]")
            console.print(f"[cyan]{self._translate('(Passwords will not be displayed as you type)')}\n[/]")
            
            while True:
                username = questionary.text(
                    self._translate("Username (leave empty to finish):"),
                    style=self.custom_style
                ).ask()
                
                if not username:
                    if not users:
                        console.print(f"[bold yellow]{self._translate('No users added. At least one user is required.')}[/]")
                        continue
                    break
                
                # Check for duplicate usernames
                if any(u['username'] == username for u in users):
                    console.print(f"[bold red]{self._translate('Username already exists. Please choose another one.')}[/]")
                    continue
                    
                # Use getpass for hidden password input
                console.print(f"[bold cyan]{self._translate('Enter password for user')} {username}:[/]")
                password = getpass.getpass("")
                
                if not password:
                    console.print(f"[bold red]{self._translate('Password cannot be empty')}[/]")
                    continue
                    
                console.print(f"[bold cyan]{self._translate('Confirm password for user')} {username}:[/]")
                confirm_password = getpass.getpass("")
                
                if password != confirm_password:
                    console.print(f"[bold red]{self._translate('Passwords do not match')}[/]")
                    continue
                    
                # Add user to the list
                users.append({
                    'username': username,
                    'password': password
                })
                
                table.add_row(
                    username, 
                    "********", 
                    f"[bold green]{self._translate('Added')}[/]"
                )
            
            # Display the table with all users
            if users:
                console.print("\n")
                console.print(table)
            
            if not users:
                console.print(f"[bold yellow]{self._translate('No users added. You\'ll need to create the .htpasswd file manually.')}[/]")
                return False
            
            # Attempt to generate the htpasswd file with retry functionality
            return self._attempt_htpasswd_generation(users, htpasswd_file_path)
                
        except Exception as e:
            console.print(f"[bold red]{self._translate('Error generating .htpasswd file')}: {str(e)}[/]")
            
            # Print detailed exception information for debugging
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/]")
            return False
    
    def _attempt_htpasswd_generation(self, users: List[Dict[str, str]], htpasswd_file_path: str) -> bool:
        """
        Attempt to generate an htpasswd file with retry handling.
        
        Args:
            users: List of dictionaries with username and password
            htpasswd_file_path: Path where the .htpasswd file will be saved
            
        Returns:
            bool: True if successful, False otherwise
        """
        while True:
            try:
                # Check if Docker is available
                try:
                    subprocess.run(["docker", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                except (subprocess.SubprocessError, FileNotFoundError):
                    console.print(f"[bold red]{self._translate('Docker is not available. Cannot generate .htpasswd file.')}[/]")
                    console.print(f"[yellow]{self._translate('You\'ll need to create the .htpasswd file manually.')}[/]")
                    return False

                # Check internet connection
                if not self.check_internet_connection():
                    console.print(f"[bold red]{self._translate('Error: No internet connection detected. Docker may not be able to pull the httpd image.')}[/]")
                    retry = questionary.confirm(
                        self._translate("Would you like to check your connection and retry?"),
                        default=True,
                        style=self.custom_style
                    ).ask()
                    
                    if not retry:
                        console.print(f"[yellow]{self._translate('Skipping .htpasswd generation. You will need to create it manually.')}[/]")
                        return False
                    
                    console.print(f"[cyan]{self._translate('Retrying .htpasswd generation...')}[/]")
                    continue
                
                console.print(f"[cyan]{self._translate('Pulling httpd:alpine Docker image...')}[/]")
                pull_result = subprocess.run(
                    ["docker", "pull", "httpd:alpine"],
                    capture_output=True,
                    text=True
                )
                
                if pull_result.returncode != 0:
                    console.print(f"[bold red]{self._translate('Error pulling Docker image')}:[/]")
                    console.print(f"[red]{pull_result.stderr}[/]")
                    
                    # Check if it's a network error
                    if "network" in pull_result.stderr.lower() or "connection" in pull_result.stderr.lower() or "dial" in pull_result.stderr.lower() or "lookup" in pull_result.stderr.lower():
                        console.print(f"[bold yellow]{self._translate('Network error detected. Please check your internet connection.')}[/]")
                        
                        retry = questionary.confirm(
                            self._translate("Would you like to retry after checking your connection?"),
                            default=True,
                            style=self.custom_style
                        ).ask()
                        
                        if retry:
                            console.print(f"[cyan]{self._translate('Retrying .htpasswd generation...')}[/]")
                            continue
                        else:
                            console.print(f"[yellow]{self._translate('Skipping .htpasswd generation. You will need to create it manually.')}[/]")
                            return False
                    else:
                        # For other Docker errors
                        console.print(f"[bold red]{self._translate('Docker error. Cannot generate .htpasswd file.')}[/]")
                        return False

                # Create .htpasswd file using Docker
                console.print(f"[bold cyan]{self._translate('Generating .htpasswd file...')}[/]")
                
                # Create the parent directory if it doesn't exist
                security_path = os.path.dirname(htpasswd_file_path)
                Path(security_path).mkdir(parents=True, exist_ok=True)
                
                # Windows specific: Fix the path format for Docker
                if os.name == 'nt':
                    docker_security_path = security_path.replace('\\', '/')
                    if ':' in docker_security_path:
                        docker_security_path = '/' + docker_security_path[0].lower() + docker_security_path[2:]
                else:
                    docker_security_path = security_path
                
                console.print(f"[dim]{self._translate('Using Docker volume path')}: {docker_security_path}[/]")
                
                # Define temp filename for Docker to create
                temp_filename = "temp_htpasswd.txt"
                temp_htpasswd = os.path.join(security_path, temp_filename)
                
                # Generate the initial file
                first_user = users[0]
                cmd = [
                    "docker", "run", "--rm", 
                    "-v", f"{security_path}:/htpasswd",
                    "httpd:alpine", "sh", "-c", 
                    f"htpasswd -cb /htpasswd/{temp_filename} {first_user['username']} {first_user['password']}"
                ]
                
                # On Windows, use special Docker path format
                if os.name == 'nt':
                    cmd = [
                        "docker", "run", "--rm", 
                        "-v", f"{docker_security_path}:/htpasswd",
                        "httpd:alpine", "sh", "-c", 
                        f"htpasswd -cb /htpasswd/{temp_filename} {first_user['username']} {first_user['password']}"
                    ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    console.print(f"[bold red]{self._translate('Error creating .htpasswd file')}:[/]")
                    console.print(f"[red]{result.stderr}[/]")
                    raise Exception(f"Failed to create .htpasswd: {result.stderr}")
                
                # Add additional users
                for user in users[1:]:
                    # On Windows, use special Docker path format
                    cmd = [
                        "docker", "run", "--rm", 
                        "-v", f"{security_path}:/htpasswd",
                        "httpd:alpine", "sh", "-c", 
                        f"htpasswd -b /htpasswd/{temp_filename} {user['username']} {user['password']}"
                    ]
                    
                    if os.name == 'nt':
                        cmd = [
                            "docker", "run", "--rm", 
                            "-v", f"{docker_security_path}:/htpasswd",
                            "httpd:alpine", "sh", "-c", 
                            f"htpasswd -b /htpasswd/{temp_filename} {user['username']} {user['password']}"
                        ]
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode != 0:
                        raise Exception(f"Failed to add user {user['username']}: {result.stderr}")
                
                # Ensure directory exists for the target file
                Path(os.path.dirname(htpasswd_file_path)).mkdir(parents=True, exist_ok=True)
                
                try:
                    # Move the temp file to the final location
                    if os.path.exists(temp_htpasswd):
                        # Check if the destination exists and remove it if needed
                        if os.path.exists(htpasswd_file_path):
                            os.remove(htpasswd_file_path)
                            
                        # Copy instead of move to handle cross-device scenarios
                        import shutil
                        shutil.copy2(temp_htpasswd, htpasswd_file_path)
                        
                        # Only remove temp file after successful copy
                        if os.path.exists(htpasswd_file_path) and os.path.getsize(htpasswd_file_path) > 0:
                            try:
                                os.remove(temp_htpasswd)
                            except Exception as e:
                                console.print(f"[dim]{self._translate('Note: Could not remove temporary file')} {temp_htpasswd}: {str(e)}[/]")
                    else:
                        raise FileNotFoundError(f"Temporary file {temp_htpasswd} not found")
                except Exception as e:
                    console.print(f"[bold red]{self._translate('Error moving .htpasswd file')}: {str(e)}[/]")
                    
                    # Try direct Docker write approach as fallback
                    console.print(f"[cyan]{self._translate('Attempting alternative .htpasswd generation...')}[/]")
                    try:
                        # Write directly to final location
                        first_user = users[0]
                        cmd = [
                            "docker", "run", "--rm", 
                            "-v", f"{docker_security_path}:/htpasswd",
                            "httpd:alpine", "sh", "-c", 
                            f"htpasswd -cb /htpasswd/.htpasswd {first_user['username']} {first_user['password']}"
                        ]
                        
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True
                        )
                        
                        if result.returncode != 0:
                            raise Exception(f"Failed in fallback method: {result.stderr}")
                        
                        # Add additional users directly
                        for user in users[1:]:
                            cmd = [
                                "docker", "run", "--rm", 
                                "-v", f"{docker_security_path}:/htpasswd",
                                "httpd:alpine", "sh", "-c", 
                                f"htpasswd -b /htpasswd/.htpasswd {user['username']} {user['password']}"
                            ]
                            
                            result = subprocess.run(
                                cmd,
                                capture_output=True,
                                text=True
                            )
                            
                            if result.returncode != 0:
                                raise Exception(f"Failed to add user {user['username']}: {result.stderr}")
                    except Exception as e:
                        console.print(f"[bold red]{self._translate('Alternative method also failed')}: {str(e)}[/]")
                        raise
                
                # Verify the file was created and has content
                if os.path.exists(htpasswd_file_path) and os.path.getsize(htpasswd_file_path) > 0:
                    console.print(f"[bold green]{self._translate('.htpasswd file generated successfully!')}[/]")
                    console.print(f"[green]{self._translate('.htpasswd file location')}: {htpasswd_file_path}[/]")
                    return True
                else:
                    console.print(f"[bold red]{self._translate('Failed to create .htpasswd file or file is empty')}[/]")
                    retry = questionary.confirm(
                        self._translate("Would you like to retry?"),
                        default=True,
                        style=self.custom_style
                    ).ask()
                    
                    if not retry:
                        return False
                    
                    # If retry, loop will continue
                
            except Exception as e:
                console.print(f"[bold red]{self._translate('Error generating .htpasswd file')}: {str(e)}[/]")
                
                # Print detailed exception information for debugging
                import traceback
                console.print(f"[dim]{traceback.format_exc()}[/]")
                
                # Ask to retry
                retry = questionary.confirm(
                    self._translate("Would you like to retry .htpasswd generation?"),
                    default=True,
                    style=self.custom_style
                ).ask()
                
                if not retry:
                    return False
    
    def verify_htpasswd_file(self, htpasswd_file_path: str) -> bool:
        """
        Verify that an htpasswd file exists and has valid content.
        
        Args:
            htpasswd_file_path: Path to the .htpasswd file
            
        Returns:
            bool: True if the file exists and has valid content, False otherwise
        """
        # Check if file exists
        if not os.path.exists(htpasswd_file_path):
            console.print(f"[bold red]{self._translate('.htpasswd file not found at')} {htpasswd_file_path}[/]")
            return False
        
        # Check if file has content
        if os.path.getsize(htpasswd_file_path) == 0:
            console.print(f"[bold red]{self._translate('.htpasswd file is empty at')} {htpasswd_file_path}[/]")
            return False
        
        # Try to validate file format with Docker
        try:
            security_path = os.path.dirname(htpasswd_file_path)
            htpasswd_filename = os.path.basename(htpasswd_file_path)
            
            # Windows specific: Fix the path format for Docker
            if os.name == 'nt':
                docker_security_path = security_path.replace('\\', '/')
                if ':' in docker_security_path:
                    docker_security_path = '/' + docker_security_path[0].lower() + docker_security_path[2:]
            else:
                docker_security_path = security_path
            
            # Validate file format using Docker httpd
            cmd = [
                "docker", "run", "--rm", 
                "-v", f"{docker_security_path}:/htpasswd",
                "httpd:alpine", "cat", f"/htpasswd/{htpasswd_filename}"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                console.print(f"[bold yellow]{self._translate('Warning: Could not validate .htpasswd format')}[/]")
                return True  # Assume it's valid if we can't check
            
            # Check if the output has at least one line with expected format
            lines = result.stdout.strip().split("\n")
            if not lines:
                console.print(f"[bold red]{self._translate('.htpasswd file appears to be empty or invalid')}[/]")
                return False
                
            # Check if lines have the user:hash format
            for line in lines:
                if ":" not in line:
                    console.print(f"[bold red]{self._translate('.htpasswd file appears to have invalid format')}[/]")
                    return False
            
            # File exists, has content, and appears to have valid format
            console.print(f"[bold green]{self._translate('.htpasswd file validated successfully')}[/]")
            return True
            
        except Exception as e:
            # If we can't run Docker, just check if the file exists and has content
            console.print(f"[bold yellow]{self._translate('Warning: Could not fully validate .htpasswd file')}: {str(e)}[/]")
            return True  # Assume it's valid if we can't check