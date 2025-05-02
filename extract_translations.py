#!/usr/bin/env python3
"""
Extract translatable strings from Python source files.

This script:
1. Extracts translatable strings using xgettext if available
2. Falls back to a basic string extraction if xgettext is not available
3. Updates existing .po files with msgmerge if available
"""

import os
import subprocess
import re
import glob
from pathlib import Path

PACKAGE_DIR = Path("TeddyCloudStarter")
LOCALES_DIR = PACKAGE_DIR / "locales"
POT_FILE = LOCALES_DIR / "teddycloudstarter.pot"

def extract_strings_with_xgettext():
    """Extract strings using xgettext."""
    print("Extracting strings with xgettext...")
    
    os.makedirs(LOCALES_DIR, exist_ok=True)
    
    python_files = []
    for root, _, files in os.walk(PACKAGE_DIR):
        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))
    
    if not python_files:
        print("No Python files found.")
        return False
    
    try:
        cmd = [
            "xgettext", 
            "--language=Python", 
            "--from-code=UTF-8",
            "--keyword=_", 
            "--keyword=get", 
            "--keyword=_translate",
            "--output=" + str(POT_FILE),
            "--package-name=TeddyCloudStarter",
            "--package-version=1.0.0",
            "--copyright-holder=TeddyCloud Team",
            "--msgid-bugs-address=https://github.com/quentendo64/teddycloudstarter/issues"
        ] + python_files
        
        subprocess.run(cmd, check=True)
        print(f"Strings extracted to {POT_FILE}")
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        print("xgettext not available, falling back to basic extraction...")
        return extract_strings_basic()

def extract_strings_basic():
    """Basic string extraction when xgettext is not available."""
    print("Performing basic string extraction...")
    
    patterns = [
        r'_\([\'"](.+?)[\'"]\)',                       
        r'_translate\([\'"](.+?)[\'"]\)',              
        r'self\._translate\([\'"](.+?)[\'"]\)',        
        r'translator\.get\([\'"](.+?)[\'"]\)',        
        r'self\.translator\.get\([\'"](.+?)[\'"]\)',   
    ]
    
    strings = set()
    
    for root, _, files in os.walk(PACKAGE_DIR):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        for pattern in patterns:
                            matches = re.findall(pattern, content)
                            strings.update(matches)
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    
    os.makedirs(os.path.dirname(POT_FILE), exist_ok=True)
    with open(POT_FILE, 'w', encoding='utf-8') as f:
        f.write('# TeddyCloudStarter Translation Template\n')
        f.write('# This file is distributed under the same license as the TeddyCloudStarter package.\n')
        f.write('msgid ""\n')
        f.write('msgstr ""\n')
        f.write('"Project-Id-Version: TeddyCloudStarter 1.0.0\\n"\n')
        f.write('"POT-Creation-Date: 2025-04-22 12:00+0200\\n"\n')
        f.write('"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\\n"\n')
        f.write('"Last-Translator: FULL NAME <EMAIL@ADDRESS>\\n"\n')
        f.write('"Language-Team: LANGUAGE <LL@li.org>\\n"\n')
        f.write('"MIME-Version: 1.0\\n"\n')
        f.write('"Content-Type: text/plain; charset=UTF-8\\n"\n')
        f.write('"Content-Transfer-Encoding: 8bit\\n"\n')
        f.write('\n')
        
        for string in sorted(strings):
            f.write(f'msgid "{string}"\n')
            f.write('msgstr ""\n\n')
    
    print(f"Extracted {len(strings)} strings to {POT_FILE}")
    return True

def update_po_files():
    """Update existing PO files with new strings."""
    print("Updating PO files...")
    
    if not os.path.exists(POT_FILE):
        print("POT file not found. Run extraction first.")
        return False
    
    for lang_dir in glob.glob(str(LOCALES_DIR / "*")):
        if not os.path.isdir(lang_dir):
            continue
        
        lc_messages_dir = os.path.join(lang_dir, "LC_MESSAGES")
        os.makedirs(lc_messages_dir, exist_ok=True)
        
        po_file = os.path.join(lc_messages_dir, "teddycloudstarter.po")
        
        if os.path.exists(po_file):
            print(f"Updating {po_file}...")
            try:
                subprocess.run([
                    "msgmerge", 
                    "--update", 
                    "--backup=none", 
                    po_file, 
                    str(POT_FILE)
                ], check=True)
                print(f"Updated {po_file}")
            except (subprocess.SubprocessError, FileNotFoundError):
                print("msgmerge not available, creating backup and copying POT...")
                backup_file = po_file + ".bak"
                try:
                    with open(po_file, 'r', encoding='utf-8') as src:
                        with open(backup_file, 'w', encoding='utf-8') as dest:
                            dest.write(src.read())
                    
                    with open(backup_file, 'r', encoding='utf-8') as backup:
                        header = ""
                        in_header = True
                        for line in backup:
                            if in_header:
                                header += line
                                if line.strip() == "":
                                    in_header = False
                            else:
                                break
                    
                    with open(POT_FILE, 'r', encoding='utf-8') as pot:
                        pot_content = pot.read()
                        pot_content = pot_content.split('\n\n', 1)[1] if '\n\n' in pot_content else pot_content
                    
                    with open(po_file, 'w', encoding='utf-8') as out:
                        out.write(header)
                        out.write(pot_content)
                    
                    print(f"Updated {po_file} (manual merge)")
                except Exception as e:
                    print(f"Error updating {po_file}: {e}")
        else:
            print(f"Creating new PO file {po_file}...")
            os.makedirs(os.path.dirname(po_file), exist_ok=True)
            try:
                with open(POT_FILE, 'r', encoding='utf-8') as src:
                    with open(po_file, 'w', encoding='utf-8') as dest:
                        dest.write(src.read())
                        
                print(f"Created {po_file}")
            except Exception as e:
                print(f"Error creating {po_file}: {e}")
    
    return True

def create_new_language(lang_code):
    """Create a new language translation file."""
    print(f"Creating translation file for language: {lang_code}")
    
    if not os.path.exists(POT_FILE):
        print("POT file not found. Running extraction first...")
        if not extract_strings_with_xgettext():
            print("Failed to extract strings. Cannot create new language.")
            return False
    
    lang_dir = LOCALES_DIR / lang_code
    lc_messages_dir = lang_dir / "LC_MESSAGES"
    os.makedirs(lc_messages_dir, exist_ok=True)
    
    po_file = lc_messages_dir / "teddycloudstarter.po"
    
    try:
        with open(POT_FILE, 'r', encoding='utf-8') as src:
            content = src.read()
            content = content.replace('Language-Team: LANGUAGE <LL@li.org>\\n"', f'Language-Team: {lang_code}\\n"')
            content = content.replace('Language: \\n"', f'Language: {lang_code}\\n"')
            
            with open(po_file, 'w', encoding='utf-8') as dest:
                dest.write(content)
                
        print(f"Created translation file: {po_file}")
        return True
    except Exception as e:
        print(f"Error creating translation file: {e}")
        return False

def main():
    """Main function."""
    if extract_strings_with_xgettext():
        update_po_files()
        
        try:
            import compile_translations as compile_translations
            print("Compiling updated translations...")
            compile_translations.compile_translations()
        except ImportError:
            print("Could not import compile_translations.py. Please run it manually.")
    
    print("\nDone!")
    print("To add a new language, run: python extract_translations.py create_lang <lang_code>")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "create_lang" and len(sys.argv) > 2:
        create_new_language(sys.argv[2])
    else:
        main()