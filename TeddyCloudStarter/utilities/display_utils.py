#!/usr/bin/env python3
"""
Display utility functions for TeddyCloudStarter.
"""
import threading
import time
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .keyboard_utils import capture_keypress
from .logger import get_logger

logger = get_logger("DisplayUtils")
console = Console()


def display_live_logs(container, service_name, show_timestamp=False):
    """
    Display live logs from a Docker container with interactive controls.

    Controls:
    - Press 'p' to pause/play logs
    - Press 'c' to clear logs
    - Press 'q' to quit log view
    """
    paused = False
    stop_thread = False
    last_lines = []
    max_lines = 100  # Keep track of the last 100 lines

    def log_reader():
        nonlocal last_lines
        try:
            for log in container.logs(
                stream=True, follow=True, timestamps=show_timestamp
            ):
                if stop_thread:
                    break
                if not paused:
                    log_line = log.decode("utf-8").strip()
                    last_lines.append(log_line)
                    # Keep only the last max_lines
                    if len(last_lines) > max_lines:
                        last_lines = last_lines[-max_lines:]
                    print(log_line)
                time.sleep(0.01)  # Small delay to reduce CPU usage
        except Exception as e:
            logger.print_error(f"Error reading logs: {e}")

    # Start log reader thread
    log_thread = threading.Thread(target=log_reader)
    log_thread.daemon = True
    log_thread.start()

    # Show controls
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    controls_text = Text()
    controls_text.append(f"[{now}] ", style="dim")
    controls_text.append("Viewing logs for ", style="blue")
    controls_text.append(f"{service_name}", style="cyan bold")
    controls_text.append(" | Controls: ", style="blue")
    controls_text.append("p", style="yellow bold")
    controls_text.append(" = pause/play | ", style="white")
    controls_text.append("c", style="yellow bold")
    controls_text.append(" = clear | ", style="white")
    controls_text.append("q", style="yellow bold")
    controls_text.append(" = quit", style="white")

    console.print(Panel(controls_text))

    try:
        while True:
            key = capture_keypress()
            if key:
                if key == "q":
                    print("\nExiting log view.")
                    stop_thread = True
                    break
                elif key == "p":
                    paused = not paused
                    status = "⏸️ Paused" if paused else "▶️ Resumed"
                    console.print(f"[yellow]{status}[/yellow] log streaming")
                elif key == "c" and not paused:
                    console.clear()
                    console.print(Panel(controls_text))
                    console.print("[yellow]Logs cleared[/yellow]")
            time.sleep(0.1)  # Small delay to reduce CPU usage
    except KeyboardInterrupt:
        stop_thread = True
        print("\nExiting log view.")

    # Ensure the thread stops
    stop_thread = True
    log_thread.join(timeout=1.0)
