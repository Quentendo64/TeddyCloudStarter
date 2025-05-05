#!/usr/bin/env python3
"""
UI module for Nginx mode configuration in TeddyCloudStarter.
"""

import questionary
from rich import box
from rich.panel import Panel

from ..utilities.validation import validate_domain_name
from ..wizard.ui_helpers import console, custom_style
from ..utilities.logger import logger


def display_letsencrypt_not_available_warning(domain, translator):
    """
    Display a warning that Let's Encrypt is not available for the domain.

    Args:
        domain: The domain name
        translator: The translator instance for localization
    """
    logger.debug(f"Displaying Let's Encrypt not available warning for domain: {domain}")
    console.print(
        Panel(
            f"[bold yellow]{translator.get('Let\'s Encrypt Not Available')}[/]\n\n"
            f"{translator.get('The domain')} \"{domain}\" {translator.get('could not be resolved using public DNS servers (Quad9)')}\n"
            f"{translator.get('Let\'s Encrypt requires a publicly resolvable domain to issue certificates.')}\n"
            f"{translator.get('You can use self-signed or custom certificates for your setup.')}",
            box=box.ROUNDED,
            border_style="yellow",
        )
    )


def display_letsencrypt_requirements(translator):
    """
    Display Let's Encrypt requirements panel.

    Args:
        translator: The translator instance for localization
    """
    logger.debug("Displaying Let's Encrypt requirements panel.")
    console.print(
        Panel(
            f"[bold yellow]{translator.get('Let\'s Encrypt Requirements')}[/]\n\n"
            f"{translator.get('To use Let\'s Encrypt, you need:')}\n"
            f"1. {translator.get('A public domain name pointing to this server')}\n"
            f"2. {translator.get('Public internet access on ports 80 and 443')}\n"
            f"3. {translator.get('This server must be reachable from the internet')}",
            box=box.ROUNDED,
            border_style="yellow",
        )
    )


def display_letsencrypt_rate_limit_disclaimer(translator):
    """
    Display a disclaimer about Let's Encrypt rate limits.

    Args:
        translator: The translator instance for localization
    """
    logger.debug("Displaying Let's Encrypt rate limit disclaimer.")
    console.print(
        Panel(
            f"[bold red]{translator.get('Let\'s Encrypt Rate Limits Disclaimer')}[/]\n\n"
            f"{translator.get('Let\'s Encrypt enforces rate limits on certificate requests. Exceeding these limits may prevent you from obtaining or renewing certificates for a period of time.')}\n\n"
            f"- {translator.get('Certificates per Registered Domain: 50 per week')}\n"
            f"- {translator.get('Duplicate Certificate limit: 5 per week')}\n"
            f"- {translator.get('Failed Validation limit: 5 failures per account, per hostname, per hour')}\n\n"
            f"{translator.get('For full details, see:')} https://letsencrypt.org/docs/rate-limits/",
            box=box.ROUNDED,
            border_style="red",
        )
    )


def confirm_letsencrypt_requirements(translator):
    """
    Ask user to confirm they meet Let's Encrypt requirements.

    Args:
        translator: The translator instance for localization

    Returns:
        bool: True if confirmed, False otherwise
    """
    return questionary.confirm(
        translator.get("Do you meet these requirements?"),
        default=True,
        style=custom_style,
    ).ask()


def confirm_test_certificate(translator):
    """
    Ask user if they want to test if Let's Encrypt can issue a certificate.

    Args:
        translator: The translator instance for localization

    Returns:
        bool: True if confirmed, False otherwise
    """
    return questionary.confirm(
        translator.get(
            "Would you like to test if Let's Encrypt can issue a certificate for your domain?"
        ),
        default=True,
        style=custom_style,
    ).ask()


def prompt_security_type(translator):
    """
    Prompt user to select a security type.

    Args:
        translator: The translator instance for localization

    Returns:
        str: The selected security type identifier ('none', 'basic_auth', or 'client_cert')
    """
    choices = [
        {"id": "none", "text": translator.get("No additional security")},
        {
            "id": "basic_auth",
            "text": translator.get("Basic Authentication (.htpasswd)"),
        },
        {"id": "client_cert", "text": translator.get("Client Certificates")},
    ]

    choice_texts = [choice["text"] for choice in choices]
    selected_text = questionary.select(
        translator.get("How would you like to secure your TeddyCloud instance?"),
        choices=choice_texts,
        style=custom_style,
    ).ask()

    for choice in choices:
        if choice["text"] == selected_text:
            return choice["id"]

    return "none"


def prompt_htpasswd_option(translator):
    """
    Prompt user to select how to handle .htpasswd file.

    Args:
        translator: The translator instance for localization

    Returns:
        str: The selected option identifier ('generate' or 'provide')
    """
    choices = [
        {
            "id": "generate",
            "text": translator.get("Generate .htpasswd file with the wizard"),
        },
        {"id": "provide", "text": translator.get("I'll provide my own .htpasswd file")},
    ]

    choice_texts = [choice["text"] for choice in choices]
    selected_text = questionary.select(
        translator.get("How would you like to handle the .htpasswd file?"),
        choices=choice_texts,
        style=custom_style,
    ).ask()

    for choice in choices:
        if choice["text"] == selected_text:
            return choice["id"]

    return "generate"


def prompt_client_cert_source(translator):
    """
    Prompt user to select how to handle client certificates.

    Args:
        translator: The translator instance for localization

    Returns:
        str: The selected option identifier ('generate' or 'provide')
    """
    choices = [
        {"id": "generate", "text": translator.get("Generate certificates for me")},
        {"id": "provide", "text": translator.get("I'll provide my own certificates")},
    ]

    choice_texts = [choice["text"] for choice in choices]
    selected_text = questionary.select(
        translator.get("How would you like to handle client certificates?"),
        choices=choice_texts,
        style=custom_style,
    ).ask()

    for choice in choices:
        if choice["text"] == selected_text:
            return choice["id"]

    return "generate"


def display_domain_not_resolvable_warning(domain, translator):
    """
    Display warning that domain is not resolvable.

    Args:
        domain: The domain name
        translator: The translator instance for localization
    """
    console.print(
        Panel(
            f"[bold yellow]{translator.get('Domain Not Resolvable')}[/]\n\n"
            f"{translator.get('The domain')} '{domain}' {translator.get('could not be resolved using public DNS servers.')}\n"
            f"{translator.get('If using Let\'s Encrypt, make sure the domain is publicly resolvable.')}",
            box=box.ROUNDED,
            border_style="yellow",
        )
    )


def confirm_switch_to_self_signed(translator):
    """
    Ask user if they want to switch from Let's Encrypt to self-signed certificates.

    Args:
        translator: The translator instance for localization

    Returns:
        bool: True if confirmed, False otherwise
    """
    return questionary.confirm(
        translator.get(
            "Would you like to switch from Let's Encrypt to self-signed certificates?"
        ),
        default=True,
        style=custom_style,
    ).ask()


def confirm_change_security_method(translator):
    """
    Ask user if they want to return to the security selection menu.

    Args:
        translator: The translator instance for localization

    Returns:
        bool: True if confirmed, False otherwise
    """
    return questionary.confirm(
        translator.get("Do you want to return to the security selection menu?"),
        default=False,
        style=custom_style,
    ).ask()


def select_https_mode_for_modification(current_mode, translator):
    """
    Prompt user to select HTTPS mode when modifying configuration.

    Args:
        current_mode: Current HTTPS mode identifier
        translator: The translator instance for localization

    Returns:
        str: The selected HTTPS mode identifier ('letsencrypt', 'self_signed', or 'user_provided')
    """
    choices = [
        {
            "id": "letsencrypt",
            "text": translator.get("Let's Encrypt (automatic certificates)"),
        },
        {
            "id": "self_signed",
            "text": translator.get("Create self-signed certificates"),
        },
        {
            "id": "user_provided",
            "text": translator.get("Custom certificates (provide your own)"),
        },
    ]
    valid_ids = [c["id"] for c in choices]
    if current_mode in valid_ids:
        default_value = current_mode
    else:
        default_value = choices[0]["id"]

    selected = questionary.select(
        translator.get("Select new HTTPS mode:"),
        choices=[{"value": c["id"], "name": c["text"]} for c in choices],
        default=default_value,
        style=custom_style,
    ).ask()
    selected_choice = next(c for c in choices if c["id"] == selected)
    return selected_choice["text"], selected


def select_security_type_for_modification(current_security_type, translator):
    """
    Prompt user to select security type when modifying configuration.

    Args:
        current_security_type: Current security type identifier
        translator: The translator instance for localization

    Returns:
        str: The selected security type identifier ('none', 'basic_auth', or 'client_cert')
    """
    choices = [
        {"id": "none", "text": translator.get("No additional security")},
        {
            "id": "basic_auth",
            "text": translator.get("Basic Authentication (.htpasswd)"),
        },
        {"id": "client_cert", "text": translator.get("Client Certificates")},
    ]

    choice_texts = [choice["text"] for choice in choices]
    # Only set default if current_security_type is valid
    valid_ids = [choice["id"] for choice in choices]
    if current_security_type in valid_ids:
        default_text = next(
            (
                choice["text"]
                for choice in choices
                if choice["id"] == current_security_type
            ),
            choice_texts[0],
        )
    else:
        default_text = choice_texts[0]

    selected_text = questionary.select(
        translator.get("How would you like to secure your TeddyCloud instance?"),
        choices=choice_texts,
        default=default_text,
        style=custom_style,
    ).ask()

    for choice in choices:
        if choice["text"] == selected_text:
            return choice["id"]

    return "none"


def prompt_for_fallback_option(translator):
    """
    Ask user what they want to do if self-signed certificate generation fails.

    Args:
        translator: The translator instance for localization

    Returns:
        str: The selected option identifier ('try_again' or 'switch_to_custom')
    """
    choices = [
        {
            "id": "try_again",
            "text": translator.get("Try generating the self-signed certificate again"),
        },
        {
            "id": "switch_to_custom",
            "text": translator.get(
                "Switch to custom certificate mode (provide your own certificates)"
            ),
        },
    ]

    choice_texts = [choice["text"] for choice in choices]
    selected_text = questionary.select(
        translator.get("What would you like to do?"),
        choices=choice_texts,
        style=custom_style,
    ).ask()

    for choice in choices:
        if choice["text"] == selected_text:
            return choice["id"]

    return "try_again"


def prompt_for_domain(current_domain="", translator=None):
    """
    Prompt user to enter a domain name.

    Args:
        current_domain: Current domain name (if any)
        translator: The translator instance for localization

    Returns:
        str: The entered domain name
    """
    return questionary.text(
        "Enter the domain name for your TeddyCloud instance:",
        default=current_domain,
        validate=lambda d: validate_domain_name(d),
        style=custom_style,
    ).ask()


def prompt_for_https_mode(https_choices, default_choice_value, translator):
    """Prompt for HTTPS mode.

    Args:
        https_choices: List of available HTTPS mode choices
        default_choice_value: The default HTTPS mode value string
        translator: The translator instance for localization

    Returns:
        str: The selected HTTPS mode value string
    """
    formatted_choices = []

    for choice in https_choices:
        # Handle id/text format (old format)
        if isinstance(choice, dict) and "id" in choice and "text" in choice:
            formatted_choices.append({"value": choice["id"], "name": choice["text"]})

    # Extract valid values for validation
    valid_values = [choice["value"] for choice in formatted_choices]

    # Find the actual choice dictionary corresponding to the default value
    default_choice_obj = None
    if default_choice_value in valid_values:
        default_choice_obj = next(
            (
                choice
                for choice in formatted_choices
                if choice["value"] == default_choice_value
            ),
            None,
        )

    # If the provided default value isn't valid or not found, fall back to the first choice object
    if not default_choice_obj:
        if formatted_choices:
            default_choice_obj = formatted_choices[0]
        else:
            # Fallback option if no choices are available (should never happen)
            console.print(
                f"[bold red]{translator.get('Error: No HTTPS choices available.')}[/]"
            )
            return None

    # Create the questionary selection, passing the choice object as default
    selected_value = questionary.select(
        translator.get("Select HTTPS mode:"),
        choices=formatted_choices,
        default=default_choice_obj,  # Pass the dictionary object
        style=custom_style,
    ).ask()  # ask() returns the 'value' of the selected choice

    return selected_value  # Return the selected value string


def display_self_signed_certificate_info(domain, translator):
    """Display information about self-signed certificates.

    Args:
        domain: The domain name for the certificate
        translator: The translator instance for localization
    """
    console.print(
        f"[bold cyan]{translator.get('Generating self-signed certificates for')} {domain}...[/]"
    )
    console.print(
        f"[yellow]{translator.get('Note: Self-signed certificates will cause browser warnings. They are recommended only for testing.')}[/]"
    )


def prompt_client_cert_name(translator):
    """Prompt for client certificate name.

    Args:
        translator: The translator instance for localization

    Returns:
        str: The entered client name
    """
    return questionary.text(
        translator.get(
            "Enter a name for the client certificate (e.g., 'admin', 'my-device'):"
        ),
        style=custom_style,
    ).ask()


def prompt_modify_ip_restrictions(translator):
    """Prompt for IP restriction modification options.

    Args:
        translator: The translator instance for localization

    Returns:
        str: The selected IP restriction action
    """
    return questionary.select(
        translator.get("IP restriction options:"),
        choices=[
            {"id": "add", "text": translator.get("Add IP address")},
            {"id": "remove", "text": translator.get("Remove IP address")},
            {"id": "clear", "text": translator.get("Clear all IP restrictions")},
            {"id": "back", "text": translator.get("Back")},
        ],
        style=custom_style,
    ).ask()


def confirm_continue_anyway(translator):
    """Confirm if user wants to continue despite port issues.

    Args:
        translator: The translator instance for localization

    Returns:
        bool: True if user wants to continue, False otherwise
    """
    return questionary.confirm(
        translator.get("Would you like to proceed anyway?"),
        default=False,
        style=custom_style,
    ).ask()


def display_waiting_for_htpasswd(htpasswd_path, translator):
    """Display .htpasswd waiting message.

    Args:
        htpasswd_path: Path where .htpasswd file is expected
        translator: The translator instance for localization
    """
    console.print(
        f"[bold cyan]{translator.get('Waiting for .htpasswd file at')} {htpasswd_path}[/]"
    )
    console.print(f"[yellow]{translator.get('Press Ctrl+C to cancel at any time')}[/]")


def prompt_client_cert_password(translator):
    """
    Prompt user to optionally set a custom password for the client certificate bundle (.p12 file).

    Args:
        translator: The translator instance for localization

    Returns:
        str or None: The password entered by the user, or None to use the default
    """
    use_custom_password = questionary.confirm(
        translator.get(
            "Would you like to set a custom password for the client certificate bundle (.p12 file)?"
        ),
        default=False,
        style=custom_style,
    ).ask()

    if use_custom_password:
        password = questionary.password(
            translator.get("Enter password for the certificate bundle (min 4 characters):"),
            validate=lambda text: len(text) >= 4,
            style=custom_style,
        ).ask()
        return password
    return None


def prompt_nginx_type(translator):
    """
    Prompt user to select the Nginx type (standard or extended).

    Args:
        translator: The translator instance for localization

    Returns:
        str: The selected nginx_type ('standard' or 'extended')
    """
    choices = [
        {"id": "standard", "text": translator.get("Standard (default)")},
        #{"id": "extended", "text": translator.get("Extended (advanced features)")},
    ]
    choice_texts = [choice["text"] for choice in choices]
    selected_text = questionary.select(
        translator.get("Select Nginx mode type:"),
        choices=choice_texts,
        style=custom_style,
    ).ask()
    for choice in choices:
        if choice["text"] == selected_text:
            return choice["id"]
    return "standard"
