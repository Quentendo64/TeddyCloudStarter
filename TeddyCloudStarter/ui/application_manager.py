import subprocess
from pathlib import Path
import tempfile
import re
from ..utilities.openssl_utils import der_to_pem_cert, der_to_pem_key, get_certificate_fingerprint
from ..utilities.logger import logger


def inject_tonies_custom_json(config_manager):
    """
    Logic to inject the tonies.custom.json file from ProjectPath/data/ to the config volume.
    Returns a dict with status and messages for the UI to handle.
    """
    logger.debug("Starting injection of tonies.custom.json.")
    project_path = config_manager.config.get("environment", {}).get("path")
    logger.debug(f"Project path from config: {project_path}")
    if not project_path:
        logger.error("No project path set in config.")
        return {"status": "error", "message": "No project path set in config."}

    base_path = Path(project_path)
    source_file = base_path / "data" / "tonies.custom.json"
    logger.debug(f"Source file path: {source_file}")
    if not source_file.exists():
        logger.warning(f"tonies.custom.json file missing at {source_file}")
        return {"status": "missing_file", "source_file": str(source_file)}

    try:
        logger.debug("Checking for running Docker containers.")
        result = subprocess.run([
            "docker", "ps", "--format", "{{.Names}}"
        ], check=True, capture_output=True, text=True)
        running_containers = [c for c in result.stdout.strip().split("\n") if c]
        logger.debug(f"Running containers: {running_containers}")
        teddycloud_container = "teddycloud-app" if "teddycloud-app" in running_containers else None
        logger.debug(f"Selected container: {teddycloud_container}")
    except Exception as e:
        logger.error(f"Error checking running containers: {e}")
        running_containers = []
        teddycloud_container = None

    if not running_containers or not teddycloud_container:
        temp_container_name = "temp_teddycloud_file_injector"
        try:
            logger.info(f"Creating temporary container: {temp_container_name}")
            subprocess.run([
                "docker", "rm", "-f", temp_container_name
            ], check=False)
            subprocess.run([
                "docker", "create", "--name", temp_container_name, "-v", "teddycloudstarter_config:/config", "nginx:stable-alpine"
            ], check=True)
            teddycloud_container = temp_container_name
            is_temp = True
            logger.success(f"Temporary container {temp_container_name} created.")
        except Exception as e:
            logger.error(f"Failed to create temporary container: {e}")
            return {"status": "manual", "source_file": str(source_file)}
    else:
        is_temp = False

    target_path = "/config/tonies.custom.json" if is_temp else "/teddycloud/config/tonies.custom.json"
    logger.debug(f"Target path in container: {target_path}")
    try:
        logger.info(f"Copying {source_file} to {teddycloud_container}:{target_path}")
        subprocess.run([
            "docker", "cp", str(source_file), f"{teddycloud_container}:{target_path}"
        ], check=True)
        if is_temp:
            logger.info(f"Removing temporary container: {teddycloud_container}")
            subprocess.run(["docker", "rm", "-f", teddycloud_container], check=True)
            logger.success(f"Temporary container {teddycloud_container} removed.")
        logger.success("tonies.custom.json injected successfully.")
        return {"status": "success", "is_temp": is_temp, "container": teddycloud_container}
    except Exception as e:
        logger.error(f"Error injecting tonies.custom.json: {e}")
        return {"status": "error", "message": str(e)}


def extract_toniebox_information(config_manager):
    """
    Logic to extract Toniebox information from config.overlay.ini in the Docker config volume.
    Returns a dict with status and data for the UI to handle.
    """
    temp_dir = tempfile.gettempdir()
    temp_ini_path = Path(temp_dir) / "config.overlay.ini"
    try:
        result = subprocess.run([
            "docker", "ps", "--format", "{{.Names}}"
        ], check=True, capture_output=True, text=True)
        running_containers = [c for c in result.stdout.strip().split("\n") if c]
        teddycloud_container = "teddycloud-app" if "teddycloud-app" in running_containers else None
    except Exception:
        teddycloud_container = None
    ini_in_container = "/teddycloud/config/config.overlay.ini"
    ini_in_volume = "/config/config.overlay.ini"
    temp_container_name = "temp_teddycloud_ini_extractor"
    copied = False
    if teddycloud_container:
        try:
            subprocess.run([
                "docker", "cp", f"{teddycloud_container}:{ini_in_container}", str(temp_ini_path)
            ], check=True)
            copied = True
        except Exception:
            pass
    if not copied:
        try:
            subprocess.run([
                "docker", "rm", "-f", temp_container_name], check=False)
            subprocess.run([
                "docker", "create", "--name", temp_container_name, "-v", "teddycloudstarter_config:/config", "nginx:alpine"
            ], check=True)
            subprocess.run([
                "docker", "cp", f"{temp_container_name}:{ini_in_volume}", str(temp_ini_path)
            ], check=True)
            subprocess.run([
                "docker", "rm", "-f", temp_container_name
            ], check=False)
            copied = True
        except Exception as e:
            return {"status": "error", "message": f"Failed to extract config.overlay.ini: {e}"}
    if not temp_ini_path.exists():
        return {"status": "error", "message": "config.overlay.ini not found"}
    boxes = {}
    pattern = re.compile(r"overlay\.([A-Fa-f0-9]{12})\.(.+?)=(.+)", re.IGNORECASE)
    with open(temp_ini_path, "r", encoding="utf-8") as f:
        for line in f:
            m = pattern.match(line.strip())
            if m:
                mac, key, value = m.groups()
                if mac not in boxes:
                    boxes[mac] = {}
                boxes[mac][key] = value
    boxes_by_mac = {}
    for mac, data in boxes.items():
        mac_lower = mac.lower()
        boxes_by_mac[mac_lower] = {
            "commonName": data.get("commonName", mac_lower),
            "boxName": data.get("boxName", ""),
            "boxModel": data.get("boxModel", ""),
            "certdir": data.get("core.certdir", ""),
            "macaddress": mac_lower,
            "api_access": data.get("toniebox.api_access", "")
        }
    box_list = list(boxes_by_mac.values())

    # --- Begin certificate extraction, conversion, and copy-back ---
    for box in box_list:
        certdir = box.get("certdir")
        if not certdir:
            continue
        certdir_path = Path(certdir)
        mac_lower = box["macaddress"].lower()
        docker_certdir = f"/teddycloud/certs/client/{mac_lower}/"
        der_files = {
            "ca": certdir_path / "ca.der",
            "crt": certdir_path / "client.der",
            "key": certdir_path / "private.der"
        }
        temp_pem_files = {}
        temp_der_files = {}
        for key, der_path in der_files.items():
            temp_der = Path(tempfile.gettempdir()) / der_path.name
            try:
                subprocess.run([
                    "docker", "cp", f"teddycloud-app:{docker_certdir}{der_path.name}", str(temp_der)
                ], check=True)
                temp_der_files[key] = temp_der
                # Get fingerprint of the .der file
                try:
                    fingerprint = get_certificate_fingerprint(temp_der)
                    box[f"{key}_fingerprint"] = fingerprint
                except Exception:
                    box[f"{key}_fingerprint"] = None
            except Exception:
                continue  # If .der file doesn't exist, skip
            temp_pem = temp_der.with_suffix('.pem')
            try:
                if key == "key":
                    der_to_pem_key(temp_der, temp_pem, key_type="rsa")
                else:
                    der_to_pem_cert(temp_der, temp_pem)
                temp_pem_files[key] = temp_pem
            except Exception:
                continue
        for key, temp_pem in temp_pem_files.items():
            try:
                subprocess.run([
                    "docker", "cp", str(temp_pem), f"teddycloud-app:{docker_certdir}{temp_pem.name}"
                ], check=True)
                box[f"{key}_pem"] = str(certdir_path / temp_pem.name)
                # Ensure private.pem is readable by nginx
                if key == "key":
                    subprocess.run([
                        "docker", "exec", "teddycloud-app", "chmod", "0644", f"{docker_certdir}{temp_pem.name}"
                    ], check=True)
            except Exception:
                pass
        for temp_file in list(temp_der_files.values()) + list(temp_pem_files.values()):
            try:
                temp_file.unlink(missing_ok=True)
            except Exception:
                pass

    # --- Convert root CA certificate and create CA chain ---
    logger.info("Converting root CA certificate and creating CA chain")
    temp_root_ca_der = Path(tempfile.gettempdir()) / "ca.der"
    temp_root_ca_pem = Path(tempfile.gettempdir()) / "ca.pem"
    root_ca_path_in_container = "/teddycloud/certs/client/ca.der"
    
    try:
        # Download and convert the root CA certificate
        subprocess.run([
            "docker", "cp", f"teddycloud-app:{root_ca_path_in_container}", str(temp_root_ca_der)
        ], check=True)
        
        # Convert root CA from DER to PEM
        der_to_pem_cert(temp_root_ca_der, temp_root_ca_pem)
        
        # Upload the converted root CA.pem back to the container
        subprocess.run([
            "docker", "cp", str(temp_root_ca_pem), "teddycloud-app:/teddycloud/certs/client/ca.pem"
        ], check=True)
        
        # Collect all unique ca.pem files
        unique_ca_pems = {temp_root_ca_pem.read_bytes(): temp_root_ca_pem}  # Use file content as key to ensure uniqueness
        temp_ca_chain_pem = Path(tempfile.gettempdir()) / "ca_chain.pem"
        
        # Collect all ca.pem files from MAC directories
        for box in box_list:
            mac_lower = box["macaddress"].lower()
            temp_box_ca_pem = Path(tempfile.gettempdir()) / f"{mac_lower}_ca.pem"
            
            try:
                # Copy ca.pem from toniebox directory
                subprocess.run([
                    "docker", "cp", f"teddycloud-app:/teddycloud/certs/client/{mac_lower}/ca.pem", str(temp_box_ca_pem)
                ], check=True)
                
                # Add to unique collection if it doesn't exist yet
                ca_content = temp_box_ca_pem.read_bytes()
                if ca_content not in unique_ca_pems:
                    unique_ca_pems[ca_content] = temp_box_ca_pem
            except Exception:
                logger.debug(f"No ca.pem found for {mac_lower} or other error")
                continue
        
        # Combine all unique CA certificates into a chain file
        with open(temp_ca_chain_pem, "wb") as chain_file:
            for ca_content, ca_file in unique_ca_pems.items():
                chain_file.write(ca_content)
                chain_file.write(b"\n")  # Add newline between certificates
        
        # Upload the CA chain file back to the container
        subprocess.run([
            "docker", "cp", str(temp_ca_chain_pem), "teddycloud-app:/teddycloud/certs/client/ca_chain.pem"
        ], check=True)
        
        logger.success("CA chain file created successfully")
    except Exception as e:
        logger.error(f"Failed to create CA chain: {e}")
    finally:
        # Clean up temporary files
        for file in [temp_root_ca_der, temp_root_ca_pem, temp_ca_chain_pem]:
            try:
                file.unlink(missing_ok=True)
            except Exception:
                pass
        # Clean up any box-specific CA files
        for box in box_list:
            try:
                (Path(tempfile.gettempdir()) / f"{box['macaddress'].lower()}_ca.pem").unlink(missing_ok=True)
            except Exception:
                pass

    # --- Begin server certificate extraction, conversion, copy-back, and renaming for nginx ---
    server_cert_path = "/teddycloud/certs/server/teddy-cert.pem"
    server_key_path = "/teddycloud/certs/server/teddy-key.pem"
    temp_server_cert = Path(tempfile.gettempdir()) / "teddy-cert.pem"
    temp_server_key = Path(tempfile.gettempdir()) / "teddy-key.pem"
    temp_server_cert_nginx = Path(tempfile.gettempdir()) / "teddy-cert.nginx.pem"
    temp_server_key_nginx = Path(tempfile.gettempdir()) / "teddy-key.nginx.pem"
    try:
        subprocess.run([
            "docker", "cp", f"teddycloud-app:{server_cert_path}", str(temp_server_cert)
        ], check=True)
        subprocess.run([
            "docker", "cp", f"teddycloud-app:{server_key_path}", str(temp_server_key)
        ], check=True)
        # Check if the cert is already PEM (open as binary)
        with open(temp_server_cert, "rb") as f:
            first_bytes = f.read(32)
        if first_bytes.startswith(b"-----BEGIN"):
            # Already PEM, just copy as nginx.pem
            temp_server_cert_nginx.write_bytes(temp_server_cert.read_bytes())
        else:
            # Convert to PEM format for nginx
            der_to_pem_cert(temp_server_cert, temp_server_cert_nginx)
        # Check if the key is already PEM (open as binary)
        with open(temp_server_key, "rb") as f:
            first_bytes = f.read(32)
        if first_bytes.startswith(b"-----BEGIN"):
            temp_server_key_nginx.write_bytes(temp_server_key.read_bytes())
        else:
            der_to_pem_key(temp_server_key, temp_server_key_nginx, key_type="rsa")
        # Copy back as .nginx.pem
        subprocess.run([
            "docker", "cp", str(temp_server_cert_nginx), f"teddycloud-app:/teddycloud/certs/server/teddy-cert.nginx.pem"
        ], check=True)
        subprocess.run([
            "docker", "cp", str(temp_server_key_nginx), f"teddycloud-app:/teddycloud/certs/server/teddy-key.nginx.pem"
        ], check=True)
        # --- Begin: Check if .nginx.pem files exist in the container ---
        check_cert = subprocess.run([
            "docker", "exec", "teddycloud-app", "test", "-f", "/teddycloud/certs/server/teddy-cert.nginx.pem"
        ])
        check_key = subprocess.run([
            "docker", "exec", "teddycloud-app", "test", "-f", "/teddycloud/certs/server/teddy-key.nginx.pem"
        ])
        if check_cert.returncode != 0 or check_key.returncode != 0:
            raise FileNotFoundError("Failed to copy .nginx.pem files into the container.")
        # --- End: Check if .nginx.pem files exist in the container ---
    except Exception as e:
        return {"status": "error", "message": f"Server certificate copy/conversion failed: {e}"}
    finally:
        for f in [temp_server_cert, temp_server_key, temp_server_cert_nginx, temp_server_key_nginx]:
            try:
                f.unlink(missing_ok=True)
            except Exception:
                pass
    # --- End server certificate extraction, conversion, copy-back, and renaming for nginx ---

    # --- End certificate extraction, conversion, and copy-back ---

    config_manager.config["boxes"] = box_list
    config_manager.save()
    try:
        temp_ini_path.unlink(missing_ok=True)
    except Exception:
        pass
    return {"status": "success", "boxes": box_list}
