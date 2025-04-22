#!/usr/bin/env python3
"""
Utility functions for TeddyCloudStarter.
"""
import socket
import re
import ipaddress


def check_port_available(port: int) -> bool:
    """Check if a port is available on the system.
    
    Args:
        port: The port number to check
        
    Returns:
        bool: True if port is available, False otherwise
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return True
        except socket.error:
            return False


def validate_domain_name(domain: str) -> bool:
    """Validate a domain name format.
    
    Args:
        domain: The domain name to validate
        
    Returns:
        bool: True if valid domain, False otherwise
    """
    domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    return bool(re.match(domain_pattern, domain))


def validate_ip_address(ip_str: str) -> bool:
    """Validate an IP address or CIDR notation.
    
    Args:
        ip_str: The string to validate as IP or CIDR
        
    Returns:
        bool: True if valid IP or CIDR, False otherwise
    """
    try:
        ipaddress.ip_network(ip_str)
        return True
    except ValueError:
        return False