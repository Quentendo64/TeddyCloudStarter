#!/usr/bin/env python3
"""
Let's Encrypt helper functions for TeddyCloudStarter.
"""
from ..utilities.network import check_domain_resolvable
from ..ui.letsencrypt_ui import (
    display_letsencrypt_requirements,
    confirm_letsencrypt_requirements,
    confirm_test_certificate,
    display_letsencrypt_not_available_warning,
    display_domain_not_resolvable_warning,
    confirm_switch_to_self_signed
)

def handle_letsencrypt_setup(nginx_config, translator, lets_encrypt_manager):
    """
    Handle Let's Encrypt certificate setup.
    
    Args:
        nginx_config: The nginx configuration dictionary
        translator: The translator instance for localization
        lets_encrypt_manager: The Let's Encrypt manager instance
        
    Returns:
        bool: True if Let's Encrypt setup was successful, False if fallback needed
    """
    domain = nginx_config["domain"]
    
    # Check if domain is publicly resolvable
    domain_resolvable = check_domain_resolvable(domain)
    
    if not domain_resolvable:
        display_letsencrypt_not_available_warning(domain, translator)
        return False
        
    # Warn about Let's Encrypt requirements
    display_letsencrypt_requirements(translator)
    
    if not confirm_letsencrypt_requirements(translator):
        return False
        
    # Test if domain is properly set up
    if confirm_test_certificate(translator):
        result = lets_encrypt_manager.request_certificate(domain)
        return result
    
    return True  # User chose not to test, but we'll continue with Let's Encrypt

def check_domain_suitable_for_letsencrypt(domain, translator, current_https_mode=None):
    """
    Check if domain is suitable for Let's Encrypt and handle warnings.
    
    Args:
        domain: Domain to check
        translator: The translator instance for localization
        current_https_mode: Optional current HTTPS mode from config
        
    Returns:
        bool: True if domain is suitable for Let's Encrypt
    """
    # Check if domain is publicly resolvable
    domain_resolvable = check_domain_resolvable(domain)
    
    if not domain_resolvable:
        display_domain_not_resolvable_warning(domain, translator)
        
        # If using Let's Encrypt, offer to change HTTPS mode
        if current_https_mode == "letsencrypt":
            return confirm_switch_to_self_signed(translator)
    
    return domain_resolvable