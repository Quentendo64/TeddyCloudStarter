#!/usr/bin/env python3
"""
Log viewing utilities for TeddyCloudStarter.
"""
import os
import time
import threading
import queue
import sys
import platform

from rich.console import Console
from rich.live import Live
from rich.text import Text
from rich.layout import Layout
from rich.panel import Panel

# Global console instance for rich output
console = Console()


# Add platform-agnostic getch implementation
def capture_keypress():
    """Cross-platform function to get a single keypress without requiring Enter"""
    if os.name == 'nt':
        import msvcrt
        if msvcrt.kbhit():
            return msvcrt.getch().decode('utf-8', errors='ignore').lower()
        return None
    else:
        # Unix-like systems (Linux, macOS)
        import termios
        import tty
        import select
        
        # Check if we're in WSL (Windows Subsystem for Linux)
        is_wsl = "microsoft-standard" in platform.release().lower() or "microsoft" in platform.release().lower()
        
        # Use a more aggressive approach for WSL
        if is_wsl:
            try:
                # Save terminal settings
                old_settings = termios.tcgetattr(sys.stdin)
                try:
                    # Set terminal to raw mode
                    tty.setraw(sys.stdin.fileno(), termios.TCSANOW)
                    # For WSL, we'll use a blocking read with a very short timeout
                    rlist, _, _ = select.select([sys.stdin], [], [], 0.01)
                    if rlist:
                        ch = sys.stdin.read(1)
                        return ch.lower()
                    else:
                        return None
                finally:
                    # Restore terminal settings
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            except Exception:
                # Fallback method if the above doesn't work
                return None
        else:
            # Standard Unix approach
            # Check if anything is available to read
            if select.select([sys.stdin], [], [], 0)[0]:
                # Save terminal settings
                old_settings = termios.tcgetattr(sys.stdin)
                try:
                    # Set terminal to raw mode
                    tty.setraw(sys.stdin.fileno(), termios.TCSANOW)
                    # Read a single character
                    ch = sys.stdin.read(1)
                    return ch.lower()
                finally:
                    # Restore terminal settings
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            return None


def display_live_logs(docker_manager, service_name=None, project_path=None):
    """
    Show live logs from Docker services with interactive controls.
    
    Args:
        docker_manager: The DockerManager instance
        service_name: Optional specific service to get logs from
        project_path: Optional project path for Docker operations
    """
    # Get translator if available from docker_manager
    translator = getattr(docker_manager, 'translator', None)
    
    def _translate(text):
        """Helper to translate text if translator is available."""
        if translator:
            return translator.get(text)
        return text
    
    # Start logs process
    logs_process = docker_manager.get_logs(service_name, project_path=project_path)
    if not logs_process:
        console.print(f"[bold red]{_translate('Failed to start logs process.')}[/]")
        return
        
    # Create a queue for the logs
    log_queue = queue.Queue(maxsize=1000)  # Limit queue size
    
    # Flag to control log collection
    running = True
    paused = False
    
    # Create a function to collect logs
    def _collect_logs():
        while running:
            if not paused:
                # Windows-compatible approach to read from stdout without blocking
                line = logs_process.stdout.readline()
                if line:
                    try:
                        log_queue.put_nowait(line)
                    except queue.Full:
                        # If queue is full, remove oldest item
                        try:
                            log_queue.get_nowait()
                            log_queue.put_nowait(line)
                        except (queue.Empty, queue.Full):
                            pass
            time.sleep(0.1)  # Small sleep to prevent CPU hogging
        
    # Start log collection in a thread
    collector_thread = threading.Thread(target=_collect_logs)
    collector_thread.daemon = True
    collector_thread.start()
    
    # Create a live display with Rich
    log_buffer = []
    max_buffer_lines = min(console.height - 7, 20)  # Adjust based on terminal size with room for controls
    
    # Set up the layout with pinned controls
    layout = Layout()
    layout.split(
        Layout(name="main", ratio=9),
        Layout(name="footer", size=3)
    )
    
    # Create title and initial status
    title = f"[bold green]{_translate('Live Logs')}[/]"
    if service_name:
        title = f"[bold green]{_translate('Live Logs - Service:')} [cyan]{service_name}[/][/]"
    
    status = _translate("Playing")
    controls = f"[bold yellow]{_translate('Controls:')} [P]{_translate('ause')}/[R]{_translate('esume')} | [C]{_translate('lear')} | [Q]{_translate('uit')}[/]"
    
    try:
        with Live(layout, auto_refresh=True, refresh_per_second=4) as live:
            while True:
                # Check for key press events using our cross-platform capture_keypress function
                key = capture_keypress()
                if key:
                    if key == 'q':
                        break  # Exit log view
                    elif key in ('p', 'r'):
                        paused = not paused
                        status = f"[bold yellow]{_translate('Paused')}[/]" if paused else f"[bold green]{_translate('Playing')}[/]"
                        if paused:
                            log_buffer.append(f"[bold yellow]--- {_translate('Log display paused')} ---[/]")
                        else:
                            log_buffer.append(f"[bold green]--- {_translate('Log display resumed')} ---[/]")
                    elif key == 'c':
                        log_buffer = [f"[bold yellow]--- {_translate('Logs cleared')} ---[/]"]
                
                # Process any new log entries if not paused
                if not paused:
                    try:
                        # Get new logs from queue
                        while not log_queue.empty():
                            line = log_queue.get_nowait()
                            log_buffer.append(line.strip())
                            # Trim buffer if it gets too long
                            if len(log_buffer) > max_buffer_lines:
                                log_buffer.pop(0)
                    except queue.Empty:
                        pass
                
                # Update the layout with latest log entries and controls
                log_text = Text("\n".join(log_buffer))
                # Create footer with status and controls
                footer = f"{_translate('Status')}: {status} | {controls}"
                footer_panel = Panel(footer, border_style="cyan")
                # Update both panels
                layout["main"].update(Panel(log_text, title=title, border_style="blue"))
                layout["footer"].update(footer_panel)
                
                time.sleep(0.25)
            
    except KeyboardInterrupt:
        pass
    finally:
        # Clean up
        running = False
        
        # Wait for the thread to finish
        collector_thread.join(timeout=1.0)
        
        # Terminate the logs process
        try:
            logs_process.terminate()
            logs_process.wait(timeout=2.0)
        except:
            pass
        
        console.print(f"\n[bold green]{_translate('Log view closed.')}[/]")
        
        # Wait for user to press a key before returning
        console.print(f"[bold yellow]{_translate('Press Enter to return to menu...')}[/]")
        input()
