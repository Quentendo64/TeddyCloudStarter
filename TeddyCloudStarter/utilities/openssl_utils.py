import subprocess
from pathlib import Path

def der_to_pem_cert(der_path, pem_path):
    """
    Convert a DER-encoded certificate to PEM format using OpenSSL.

    Args:
        der_path (str or Path): Path to the input DER certificate file.
        pem_path (str or Path): Path to the output PEM certificate file.

    Raises:
        RuntimeError: If the OpenSSL command fails.
    """
    der_path = str(der_path)
    pem_path = str(pem_path)
    result = subprocess.run([
        "openssl", "x509", "-inform", "der", "-in", der_path, "-out", pem_path
    ], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"OpenSSL error: {result.stderr.strip()}")
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
    der_path = str(der_path)
    pem_path = str(pem_path)
    tried_pkcs8 = False
    if key_type == "ec":
        cmd = ["openssl", "ec", "-inform", "der", "-in", der_path, "-out", pem_path]
    else:
        cmd = ["openssl", "rsa", "-inform", "der", "-in", der_path, "-out", pem_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Try PKCS#8 fallback
        cmd = [
            "openssl", "pkcs8", "-inform", "der", "-in", der_path, "-out", pem_path, "-outform", "PEM", "-nocrypt"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        tried_pkcs8 = True
    if result.returncode != 0:
        raise RuntimeError(f"OpenSSL error (rsa/ec{' then pkcs8' if tried_pkcs8 else ''}): {result.stderr.strip()}")
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
    cert_path = str(cert_path)
    result = subprocess.run([
        "openssl", "x509", "-noout", "-fingerprint", f"-{hash_algo}", "-in", cert_path
    ], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"OpenSSL error: {result.stderr.strip()}")
    # Output is like: 'SHA256 Fingerprint=AA:BB:...'
    line = result.stdout.strip()
    if '=' in line:
        return line.split('=', 1)[1]
    return line
