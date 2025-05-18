import subprocess
from pathlib import Path
from .logger import logger

def der_to_pem_cert(der_path, pem_path):
    """
    Convert a DER-encoded certificate to PEM format using OpenSSL.

    Args:
        der_path (str or Path): Path to the input DER certificate file.
        pem_path (str or Path): Path to the output PEM certificate file.

    Raises:
        RuntimeError: If the OpenSSL command fails.
    """
    logger.debug(f"Starting DER to PEM certificate conversion: der_path={der_path}, pem_path={pem_path}")
    der_path = str(der_path)
    pem_path = str(pem_path)
    result = subprocess.run([
        "openssl", "x509", "-inform", "der", "-in", der_path, "-out", pem_path
    ], capture_output=True, text=True)
    logger.debug(f"OpenSSL x509 command result: returncode={result.returncode}, stderr={result.stderr.strip()}")
    if result.returncode != 0:
        logger.error(f"OpenSSL error during DER to PEM cert conversion: {result.stderr.strip()}")
        raise RuntimeError(f"OpenSSL error: {result.stderr.strip()}")
    logger.info(f"DER to PEM certificate conversion successful: {pem_path}")
    return pem_path

def der_to_pem_key(der_path, pem_path, key_type="rsa"):
    """
    Convert a DER-encoded private key to PEM format using OpenSSL.

    Args:
        der_path (str or Path): Path to the input DER private key file.
        pem_path (str or Path): Path to the output PEM private key file.
        key_type (str): 'rsa' or 'ec'.

    Raises:
        RuntimeError: If the OpenSSL command fails.
    """
    logger.debug(f"Starting DER to PEM key conversion: der_path={der_path}, pem_path={pem_path}, key_type={key_type}")
    der_path = str(der_path)
    pem_path = str(pem_path)
    tried_pkcs8 = False
    if key_type == "ec":
        cmd = ["openssl", "ec", "-inform", "der", "-in", der_path, "-out", pem_path]
    else:
        cmd = ["openssl", "rsa", "-inform", "der", "-in", der_path, "-out", pem_path]
    logger.debug(f"Running OpenSSL command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    logger.debug(f"OpenSSL {key_type} command result: returncode={result.returncode}, stderr={result.stderr.strip()}")
    if result.returncode != 0:
        logger.warning(f"OpenSSL {key_type} command failed, trying PKCS#8 fallback.")
        cmd = [
            "openssl", "pkcs8", "-inform", "der", "-in", der_path, "-out", pem_path, "-outform", "PEM", "-nocrypt"
        ]
        logger.debug(f"Running OpenSSL PKCS#8 fallback command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        tried_pkcs8 = True
        logger.debug(f"OpenSSL pkcs8 command result: returncode={result.returncode}, stderr={result.stderr.strip()}")
    if result.returncode != 0:
        logger.error(f"OpenSSL error during DER to PEM key conversion (rsa/ec{' then pkcs8' if tried_pkcs8 else ''}): {result.stderr.strip()}")
        raise RuntimeError(f"OpenSSL error (rsa/ec{' then pkcs8' if tried_pkcs8 else ''}): {result.stderr.strip()}")
    logger.info(f"DER to PEM key conversion successful: {pem_path}")
    return pem_path

def get_certificate_fingerprint(cert_path, hash_algo="sha1"):
    """
    Get the fingerprint of a certificate file (DER or PEM) using OpenSSL.

    Args:
        cert_path (str or Path): Path to the certificate file.
        hash_algo (str): Hash algorithm to use (e.g., 'sha256', 'sha1').

    Returns:
        str: The fingerprint string (colon-separated hex bytes).

    Raises:
        RuntimeError: If the OpenSSL command fails.
    """
    logger.debug(f"Starting certificate fingerprint retrieval: cert_path={cert_path}, hash_algo={hash_algo}")
    cert_path = str(cert_path)
    result = subprocess.run([
        "openssl", "x509", "-noout", "-fingerprint", f"-{hash_algo}", "-in", cert_path
    ], capture_output=True, text=True)
    logger.debug(f"OpenSSL x509 fingerprint command result: returncode={result.returncode}, stderr={result.stderr.strip()}")
    if result.returncode != 0:
        logger.error(f"OpenSSL error during certificate fingerprint retrieval: {result.stderr.strip()}")
        raise RuntimeError(f"OpenSSL error: {result.stderr.strip()}")
    line = result.stdout.strip()
    logger.debug(f"Certificate fingerprint output: {line}")
    if '=' in line:
        fingerprint = line.split('=', 1)[1]
        logger.info(f"Certificate fingerprint retrieval successful: {fingerprint}")
        return fingerprint
    logger.info(f"Certificate fingerprint retrieval successful: {line}")
    return line
