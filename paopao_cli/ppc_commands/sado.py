import argparse
import subprocess
import sys
import os
import ctypes
import time

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.syntax import Syntax
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

console = Console()

# ─────────────────────────────────────────────────────────────────────────────
# UI Helpers
# ─────────────────────────────────────────────────────────────────────────────

def header():
    title = Text("SADO — Super Administrator Do", style="bold white on green", justify="center")
    console.clear()
    console.rule(title)

def show_panel(message: str, title="Notice", style="cyan"):
    console.print(Panel(message, title=f"[{style}]{title}[/{style}]", border_style=style, box=box.ROUNDED))

def show_rich_warning():
    msg = "[bold black on red] WARNING: You are running as TrustedInstaller. [/bold black on red]\n\n" \
          "Misuse can break your system. Proceed only if you understand the risks."
    show_panel(msg, title="Danger", style="red")

def show_error(title: str, message: str):
    console.print(Panel(message, title=f"[red]{title}[/red]", border_style="red", box=box.ROUNDED))

def show_command_preview(command: list[str]):
    command_str = ' '.join(command)
    syntax = Syntax(command_str, "powershell", theme="monokai", word_wrap=True)
    console.print(Panel(syntax, title="[bold blue]Command Preview[/bold blue]", border_style="blue", box=box.ROUNDED))

# ─────────────────────────────────────────────────────────────────────────────
# Elevation and PowerShell Setup
# ─────────────────────────────────────────────────────────────────────────────

def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def elevate_with_admin():
    script = os.path.abspath(sys.argv[0])
    args = " ".join(f'"{arg}"' for arg in sys.argv[1:])
    command = f"Start-Process -FilePath 'python.exe' -ArgumentList '{script} {args}' -Verb RunAs"

    try:
        result = subprocess.run(
            ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        if result.returncode != 0:
            show_error("Elevation Failed", "User canceled elevation or it was blocked.")
        sys.exit(result.returncode)
    except Exception as e:
        show_error("Elevation Failed", str(e))
        sys.exit(1)

def check_powershell():
    result = subprocess.run(
        ["powershell", "-Command", "Get-Host"],
        capture_output=True, text=True,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    if result.returncode != 0:
        raise RuntimeError("PowerShell execution failed.")

def install_ntobjectmanager():
    result = subprocess.run(
        ["powershell", "-Command", "Get-Module -ListAvailable -Name NtObjectManager"],
        capture_output=True, text=True,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    if "NtObjectManager" not in result.stdout:
        console.print("[yellow bold]Installing NtObjectManager...[/yellow bold]")
        subprocess.run([
            "powershell", "-Command",
            "Install-Module NtObjectManager -Force -Scope CurrentUser -AllowClobber"
        ],
        capture_output=True, text=True,
        creationflags=subprocess.CREATE_NO_WINDOW
        )
    else:
        console.print("[green]NtObjectManager is already installed.[/green]")

# ─────────────────────────────────────────────────────────────────────────────
# Command Execution as TrustedInstaller
# ─────────────────────────────────────────────────────────────────────────────

def run_as_trustedinstaller(command: list[str]):
    base_command = subprocess.list2cmdline(command)

    BACKGROUND_RED = '\033[41m' 
    BLACK = '\033[30m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

    warning = (
        f"{BACKGROUND_RED}{BLACK}{BOLD}"
        "[WARNING] You are running as TrustedInstaller. "
        "Misuse can break your system. Proceed only if you understand the risks."
        f"{RESET}"
    )

    wrapped = f'cmd.exe /c "echo {warning} & {base_command}"'
    escaped = wrapped.replace('"', '`"')

    ps_script = f"""
    Set-ExecutionPolicy Bypass -Scope Process -Force;
    Import-Module NtObjectManager -Force;
    sc.exe start TrustedInstaller;
    $proc = Get-NtProcess -Name TrustedInstaller.exe -ErrorAction SilentlyContinue;
    if (-not $proc) {{ Write-Error 'TrustedInstaller not found'; exit 1; }}
    New-Win32Process "{escaped}" -CreationFlags NewConsole -ParentProcess $proc[0];
    """

    result = subprocess.run(
        ['powershell', '-NoProfile', '-NonInteractive', '-Command', ps_script],
        capture_output=True, text=True,
        creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NO_WINDOW
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Unknown error occurred.")

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main(args):
    parser = argparse.ArgumentParser(
        description="Run any command with TrustedInstaller privileges.",
        epilog="Example:\n  python sado.py powershell -Command \"Stop-Service -Name wuauserv\"",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("command", nargs=argparse.REMAINDER, help="The command to run.")
    parser.add_argument("--NoWarning", action="store_true", help="Disable warning panel.")
    args = parser.parse_args(args)

    header()

    if not args.command:
        show_error("Missing Command", "Please provide a command to run.")
        parser.print_help()
        sys.exit(1)

    if not is_admin():
        show_panel("This action requires administrator privileges.", title="Permission Required", style="yellow")
        if Confirm.ask("[yellow bold]Relaunch as administrator?[/yellow bold]", show_choices=True):
            elevate_with_admin()
        else:
            show_error("Access Denied", "Elevation declined.")
            sys.exit(1)

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task(description="Checking PowerShell...", total=None)
        check_powershell()

        progress.add_task(description="Checking NtObjectManager...", total=None)
        install_ntobjectmanager()

    console.rule("[blue]Preview & Execution[/blue]")
    show_command_preview(args.command)

    if not args.NoWarning:
        show_rich_warning()
        if not Confirm.ask("[yellow bold]Continue?[/yellow bold]", show_choices=True):
            console.print("[red bold]Operation cancelled.[/red bold]")
            time.sleep(1)
            sys.exit(0)

    show_panel("Launching command as TrustedInstaller...", style="blue", title="Running")

    try:
        run_as_trustedinstaller(args.command)
        show_panel("Command launched successfully.", title="Success", style="green")
    except Exception as e:
        show_error("Execution Failed", str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
