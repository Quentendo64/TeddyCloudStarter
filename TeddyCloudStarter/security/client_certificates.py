#!/usr/bin/env python3
"""
Client certificate operations for TeddyCloudStarter.
"""
import os
import shutil
import time
import subprocess
import re
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich import box
from .certificate_authority import CertificateAuthority

# Re-export console to ensure compatibility
console = Console()

class ClientCertificateManager:
    """Handles client certificate operations for TeddyCloudStarter."""
    
    def __init__(self, base_dir: str = None, translator=None):
        """
        Initialize the ClientCertificateManager.
        
        Args:
            base_dir: The base directory for certificate operations. If None, use project path from config.
            translator: The translator instance for localization
        """
        # Create the certificate authority manager
        self.ca_manager = CertificateAuthority(base_dir=base_dir, translator=translator)
        
        # Set up directories
        if base_dir is None:
            # Import here to avoid circular imports
            from ..config_manager import ConfigManager
            config_manager = ConfigManager()
            project_path = None
            try:
                if config_manager and config_manager.config:
                    project_path = config_manager.config.get("environment", {}).get("path")
            except Exception:
                pass
            self.base_dir = Path(project_path) if project_path else Path(".")
        else:
            self.base_dir = Path(base_dir)
            
        self.client_certs_dir = self.base_dir / "data" / "client_certs"
        self.ca_dir = self.client_certs_dir / "ca"
        self.clients_dir = self.client_certs_dir / "clients"
        self.server_dir = self.client_certs_dir / "server"
        self.crl_dir = self.client_certs_dir / "crl"
        self.translator = translator
    
    def _translate(self, text):
        """Helper method to translate text if translator is available."""
        if self.translator:
            return self.translator.get(text)
        return text
    
    def _check_openssl(self) -> bool:
        """
        Check if OpenSSL is available.
        
        Returns:
            bool: True if OpenSSL is available, False otherwise
        """
        return self.ca_manager._check_openssl()
    
    def generate_server_certificate(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Generate a server certificate signed by the CA.
        
        Returns:
            Tuple[bool, Optional[str], Optional[str]]: (success, certificate_path, key_path)
        """
        # Ensure directories exist
        self.client_certs_dir.mkdir(parents=True, exist_ok=True)
        self.server_dir.mkdir(exist_ok=True)
        
        # Check if OpenSSL is available
        if not self._check_openssl():
            return False, None, None
        
        # Check if server certificate already exists
        server_key_path = self.server_dir / "server.key"
        server_crt_path = self.server_dir / "server.crt"
        
        if server_key_path.exists() and server_crt_path.exists():
            return True, str(server_crt_path), str(server_key_path)
        
        try:
            console.print(f"[bold cyan]{self._translate('Generating server certificate...')}[/]")
            
            # First ensure we have a Certificate Authority
            ca_success, ca_crt_path, ca_key_path = self.ca_manager.create_ca_certificate()
            if not ca_success:
                return False, None, None
            
            # Generate server key and CSR
            server_csr_path = self.server_dir / "server.csr"
            
            subprocess.run([
                "openssl", "req", "-newkey", "rsa:4096", "-nodes",
                "-keyout", str(server_key_path),
                "-out", str(server_csr_path),
                "-subj", "/CN=TeddyCloudServer"
            ], check=True)
            
            # Sign server certificate with CA
            subprocess.run([
                "openssl", "x509", "-req",
                "-in", str(server_csr_path),
                "-CA", ca_crt_path,
                "-CAkey", ca_key_path,
                "-CAcreateserial",
                "-out", str(server_crt_path),
                "-days", "3650"
            ], check=True)
            
            # Clean up temporary CSR file
            if server_csr_path.exists():
                try:
                    server_csr_path.unlink()
                except:
                    pass
            
            console.print(f"[bold green]{self._translate('Server certificate generated successfully!')}[/]")
            return True, str(server_crt_path), str(server_key_path)
            
        except subprocess.SubprocessError as e:
            error_msg = f"Error generating server certificate: {e}"
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return False, None, None
        except Exception as e:
            error_msg = f"Error: {e}"
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return False, None, None
    
    def generate_client_certificate(self, client_name: Optional[str] = None, passout: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Generate client certificates using OpenSSL.
        
        Args:
            client_name: Optional name for the client certificate. If not provided, will use default
            passout: Optional password for the PKCS#12 file. If not provided, will use default "teddycloud"
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (success, certificate_info)
        """
        console.print(f"[bold cyan]{self._translate('Generating client certificate...')}[/]")
        
        try:
            # Ensure directories exist
            self.client_certs_dir.mkdir(parents=True, exist_ok=True)
            self.clients_dir.mkdir(exist_ok=True)
            
            # Check if OpenSSL is available
            if not self._check_openssl():
                return False, {}
            
            # Use default name if none provided
            if not client_name:
                client_name = "TeddyCloudClient"
            
            # Store whether this is a default password for display purposes
            is_default_password = not passout
            
            # Use default password if none provided
            if not passout:
                passout = "teddycloud"
            
            # Ensure client_name is valid as file name by removing special chars
            safe_name = re.sub(r'[^\w\-\.]', '_', client_name)
            
            # First ensure we have a Certificate Authority
            ca_success, ca_crt_path, ca_key_path = self.ca_manager.create_ca_certificate()
            if not ca_success:
                return False, {}
            
            # Generate client key and CSR with the provided name
            client_key = self.clients_dir / f"{safe_name}.key"
            client_csr = self.clients_dir / f"{safe_name}.csr"
            client_crt = self.clients_dir / f"{safe_name}.crt"
            client_p12 = self.clients_dir / f"{safe_name}.p12"
            
            subprocess.run([
                "openssl", "req", "-newkey", "rsa:4096", "-nodes",
                "-keyout", str(client_key),
                "-out", str(client_csr),
                "-subj", f"/CN={client_name}"
            ], check=True)
            
            # Sign client certificate with CA
            subprocess.run([
                "openssl", "x509", "-req",
                "-in", str(client_csr),
                "-CA", ca_crt_path,
                "-CAkey", ca_key_path,
                "-CAcreateserial",
                "-out", str(client_crt),
                "-days", "3650"
            ], check=True)
            
            # Create PKCS#12 file for client with provided or default password
            subprocess.run([
                "openssl", "pkcs12", "-export",
                "-inkey", str(client_key),
                "-in", str(client_crt),
                "-certfile", ca_crt_path,
                "-out", str(client_p12),
                "-passout", f"pass:{passout}"
            ], check=True)
            
            # Get certificate serial number for tracking
            result = subprocess.run(
                ["openssl", "x509", "-noout", "-serial", "-in", str(client_crt)],
                capture_output=True, text=True, check=True
            )
            serial = result.stdout.strip().split('=')[1]
            
            # Add the last 8 characters of serial to the filename to avoid overwriting
            serial_suffix = serial[-8:]
            new_safe_name = f"{safe_name}_{serial_suffix}"
            
            # Rename files to include serial suffix
            client_p12_with_serial = self.clients_dir / f"{new_safe_name}.p12"
            client_key_with_serial = self.clients_dir / f"{new_safe_name}.key"
            client_crt_with_serial = self.clients_dir / f"{new_safe_name}.crt"
            
            # Rename the files
            shutil.move(str(client_p12), str(client_p12_with_serial))
            shutil.move(str(client_key), str(client_key_with_serial))
            shutil.move(str(client_crt), str(client_crt_with_serial))
            
            # Update our variables to use the new filenames
            client_p12 = client_p12_with_serial
            client_key = client_key_with_serial
            client_crt = client_crt_with_serial
            
            # Clean up temporary CSR file
            if client_csr.exists():
                try:
                    client_csr.unlink()
                except:
                    pass
            
            # Get certificate expiration date
            result = subprocess.run(
                ["openssl", "x509", "-noout", "-enddate", "-in", str(client_crt)],
                capture_output=True, text=True, check=True
            )
            end_date = result.stdout.strip().split('=')[1]
            
            # Format the end date
            try:
                # Parse the date format from OpenSSL (e.g., "May 14 12:00:00 2026 GMT")
                parsed_date = datetime.strptime(end_date, "%b %d %H:%M:%S %Y %Z")
                formatted_end_date = parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                formatted_end_date = end_date  # Use original format if parsing fails
            
            # Collect certificate information
            cert_info = {
                "client_name": client_name,
                "safe_name": new_safe_name,
                "serial": serial,
                "creation_date": datetime.now().strftime("%Y-%m-%d"),
                "valid_till": formatted_end_date,
                "revoked": False,
                "path": {
                    "p12": str(client_p12),
                    "key": str(client_key),
                    "crt": str(client_crt)
                },
                "password": "Default: teddycloud" if is_default_password else "Custom (hidden)"
            }
            
            # Store certificate info in config.json
            self._update_certificate_info_in_config(cert_info)
            
            # Display success message with certificate details
            message = f"[bold green]{self._translate('Client certificate generated successfully!')}[/]\n\n"
            message += f"{self._translate('Client certificate')} '{client_name}' {self._translate('has been created:')}\n"
            message += f"- {client_key}: {self._translate('The client private key')}\n"
            message += f"- {client_crt}: {self._translate('The client certificate')}\n"
            
            # Display password differently based on whether it's the default or a custom one
            if is_default_password:
                message += f"- {client_p12}: {self._translate('Client certificate bundle (password: ')} {passout})\n\n"
            else:
                message += f"- {client_p12}: {self._translate('Client certificate bundle (password: ')} ******)\n\n"
            
            message += f"{self._translate('Install the .p12 file on devices that need to access TeddyCloud.')}"
            
            console.print(Panel(
                message,
                box=box.ROUNDED,
                border_style="green"
            ))
            
            return True, cert_info
            
        except subprocess.SubprocessError as e:
            error_msg = f"Error generating certificates: {e}"
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return False, {}
        except Exception as e:
            error_msg = f"Error: {e}"
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return False, {}
    
    def _update_certificate_info_in_config(self, cert_info: Dict[str, Any]) -> bool:
        """
        Update certificate information in config.json.
        
        Args:
            cert_info: Dictionary containing certificate information
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Find the correct config file to update
            from ..config_manager import ConfigManager
            
            # First try the project-specific config
            if self.base_dir and self.base_dir != Path("."):
                project_config_path = Path(self.base_dir) / "config.json"
                if project_config_path.exists():
                    config_manager = ConfigManager(config_path=str(project_config_path))
                else:
                    # If project config doesn't exist, fall back to default
                    config_manager = ConfigManager()
            else:
                # Use default config if no project path
                config_manager = ConfigManager()
            
            if config_manager and config_manager.config:
                # Create a simplified certificate info dictionary for storage
                simplified_cert_info = {
                    "client_name": cert_info["client_name"],
                    "safe_name": cert_info["safe_name"],
                    "serial": cert_info["serial"],
                    "creation_date": cert_info["creation_date"],
                    "valid_till": cert_info["valid_till"],
                    "revoked": False,
                    "path": cert_info["path"]["p12"]
                }
                
                # Initialize security section if it doesn't exist
                if "security" not in config_manager.config:
                    config_manager.config["security"] = {}
                
                # Initialize client_certificates array if it doesn't exist
                if "client_certificates" not in config_manager.config["security"]:
                    config_manager.config["security"]["client_certificates"] = []
                
                # Add certificate info to the array
                config_manager.config["security"]["client_certificates"].append(simplified_cert_info)
                config_manager.save()
                
                # Debug info
                console.print(f"[green]{self._translate('Certificate information saved to')} {config_manager.config_path}[/]")
                return True
                
        except Exception as e:
            error_msg = f"Warning: Could not update config with certificate info: {e}"
            console.print(f"[bold yellow]{self._translate(error_msg)}[/]")
            return False
    
    def revoke_client_certificate(self, cert_name: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Revoke a client certificate.
        
        Args:
            cert_name: Optional name of the certificate to revoke. If not provided, will prompt user
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (success, certificate_info)
        """
        console.print(f"[bold cyan]{self._translate('Revoking client certificate...')}[/]")
        
        try:
            if not self.client_certs_dir.exists():
                console.print(f"[bold red]{self._translate('No client certificates directory found.')}[/]")
                return False, {}
            
            # Get certificate information from config.json
            from ..config_manager import ConfigManager
            config_manager = ConfigManager()
            
            # Check if certificates are stored in the config
            certificates = []
            if (config_manager and config_manager.config and 
                "security" in config_manager.config and 
                "client_certificates" in config_manager.config["security"]):
                certificates = config_manager.config["security"]["client_certificates"]
            
            # Check if we have any certificates to revoke
            if not certificates:
                # Fall back to checking file system if no certificates in config
                if not self.clients_dir.exists() or not any(self.clients_dir.glob('*.crt')):
                    console.print(f"[bold red]{self._translate('No client certificates found to revoke.')}[/]")
                    return False, {}
            
            # Validate the certificate name or find it in the config
            cert_info = None
            safe_name = None
            
            if cert_name:
                # Try to find the certificate in the config first
                for cert in certificates:
                    if cert.get("client_name") == cert_name or cert.get("safe_name") == cert_name:
                        cert_info = cert
                        safe_name = cert.get("safe_name")
                        break
                
                # If not found in config, check file directly
                if not cert_info:
                    # Try to find the file directly
                    cert_file = self.clients_dir / f"{cert_name}.crt"
                    if not cert_file.exists():
                        error_msg = f"Certificate {cert_name}.crt not found."
                        console.print(f"[bold red]{self._translate(error_msg)}[/]")
                        return False, {}
                    safe_name = cert_name
            else:
                # If no cert_name provided and we have certificates in config, use the first one as an example
                if certificates:
                    cert_info = certificates[0]
                    cert_name = cert_info.get("client_name")
                    safe_name = cert_info.get("safe_name")
                else:
                    # If no certificates in config, check file system
                    cert_files = list(self.clients_dir.glob('*.crt'))
                    if not cert_files:
                        console.print(f"[bold red]{self._translate('No client certificates found to revoke.')}[/]")
                        return False, {}
                    cert_file = cert_files[0]
                    cert_name = cert_file.stem
                    safe_name = cert_name
            
            # Get the certificate path from safe_name
            cert_path = self.clients_dir / f"{safe_name}.crt"
            
            # Get the certificate serial number
            serial = None
            if cert_info and "serial" in cert_info:
                serial = cert_info["serial"]
            else:
                try:
                    result = subprocess.run(
                        ["openssl", "x509", "-noout", "-serial", "-in", str(cert_path)],
                        capture_output=True, text=True, check=True
                    )
                    serial = result.stdout.strip().split('=')[1]
                except Exception as e:
                    error_msg = f"Could not get certificate serial number: {e}"
                    console.print(f"[bold yellow]{self._translate(error_msg)}[/]")
            
            # Revoke the certificate
            try:
                # Ensure we're in the CA directory for relative paths in the config
                original_dir = os.getcwd()
                os.chdir(str(self.ca_dir.absolute()))
                
                # Make sure the CA directory is properly set up
                self.ca_manager._setup_ca_directory()
                
                # Revoke the certificate using OpenSSL
                ca_key_path = self.ca_dir / "ca.key"
                ca_crt_path = self.ca_dir / "ca.crt"
                
                subprocess.run([
                    "openssl", "ca", "-config", "openssl.cnf",
                    "-revoke", str(cert_path),
                    "-keyfile", str(ca_key_path),
                    "-cert", str(ca_crt_path)
                ], check=True)
                
                # Generate CRL
                success, crl_path = self.ca_manager.generate_crl()
                if not success:
                    console.print(f"[bold yellow]{self._translate('Warning: Could not generate CRL after revocation')}[/]")
                
                # Return to original directory
                os.chdir(original_dir)
                
                # Update certificate status in config.json
                if config_manager and certificates:
                    for i, cert in enumerate(certificates):
                        if (cert.get("client_name") == cert_name or 
                            cert.get("safe_name") == safe_name or 
                            (serial and cert.get("serial") == serial)):
                            config_manager.config["security"]["client_certificates"][i]["revoked"] = True
                            config_manager.config["security"]["client_certificates"][i]["revocation_date"] = time.strftime("%Y-%m-%d")
                            config_manager.save()
                            
                            # Use the updated certificate info
                            cert_info = config_manager.config["security"]["client_certificates"][i]
                            break
                
                success_msg = f"Certificate {cert_name} has been revoked successfully."
                console.print(f"[bold green]{self._translate(success_msg)}[/]")
                update_msg = "The Certificate Revocation List (CRL) has been updated."
                console.print(f"[cyan]{self._translate(update_msg)}[/]")
                restart_msg = "You may need to restart services for the changes to take effect."
                console.print(f"[cyan]{self._translate(restart_msg)}[/]")
                
                return True, cert_info if cert_info else {"client_name": cert_name, "revoked": True}
                
            except subprocess.SubprocessError as e:
                error_msg = f"Error revoking certificate: {e}"
                console.print(f"[bold red]{self._translate(error_msg)}[/]")
                # Return to original directory on error
                try:
                    os.chdir(original_dir)
                except:
                    pass
                return False, {}
            
        except Exception as e:
            error_msg = f"Error during certificate revocation: {e}"
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return False, {}
    
    def list_certificates(self) -> list:
        """
        List all client certificates.
        
        Returns:
            list: List of certificate information dictionaries
        """
        from ..config_manager import ConfigManager
        config_manager = ConfigManager()
        
        certificates = []
        if (config_manager and config_manager.config and 
            "security" in config_manager.config and 
            "client_certificates" in config_manager.config["security"]):
            certificates = config_manager.config["security"]["client_certificates"]
        
        # If no certificates in config, try to find them in the file system
        if not certificates and self.clients_dir.exists():
            cert_files = list(self.clients_dir.glob('*.crt'))
            for cert_file in cert_files:
                try:
                    # Get certificate information
                    success, _, cert_info = self.ca_manager.validate_certificate(str(cert_file))
                    if success and cert_info:
                        # Create a simplified certificate info dictionary
                        certificates.append({
                            "client_name": cert_info.get('subject', '').replace('subject=', ''),
                            "safe_name": cert_file.stem,
                            "serial": cert_info.get('serial', ''),
                            "creation_date": "Unknown",
                            "valid_till": cert_info.get('not_after', ''),
                            "revoked": False,
                            "path": str(cert_file)
                        })
                except:
                    pass
        
        return certificates