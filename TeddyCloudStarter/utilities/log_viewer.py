#!/usr/bin/env python3
"""
Log viewing utilities for TeddyCloudStarter.
"""
import os
import platform
import queue
import sys
import threading
import time

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

console = Console()


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


def display_live_logs(docker_manager, service_name=None, project_path=None):
    """
    Show live logs from Docker services with interactive controls.

    Args:
        docker_manager: The DockerManager instance
        service_name: Optional specific service to get logs from
        project_path: Optional project path for Docker operations
    """
    translator = getattr(docker_manager, "translator", None)

    def _translate(text):
        """Helper to translate text if translator is available."""
        if translator:
            return translator.get(text)
        return text

    logs_process = docker_manager.get_logs(service_name,lines=30,project_path=project_path)
    if not logs_process:
        console.print(f"[bold red]{_translate('Failed to start logs process.')}[/]")
        return

    log_queue = queue.Queue(maxsize=1000)

    running = True
    paused = False

    def _collect_logs():
        while running:
            if not paused:
                line = logs_process.stdout.readline()
                if line:
                    try:
                        log_queue.put_nowait(line)
                    except queue.Full:
                        try:
                            log_queue.get_nowait()
                            log_queue.put_nowait(line)
                        except (queue.Empty, queue.Full):
                            pass
            time.sleep(0.1)

    collector_thread = threading.Thread(target=_collect_logs)
    collector_thread.daemon = True
    collector_thread.start()

    log_buffer = []
    max_buffer_lines = min(console.height - 7, 20)

    layout = Layout()
    layout.split(Layout(name="main", ratio=9), Layout(name="footer", size=3))

    title = f"[bold green]{_translate('Live Logs')}[/]"
    if service_name:
        title = f"[bold green]{_translate('Live Logs - Service:')} [cyan]{service_name}[/][/]"

    status = _translate("Playing")
    controls = f"[bold yellow]{_translate('Controls:')} [P]{_translate('ause')}/[R]{_translate('esume')} | [C]{_translate('lear')} | [Q]{_translate('uit')}[/]"

    try:
        with Live(layout, auto_refresh=True, refresh_per_second=4) as live:
            while True:
                key = capture_keypress()
                if key:
                    if key == "q":
                        break
                    elif key in ("p", "r"):
                        paused = not paused
                        status = (
                            f"[bold yellow]{_translate('Paused')}[/]"
                            if paused
                            else f"[bold green]{_translate('Playing')}[/]"
                        )
                        if paused:
                            log_buffer.append(
                                f"[bold yellow]--- {_translate('Log display paused')} ---[/]"
                            )
                        else:
                            log_buffer.append(
                                f"[bold green]--- {_translate('Log display resumed')} ---[/]"
                            )
                    elif key == "c":
                        log_buffer = [
                            f"[bold yellow]--- {_translate('Logs cleared')} ---[/]"
                        ]

                if not paused:
                    try:
                        while not log_queue.empty():
                            line = log_queue.get_nowait()
                            log_buffer.append(line.strip())
                            if len(log_buffer) > max_buffer_lines:
                                log_buffer.pop(0)
                    except queue.Empty:
                        pass

                log_text = Text("\n".join(log_buffer))
                footer = f"{_translate('Status')}: {status} | {controls}"
                footer_panel = Panel(footer, border_style="cyan")
                layout["main"].update(Panel(log_text, title=title, border_style="blue"))
                layout["footer"].update(footer_panel)

                time.sleep(0.25)

    except KeyboardInterrupt:
        pass
    finally:
        running = False

        collector_thread.join(timeout=1.0)

        try:
            logs_process.terminate()
            logs_process.wait(timeout=2.0)
        except:
            pass

        console.print(f"\n[bold green]{_translate('Log view closed.')}[/]")

        console.print(
            f"[bold yellow]{_translate('Press Enter to return to menu...')}[/]"
        )
        input()
