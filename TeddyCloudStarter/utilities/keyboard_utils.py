#!/usr/bin/env python3
"""
Keyboard utility functions for TeddyCloudStarter.
"""
import os
import platform
import sys

from .logger import get_logger

logger = get_logger("KeyboardUtils")


def capture_keypress():
    """Cross-platform function to get a single keypress without requiring Enter"""
    if os.name == "nt":
        import msvcrt

        if msvcrt.kbhit():
            return msvcrt.getch().decode("utf-8", errors="ignore").lower()
        return None
    else:
        import select
        import termios
        import tty

        is_wsl = (
            "microsoft-standard" in platform.release().lower()
            or "microsoft" in platform.release().lower()
        )

        if is_wsl:
            try:
                old_settings = termios.tcgetattr(sys.stdin)
                try:
                    tty.setraw(sys.stdin.fileno(), termios.TCSANOW)
                    rlist, _, _ = select.select([sys.stdin], [], [], 0.01)
                    if rlist:
                        ch = sys.stdin.read(1)
                        return ch.lower()
                    else:
                        return None
                finally:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            except Exception:
                return None
        else:
            if select.select([sys.stdin], [], [], 0)[0]:
                old_settings = termios.tcgetattr(sys.stdin)
                try:
                    tty.setraw(sys.stdin.fileno(), termios.TCSANOW)
                    ch = sys.stdin.read(1)
                    return ch.lower()
                finally:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            return None
