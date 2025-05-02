#!/usr/bin/env python3
"""
Let's Encrypt helper functions for TeddyCloudStarter.
"""
from ..utilities.network import check_domain_resolvable, check_port_available
from ..ui.letsencrypt_ui import (
    display_letsencrypt_requirements,
    confirm_letsencrypt_requirements,
    confirm_test_certificate,
    display_letsencrypt_not_available_warning,
    display_domain_not_resolvable_warning,
    confirm_switch_to_self_signed
)
from ..wizard.ui_helpers import console, custom_style
import questionary
import subprocess
import time

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
    
    domain_resolvable = check_domain_resolvable(domain)
    
    if not domain_resolvable:
        display_letsencrypt_not_available_warning(domain, translator)
        return False
        
    display_letsencrypt_requirements(translator)
    
    if not confirm_letsencrypt_requirements(translator):
        return False
    
    port_available = check_port_available(80)
    if not port_available:
        console.print(f"[bold yellow]{translator.get('Warning: Port 80 appears to be in use')}")
        console.print(f"[yellow]{translator.get('Let\'s Encrypt requires port 80 to be available for domain verification')}")
        
        use_anyway = questionary.confirm(
            translator.get("Would you like to proceed anyway? (Certbot will attempt to bind to port 80)"),
            default=False,
            style=custom_style
        ).ask()
        
        if not use_anyway:
            return False
    
    if confirm_test_certificate(translator):
        console.print(f"[bold cyan]{translator.get('Requesting Let\'s Encrypt certificate (staging) using standalone mode...')}[/]")
        staging_result = lets_encrypt_manager.request_certificate(
            domain=domain,
            mode="standalone",
            staging=True
        )
        
        if not staging_result:
            console.print(f"[bold red]{translator.get('Staging certificate request failed. Your domain may not be properly configured for Let\'s Encrypt.')}[/]")
            return False
        
        console.print(f"[bold green]{translator.get('Staging certificate request successful! Your domain is properly configured for Let\'s Encrypt.')}[/]")
        
        proceed_with_production = questionary.confirm(
            translator.get("Do you want to proceed with requesting production certificates?"),
            default=True,
            style=custom_style
        ).ask()
        
        if not proceed_with_production:
            console.print(f"[bold yellow]{translator.get('Production certificate request skipped. You can request production certificates later.')}[/]")
            return True
            
        console.print(f"[bold cyan]{translator.get('Requesting Let\'s Encrypt certificate (production) using standalone mode...')}[/]")
        
        production_result = lets_encrypt_manager.request_certificate(
            domain=domain,
            mode="standalone",
            staging=False
        )
        
        if not production_result:
            console.print(f"[bold red]{translator.get('Production certificate request failed. You may need to try again later.')}[/]")
            return True
            
        console.print(f"[bold green]{translator.get('Production certificate request successful! Your Let\'s Encrypt certificate is ready to use.')}[/]")
        return True
    
    return True

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
    domain_resolvable = check_domain_resolvable(domain)
    
    if not domain_resolvable:
        display_domain_not_resolvable_warning(domain, translator)
        
        if current_https_mode == "letsencrypt":
            return confirm_switch_to_self_signed(translator)
    
    return domain_resolvable

def switch_to_letsencrypt_https_mode(config, translator, lets_encrypt_manager):
    """
    Switch HTTPS mode from self-signed/user-provided to Let's Encrypt.
    
    Args:
        config: The configuration dictionary
        translator: The translator instance for localization
        lets_encrypt_manager: The Let's Encrypt manager instance
        
    Returns:
        bool: True if switch was successful, False otherwise
    """
    is_running = False
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}", "--filter", "name=nginx-edge"],
            capture_output=True, text=True, check=True
        )
        is_running = "nginx-edge" in result.stdout
    except Exception:
        is_running = False
    
    try:
        config["nginx"]["https_mode"] = "letsencrypt"
        
        from ..configuration.generator import generate_nginx_configs, generate_docker_compose
        from ..configurations import TEMPLATES
        
        console.print(f"[bold cyan]{translator.get('Regenerating nginx configuration for Let\'s Encrypt...')}[/]")
        
        if not generate_nginx_configs(config, translator, TEMPLATES):
            console.print(f"[bold red]{translator.get('Failed to regenerate nginx configuration')}[/]")
            return False
            
        console.print(f"[bold cyan]{translator.get('Regenerating docker-compose configuration...')}[/]")
        
        if not generate_docker_compose(config, translator, TEMPLATES):
            console.print(f"[bold red]{translator.get('Failed to regenerate docker-compose configuration')}[/]")
            return False
        
        try:
            subprocess.run(
                ["docker", "rm", "-f", "certbot-temp"],
                capture_output=True
            )
        except Exception:
            pass
        
        if is_running:
            console.print(f"[bold cyan]{translator.get('Restarting nginx-edge to apply new configuration...')}[/]")
            try:
                subprocess.run(["docker", "restart", "nginx-edge"], check=True)
                time.sleep(3)
            except Exception as e:
                console.print(f"[bold yellow]{translator.get('Warning: Failed to restart nginx-edge:')} {e}[/]")
        
        return True
        
    except Exception as e:
        console.print(f"[bold red]{translator.get('Error updating configuration:')} {e}[/]")
        return False