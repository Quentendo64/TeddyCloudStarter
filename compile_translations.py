#!/usr/bin/env python3
"""
Compiles translation .po files to .mo files.
This script should be run after updating any translations.
"""

import os
import subprocess
import sys
from pathlib import Path

def compile_translations():
    """Compile all .po files to .mo files."""
    locales_dir = Path("TeddyCloudStarter/locales")
    
    if not locales_dir.exists():
        print(f"No 'locales' directory found at {locales_dir}.")
        return
    
    for lang_dir in locales_dir.glob('*'):
        if not lang_dir.is_dir():
            continue
        
        lc_messages_dir = lang_dir / "LC_MESSAGES"
        if not lc_messages_dir.exists():
            os.makedirs(lc_messages_dir, exist_ok=True)
        
        po_file = lc_messages_dir / "teddycloudstarter.po"
        if not po_file.exists():
            print(f"No PO file found for {lang_dir.name}.")
            continue
        
        mo_file = lc_messages_dir / "teddycloudstarter.mo"
        
        try:
            # Try to use msgfmt if available (part of gettext tools)
            subprocess.run(["msgfmt", str(po_file), "-o", str(mo_file)], check=True)
            print(f"âœ“ Compiled {po_file} to {mo_file}")
        except (subprocess.SubprocessError, FileNotFoundError):
            # If msgfmt is not available, use polib
            try:
                import polib
                po = polib.pofile(str(po_file))
                po.save_as_mofile(str(mo_file))
                print(f"âœ“ Compiled {po_file} to {mo_file} using polib")
            except ImportError:
                print("Error: Neither msgfmt nor polib is available.")
                print("Please install gettext tools or run: pip install polib")
                return

if __name__ == "__main__":
    compile_translations()