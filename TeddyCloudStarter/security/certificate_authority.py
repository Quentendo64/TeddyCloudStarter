#!/usr/bin/env python3
"""
Certificate Authority operations for TeddyCloudStarter.
"""
import os
import platform
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple

from rich import box
from rich.console import Console
from rich.panel import Panel
from ..utilities.logger import logger

console = Console()


class CertificateAuthority:
    """Handles Certificate Authority operations for TeddyCloudStarter."""

    def __init__(self, base_dir: str = None, translator=None):
        """
        Initialize the CertificateAuthority.

        Args:
            base_dir: The base directory for certificate operations. If None, use project path from config.
            translator: The translator instance for localization
        """
        logger.debug("Initializing CertificateAuthority instance.")
        self.base_dir_param = base_dir
        self.translator = translator

        if base_dir is not None:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = None

        self.client_certs_dir = None
        self.ca_dir = None
        self.crl_dir = None

    def _ensure_directories(self):
        logger.debug("Ensuring certificate directories exist.")
        if self.client_certs_dir is not None:
            return

        if self.base_dir is None:
            logger.info("Base directory not set. Attempting to get from config manager.")
            from ..config_manager import ConfigManager

            config_manager = ConfigManager()
            project_path = None
            try:
                if config_manager and config_manager.config:
                    project_path = config_manager.config.get("environment", {}).get(
                        "path"
                    )
                    logger.debug(f"Project path from config: {project_path}")
            except Exception as e:
                logger.warning(f"Failed to get project path from config: {e}")

            if project_path:
                logger.info(f"Using project path for base_dir: {project_path}")
                self.base_dir = Path(project_path)
            else:
                logger.warning("No project path found. Using current directory as fallback.")
                console.print(
                    "[bold red]Warning: No project path found for certificate operations. Using current directory as fallback.[/]"
                )
                self.base_dir = Path.cwd()
                if self.translator:
                    logger.info("Translator available. Printing warning about project path.")
                    console.print(
                        f"[yellow]{self.translator.get('Please set a project path to ensure certificates are stored in the correct location.')}[/]"
                    )

        self.client_certs_dir = self.base_dir / "data" / "client_certs"
        self.ca_dir = self.client_certs_dir / "ca"
        self.crl_dir = self.client_certs_dir / "crl"

        try:
            self.client_certs_dir.mkdir(parents=True, exist_ok=True)
            self.ca_dir.mkdir(parents=True, exist_ok=True)
            self.crl_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created/verified directories: {self.client_certs_dir}, {self.ca_dir}, {self.crl_dir}")
        except Exception as e:
            logger.error(f"Error creating certificate directories: {e}")
            console.print(f"[bold red]Error creating certificate directories: {e}[/]")
            try:
                Path(str(self.client_certs_dir)).mkdir(parents=True, exist_ok=True)
                Path(str(self.ca_dir)).mkdir(parents=True, exist_ok=True)
                Path(str(self.crl_dir)).mkdir(parents=True, exist_ok=True)
                logger.debug("Fallback directory creation succeeded.")
            except Exception as e2:
                logger.critical(f"Failed to create certificate directories: {e2}")
                console.print(
                    f"[bold red]Failed to create certificate directories: {e2}[/]"
                )

    def _translate(self, text):
        """Helper method to translate text if translator is available."""
        if self.translator:
            return self.translator.get(text)
        return text

    def _check_openssl(self) -> bool:
        logger.debug("Checking for OpenSSL availability.")
        try:
            subprocess.run(["openssl", "version"], check=True, capture_output=True)
            logger.debug("OpenSSL is available.")
            return True
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.error(f"OpenSSL is not available: {e}")
            console.print(
                Panel(
                    f"[bold red]{self._translate('OpenSSL is not available on your system.')}[/]\n\n"
                    f"[bold yellow]{self._translate('Installation instructions:')}[/]\n"
                    f"- [bold]{self._translate('Windows:')}[/] {self._translate('Download and install from https://slproweb.com/products/Win32OpenSSL.html')}\n"
                    f"- [bold]{self._translate('macOS:')}[/] {self._translate('Use Homebrew: \'brew install openssl\'')}\n"
                    f"- [bold]{self._translate('Linux (Debian/Ubuntu):')}[/] {self._translate('Run \'sudo apt install openssl\'')}\n"
                    f"- [bold]{self._translate('Linux (Fedora/RHEL):')}[/] {self._translate('Run \'sudo dnf install openssl\'')}\n\n"
                    f"{self._translate('After installing OpenSSL, restart the wizard or choose a different option.')}",
                    box=box.ROUNDED,
                    border_style="red",
                )
            )
            return False

    def create_ca_info_file(self) -> bool:
        logger.info("Creating CA info file.")
        self._ensure_directories()

        try:
            openssl_version = "Unknown"
            try:
                result = subprocess.run(
                    ["openssl", "version"], capture_output=True, text=True, check=True
                )
                openssl_version = result.stdout.strip()
                logger.debug(f"OpenSSL version: {openssl_version}")
            except subprocess.SubprocessError as e:
                logger.warning(f"Could not get OpenSSL version: {e}")

            current_datetime = time.strftime("%Y-%m-%d %H:%M:%S")

            os_info = f"{platform.system()} {platform.release()}"
            from .. import __version__ as teddycloudstarter_version

            info_file = self.ca_dir / "ca_info.txt"
            with open(info_file, "w") as f:
                f.write(
                    f"""# TeddyCloudStarter CA Certificate Information
# ======================================

Generated on: {current_datetime}
Operating System: {os_info}
OpenSSL Version: {openssl_version}
TeddyCloudStarter Version: {teddycloudstarter_version}

This Certificate Authority was generated by TeddyCloudStarter.
The CA is used to sign client certificates for secure access to TeddyCloud.

Files in this directory:
- ca.key: The Certificate Authority private key (KEEP SECURE!)
- ca.crt: The Certificate Authority public certificate
- ca_info.txt: This information file

For more information, visit: https://github.com/quentendo64/teddycloudstarter
"""
                )

            logger.success(f"CA info file created at {info_file}")
            return True
        except Exception as e:
            logger.error(f"Could not create CA info file: {e}")
            error_msg = f"Warning: Could not create CA info file: {e}"
            console.print(f"[bold yellow]{self._translate(error_msg)}[/]")
            return False

    def create_ca_certificate(self) -> Tuple[bool, str, str]:
        logger.info("Creating CA certificate if not present.")
        self._ensure_directories()

        if not self._check_openssl():
            logger.warning("OpenSSL not available. Cannot create CA certificate.")
            return False, "", ""

        ca_key_path = self.ca_dir / "ca.key"
        ca_crt_path = self.ca_dir / "ca.crt"

        if ca_key_path.exists() and ca_crt_path.exists():
            logger.info("CA key and certificate already exist.")
            return True, str(ca_crt_path), str(ca_key_path)

        try:
            logger.info("Generating new Certificate Authority.")
            console.print(
                f"[bold cyan]{self._translate('Generating Certificate Authority...')}[/]"
            )

            subprocess.run(
                [
                    "openssl",
                    "req",
                    "-x509",
                    "-newkey",
                    "rsa:4096",
                    "-nodes",
                    "-keyout",
                    str(ca_key_path),
                    "-out",
                    str(ca_crt_path),
                    "-subj",
                    "/CN=TeddyCloudStarterCA",
                    "-days",
                    "3650",
                ],
                check=True,
            )

            self.create_ca_info_file()

            self._setup_ca_directory()

            logger.success("Certificate Authority created successfully.")
            console.print(
                f"[bold green]{self._translate('Certificate Authority created successfully!')}[/]"
            )
            return True, str(ca_crt_path), str(ca_key_path)

        except subprocess.SubprocessError as e:
            logger.error(f"Error generating CA certificate: {e}")
            error_msg = f"Error generating CA certificate: {e}"
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return False, "", ""
        except Exception as e:
            logger.error(f"Error: {e}")
            error_msg = f"Error: {e}"
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return False, "", ""

    def _setup_ca_directory(self) -> bool:
        logger.debug("Setting up CA directory structure.")
        self._ensure_directories()
        try:
            index_file = self.ca_dir / "index.txt"
            if not index_file.exists():
                with open(index_file, "w") as f:
                    pass
                logger.debug(f"Created index.txt at {index_file}")
            newcerts_dir = self.ca_dir / "newcerts"
            newcerts_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured newcerts directory at {newcerts_dir}")
            serial_file = self.ca_dir / "serial"
            if not serial_file.exists():
                with open(serial_file, "w") as f:
                    f.write("01")
                logger.debug(f"Created serial file at {serial_file}")
            crlnumber_file = self.ca_dir / "crlnumber"
            if not crlnumber_file.exists():
                with open(crlnumber_file, "w") as f:
                    f.write("01")
                logger.debug(f"Created crlnumber file at {crlnumber_file}")
            openssl_conf_file = self.ca_dir / "openssl.cnf"
            ca_dir_abs = self.ca_dir.resolve().as_posix()
            ca_crt_abs = (self.ca_dir / "ca.crt").resolve().as_posix()
            ca_key_abs = (self.ca_dir / "ca.key").resolve().as_posix()
            index_abs = (self.ca_dir / "index.txt").resolve().as_posix()
            serial_abs = (self.ca_dir / "serial").resolve().as_posix()
            newcerts_abs = (self.ca_dir / "newcerts").resolve().as_posix()
            crlnumber_abs = (self.ca_dir / "crlnumber").resolve().as_posix()
            with open(openssl_conf_file, "w") as f:
                f.write(
                    f"""
[ ca ]
default_ca = TCS_default

[ TCS_default ]
dir               = {ca_dir_abs}
database         = {index_abs}
serial           = {serial_abs}
new_certs_dir    = {newcerts_abs}
certificate      = {ca_crt_abs}
private_key      = {ca_key_abs}
default_days     = 3650
default_crl_days = 30
default_md       = sha256
policy           = policy_any
crlnumber        = {crlnumber_abs}

[ policy_any ]
countryName            = optional
stateOrProvinceName    = optional
organizationName       = optional
organizationalUnitName = optional
commonName             = supplied
emailAddress           = optional

[ v3_ca ]
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer
basicConstraints = critical,CA:true

[ crl_ext ]
authorityKeyIdentifier=keyid:always
"""
                )
            logger.success(f"CA directory structure set up at {self.ca_dir}")
            return True
        except Exception as e:
            logger.error(f"Error setting up CA directory: {e}")
            error_msg = f"Error setting up CA directory: {e}"
            console.print(f"[bold yellow]{self._translate(error_msg)}[/]")
            return False

    def generate_crl(self) -> Tuple[bool, str]:
        logger.info("Generating Certificate Revocation List (CRL).")
        self._ensure_directories()

        try:
            ca_key_path = self.ca_dir / "ca.key"
            ca_crt_path = self.ca_dir / "ca.crt"
            openssl_conf_path = self.ca_dir / "openssl.cnf"
            logger.debug(f"CA key: {ca_key_path}, CA crt: {ca_crt_path}, openssl.cnf: {openssl_conf_path}")

            if not ca_key_path.exists() or not ca_crt_path.exists():
                logger.error("CA certificate or key not found. Cannot generate CRL.")
                console.print(
                    f"[bold red]{self._translate('CA certificate or key not found. Cannot generate CRL.')}[/]"
                )
                return False, ""

            self.crl_dir.mkdir(exist_ok=True)

            crl_path = self.crl_dir / "ca.crl"

            self._setup_ca_directory()

            logger.debug(f"Running openssl ca -gencrl to generate CRL at {crl_path}")
            subprocess.run(
                [
                    "openssl",
                    "ca",
                    "-config",
                    str(openssl_conf_path.absolute()),
                    "-gencrl",
                    "-keyfile",
                    str(ca_key_path.absolute()),
                    "-cert",
                    str(ca_crt_path.absolute()),
                    "-out",
                    str(crl_path.absolute()),
                ],
                check=True,
            )

            if not crl_path.exists():
                logger.error("CRL file was not created.")
                return False, ""

            logger.success(f"CRL generated successfully at {crl_path}")
            console.print(
                f"[bold green]{self._translate('CRL generated successfully')}[/]"
            )
            return True, str(crl_path)

        except subprocess.SubprocessError as e:
            logger.error(f"Error generating CRL: {e}")
            error_msg = f"Error generating CRL: {e}"
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return False, ""
        except Exception as e:
            logger.error(f"Error: {e}")
            error_msg = f"Error: {e}"
            console.print(f"[bold red]{self._translate(error_msg)}[/]")
            return False, ""

    def validate_certificate(self, cert_path: str) -> Tuple[bool, str, Optional[dict]]:
        logger.info(f"Validating certificate at {cert_path}")
        self._ensure_directories()

        try:
            if not Path(cert_path).exists():
                logger.error(f"Certificate not found: {cert_path}")
                return False, f"Certificate not found: {cert_path}", None

            ca_crt_path = self.ca_dir / "ca.crt"
            if not ca_crt_path.exists():
                logger.error("CA certificate not found.")
                return False, "CA certificate not found", None

            logger.debug(f"Running openssl verify for {cert_path} against {ca_crt_path}")
            verify_result = subprocess.run(
                ["openssl", "verify", "-CAfile", str(ca_crt_path), cert_path],
                capture_output=True,
                text=True,
            )

            cert_info = {}

            logger.debug("Extracting certificate subject.")
            subject_result = subprocess.run(
                ["openssl", "x509", "-noout", "-subject", "-in", cert_path],
                capture_output=True,
                text=True,
                check=True,
            )
            if subject_result.returncode == 0:
                cert_info["subject"] = subject_result.stdout.strip()

            logger.debug("Extracting certificate issuer.")
            issuer_result = subprocess.run(
                ["openssl", "x509", "-noout", "-issuer", "-in", cert_path],
                capture_output=True,
                text=True,
                check=True,
            )
            if issuer_result.returncode == 0:
                cert_info["issuer"] = issuer_result.stdout.strip()

            logger.debug("Extracting certificate dates.")
            dates_result = subprocess.run(
                ["openssl", "x509", "-noout", "-dates", "-in", cert_path],
                capture_output=True,
                text=True,
                check=True,
            )
            if dates_result.returncode == 0:
                dates = dates_result.stdout.strip().split("\n")
                for date in dates:
                    if date.startswith("notBefore="):
                        cert_info["not_before"] = date.replace("notBefore=", "")
                    elif date.startswith("notAfter="):
                        cert_info["not_after"] = date.replace("notAfter=", "")

            logger.debug("Extracting certificate serial number.")
            serial_result = subprocess.run(
                ["openssl", "x509", "-noout", "-serial", "-in", cert_path],
                capture_output=True,
                text=True,
                check=True,
            )
            if serial_result.returncode == 0:
                cert_info["serial"] = serial_result.stdout.strip().split("=")[1]

            if verify_result.returncode != 0:
                error_msg = (
                    f"Certificate verification failed: {verify_result.stderr.strip()}"
                )
                logger.error(error_msg)
                return False, error_msg, cert_info

            logger.success(f"Certificate at {cert_path} is valid.")
            return (
                True,
                f"Certificate is valid until {cert_info.get('not_after', 'unknown')}",
                cert_info,
            )

        except subprocess.SubprocessError as e:
            logger.error(f"Error validating certificate: {e}")
            error_msg = f"Error validating certificate: {e}"
            return False, error_msg, None
        except Exception as e:
            logger.error(f"Error: {e}")
            error_msg = f"Error: {e}"
            return False, error_msg, None

    def generate_self_signed_certificate(
        self, output_dir: str, domain_name: str, translator=None
    ) -> Tuple[bool, str]:
        logger.info(f"Generating self-signed certificate for {domain_name} in {output_dir}")
        self._ensure_directories()

        trans = translator or self.translator

        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured output directory exists: {output_dir}")

            key_path = os.path.join(output_dir, "server.key")
            crt_path = os.path.join(output_dir, "server.crt")

            if not self._check_openssl():
                logger.warning("OpenSSL is not available. Cannot generate self-signed certificate.")
                return False, self._translate("OpenSSL is not available")

            logger.info(f"Running openssl to generate self-signed certificate for {domain_name}")
            cmd = [
                "openssl",
                "req",
                "-x509",
                "-nodes",
                "-days",
                "3650",
                "-newkey",
                "rsa:2048",
                "-keyout",
                key_path,
                "-out",
                crt_path,
                "-subj",
                f"/CN={domain_name}",
            ]

            subprocess.run(cmd, check=True, capture_output=True)
            logger.debug(f"Generated key at {key_path} and certificate at {crt_path}")

            if not os.path.exists(key_path) or not os.path.exists(crt_path):
                logger.error("Failed to create certificate files.")
                return False, self._translate("Failed to create certificate files")

            msg = self._translate("Self-signed certificate created successfully")
            logger.success(msg)
            console.print(f"[bold green]{msg}[/]")
            return True, msg

        except subprocess.SubprocessError as e:
            logger.error(f"Error generating self-signed certificate: {e}")
            if translator:
                error_msg = translator.get(
                    "Error generating self-signed certificate: {error}"
                ).format(error=str(e))
            else:
                error_msg = f"Error generating self-signed certificate: {e}"
            return False, error_msg
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            if translator:
                error_msg = translator.get("Unexpected error: {error}").format(
                    error=str(e)
                )
            else:
                error_msg = f"Unexpected error: {e}"
            return False, error_msg
