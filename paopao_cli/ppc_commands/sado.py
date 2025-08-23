import argparse
import subprocess
import sys
import os
import ctypes
import time
import logging
from pathlib import Path
from typing import List, Optional
import shlex

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.syntax import Syntax
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sado.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Configuration and Constants
# ─────────────────────────────────────────────────────────────────────────────

class Config:
    """Configuration settings for SADO."""
    LOG_FILE = "sado.log"
    TRUSTED_INSTALLER_SERVICE = "TrustedInstaller"
    POWERSHELL_TIMEOUT = 30
    MAX_COMMAND_LENGTH = 2000
    
    # Dangerous commands that require extra confirmation
    DANGEROUS_COMMANDS = {
        'rm', 'del', 'rmdir', 'rd', 'format', 'fdisk', 'diskpart',
        'reg delete', 'takeown', 'icacls', 'attrib', 'sfc /scannow'
    }

# ─────────────────────────────────────────────────────────────────────────────
# Custom Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class SADOError(Exception):
    """Base exception for SADO operations."""
    pass

class ElevationError(SADOError):
    """Raised when elevation fails."""
    pass

class PowerShellError(SADOError):
    """Raised when PowerShell operations fail."""
    pass

class TrustedInstallerError(SADOError):
    """Raised when TrustedInstaller operations fail."""
    pass

# ─────────────────────────────────────────────────────────────────────────────
# UI Helpers
# ─────────────────────────────────────────────────────────────────────────────

def header():
    """Display application header."""
    title = Text("SADO — Super Administrator Do", style="bold white on green", justify="center")
    console.clear()
    console.rule(title)

def show_panel(message: str, title: str = "Notice", style: str = "cyan"):
    """Display a styled panel with message."""
    console.print(Panel(message, title=f"[{style}]{title}[/{style}]", border_style=style, box=box.ROUNDED))

def show_rich_warning():
    """Display TrustedInstaller warning."""
    msg = ("[bold red]⚠️  CRITICAL WARNING ⚠️[/bold red]\n\n"
           "[bold]You are about to execute commands as TrustedInstaller.[/bold]\n\n"
           "• This is the highest privilege level in Windows\n"
           "• Commands can bypass ALL security restrictions\n"
           "• Incorrect usage can render your system unbootable\n"
           "• Only proceed if you fully understand the consequences\n\n"
           "[bold yellow]This action is logged and traceable.[/bold yellow]")
    show_panel(msg, title="DANGER ZONE", style="red")

def show_error(title: str, message: str):
    """Display error panel."""
    console.print(Panel(message, title=f"[red]{title}[/red]", border_style="red", box=box.ROUNDED))
    logger.error(f"{title}: {message}")

def show_command_preview(command: List[str]):
    """Display command preview with syntax highlighting."""
    command_str = ' '.join(shlex.quote(arg) for arg in command)
    
    # Truncate very long commands
    if len(command_str) > Config.MAX_COMMAND_LENGTH:
        command_str = command_str[:Config.MAX_COMMAND_LENGTH] + "... [TRUNCATED]"
    
    syntax = Syntax(command_str, "powershell", theme="monokai", word_wrap=True)
    console.print(Panel(syntax, title="[bold blue]Command Preview[/bold blue]", border_style="blue", box=box.ROUNDED))

def check_dangerous_command(command: List[str]) -> bool:
    """Check if command contains dangerous operations."""
    command_str = ' '.join(command).lower()
    return any(dangerous in command_str for dangerous in Config.DANGEROUS_COMMANDS)

# ─────────────────────────────────────────────────────────────────────────────
# System Validation
# ─────────────────────────────────────────────────────────────────────────────

def validate_system():
    """Validate system requirements."""
    # Check Windows version
    if sys.platform != "win32":
        raise SADOError("This tool only works on Windows systems.")
    
    # Check Python version
    if sys.version_info < (3, 8):
        raise SADOError("Python 3.8 or higher is required.")
    
    # Check if running in compatible environment
    if not os.path.exists(os.environ.get('SYSTEMROOT', r'C:\Windows')):
        raise SADOError("Windows system directory not found.")

def is_admin() -> bool:
    """Check if running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception as e:
        logger.error(f"Failed to check admin status: {e}")
        return False

def validate_command(command: List[str]) -> None:
    """Validate command before execution."""
    if not command:
        raise ValueError("Command cannot be empty.")
    
    if len(command[0]) == 0:
        raise ValueError("Command executable cannot be empty.")
    
    # Check for null bytes or other injection attempts
    command_str = ' '.join(command)
    if '\x00' in command_str:
        raise ValueError("Command contains null bytes.")
    
    # Check command length
    if len(command_str) > Config.MAX_COMMAND_LENGTH:
        raise ValueError(f"Command exceeds maximum length of {Config.MAX_COMMAND_LENGTH} characters.")

# ─────────────────────────────────────────────────────────────────────────────
# Elevation and PowerShell Setup
# ─────────────────────────────────────────────────────────────────────────────

def elevate_with_admin():
    """Restart script with administrator privileges."""
    try:
        script = os.path.abspath(sys.argv[0])
        args = " ".join(f'"{arg}"' for arg in sys.argv[1:])
        
        # Use PowerShell to elevate with better error handling
        ps_command = (
            f"try {{ "
            f"Start-Process -FilePath 'python.exe' -ArgumentList '{script} {args}' -Verb RunAs -Wait; "
            f"}} catch {{ "
            f"Write-Error $_.Exception.Message; "
            f"exit 1; "
            f"}}"
        )
        
        result = subprocess.run(
            ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_command],
            capture_output=True,
            text=True,
            timeout=Config.POWERSHELL_TIMEOUT,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() or "User declined elevation or elevation was blocked."
            raise ElevationError(error_msg)
            
        sys.exit(result.returncode)
        
    except subprocess.TimeoutExpired:
        raise ElevationError("Elevation request timed out.")
    except Exception as e:
        raise ElevationError(f"Failed to elevate privileges: {e}")

def check_powershell():
    """Verify PowerShell is available and functional."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "$PSVersionTable.PSVersion.Major"],
            capture_output=True,
            text=True,
            timeout=Config.POWERSHELL_TIMEOUT,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        if result.returncode != 0:
            raise PowerShellError(f"PowerShell check failed: {result.stderr}")
        
        # Check PowerShell version
        try:
            ps_version = int(result.stdout.strip())
            if ps_version < 5:
                logger.warning(f"PowerShell version {ps_version} detected. Version 5+ recommended.")
        except ValueError:
            logger.warning("Could not determine PowerShell version.")
            
    except subprocess.TimeoutExpired:
        raise PowerShellError("PowerShell check timed out.")
    except FileNotFoundError:
        raise PowerShellError("PowerShell not found. Please install Windows PowerShell.")

def install_ntobjectmanager():
    """Install or verify NtObjectManager module."""
    try:
        # Check if module is available
        check_result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", 
             "Get-Module -ListAvailable -Name NtObjectManager | Select-Object -ExpandProperty Name"],
            capture_output=True,
            text=True,
            timeout=Config.POWERSHELL_TIMEOUT,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        if "NtObjectManager" not in check_result.stdout:
            console.print("[yellow]Installing NtObjectManager module...[/yellow]")
            
            install_result = subprocess.run([
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                "try { "
                "Install-Module NtObjectManager -Force -Scope CurrentUser -AllowClobber -AcceptLicense; "
                "Write-Output 'Success'; "
                "} catch { "
                "Write-Error $_.Exception.Message; "
                "exit 1; "
                "}"
            ],
            capture_output=True,
            text=True,
            timeout=60,  # Installation can take longer
            creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if install_result.returncode != 0:
                raise PowerShellError(f"Failed to install NtObjectManager: {install_result.stderr}")
            
            console.print("[green]✓ NtObjectManager installed successfully.[/green]")
        else:
            console.print("[green]✓ NtObjectManager is already available.[/green]")
            
    except subprocess.TimeoutExpired:
        raise PowerShellError("NtObjectManager installation timed out.")

def check_trustedinstaller_service():
    """Verify TrustedInstaller service is available."""
    try:
        result = subprocess.run([
            "powershell", "-NoProfile", "-Command",
            f"Get-Service -Name {Config.TRUSTED_INSTALLER_SERVICE} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status"
        ],
        capture_output=True,
        text=True,
        timeout=Config.POWERSHELL_TIMEOUT,
        creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        if not result.stdout.strip():
            raise TrustedInstallerError("TrustedInstaller service not found.")
        
        logger.info(f"TrustedInstaller service status: {result.stdout.strip()}")
        
    except subprocess.TimeoutExpired:
        raise TrustedInstallerError("TrustedInstaller service check timed out.")

# ─────────────────────────────────────────────────────────────────────────────
# Command Execution as TrustedInstaller
# ─────────────────────────────────────────────────────────────────────────────

def run_as_trustedinstaller(command: List[str]):
    """Execute command with TrustedInstaller privileges."""
    validate_command(command)
    
    # Log the command execution attempt
    logger.info(f"Attempting to run command as TrustedInstaller: {' '.join(command)}")
    
    # Properly escape the command for PowerShell
    base_command = subprocess.list2cmdline(command)
    
    # Create warning message for the spawned console
    warning_msg = (
        "echo [WARNING] Running as TrustedInstaller - System integrity at risk! && "
        "echo Press Ctrl+C to abort, or any key to continue && pause >nul && "
    )
    
    # Construct the full command with warning
    full_command = f'cmd.exe /c "{warning_msg}{base_command}"'
    
    # Escape for PowerShell
    escaped_command = full_command.replace('"', '`"').replace("'", "''")
    
    # PowerShell script to run as TrustedInstaller
    ps_script = f"""
    try {{
        Set-ExecutionPolicy Bypass -Scope Process -Force;
        Import-Module NtObjectManager -Force;
        
        # Start TrustedInstaller service if not running
        $service = Get-Service -Name TrustedInstaller -ErrorAction Stop;
        if ($service.Status -ne 'Running') {{
            Start-Service -Name TrustedInstaller -ErrorAction Stop;
            Start-Sleep -Seconds 2;
        }}
        
        # Get TrustedInstaller process
        $proc = Get-NtProcess -Name TrustedInstaller.exe -ErrorAction Stop;
        if (-not $proc) {{
            throw 'TrustedInstaller process not found after service start';
        }}
        
        # Launch command in new console with TrustedInstaller privileges
        New-Win32Process '{escaped_command}' -CreationFlags NewConsole -ParentProcess $proc[0] -ErrorAction Stop;
        Write-Output 'Command launched successfully';
        
    }} catch {{
        Write-Error "Failed to execute as TrustedInstaller: $($_.Exception.Message)";
        exit 1;
    }}
    """
    
    try:
        result = subprocess.run(
            ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
            capture_output=True,
            text=True,
            timeout=Config.POWERSHELL_TIMEOUT,
            creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NO_WINDOW
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() or "Unknown error occurred during execution."
            logger.error(f"TrustedInstaller execution failed: {error_msg}")
            raise TrustedInstallerError(error_msg)
        
        logger.info("Command launched successfully as TrustedInstaller")
        
    except subprocess.TimeoutExpired:
        raise TrustedInstallerError("Command execution timed out.")

# ─────────────────────────────────────────────────────────────────────────────
# Main Application Logic
# ─────────────────────────────────────────────────────────────────────────────

def setup_argument_parser() -> argparse.ArgumentParser:
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Run any command with TrustedInstaller privileges.",
        epilog="""Examples:
  python sado.py powershell -Command "Stop-Service -Name wuauserv"
  python sado.py cmd /c "takeown /f C:\\Windows\\System32\\test.dll"
  python sado.py --no-warning reg delete "HKLM\\SOFTWARE\\Test" /f
        """,
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument(
        "command", 
        nargs=argparse.REMAINDER, 
        help="The command and arguments to run with TrustedInstaller privileges."
    )
    
    parser.add_argument(
        "--no-warning", 
        action="store_true", 
        help="Skip the warning dialog (use with extreme caution)."
    )
    
    parser.add_argument(
        "--log-level", 
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
        default='INFO',
        help="Set logging level (default: INFO)."
    )
    
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Show what would be executed without actually running the command."
    )
    
    return parser

def main():
    """Main application entry point."""
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    header()
    
    try:
        # Validate system requirements
        validate_system()
        
        # Check if command was provided
        if not args.command:
            show_error("Missing Command", "Please provide a command to run.")
            console.print("\n")
            parser.print_help()
            sys.exit(1)
        
        # Validate command
        validate_command(args.command)
        
        # Check for administrator privileges
        if not is_admin():
            show_panel(
                "Administrator privileges are required to run commands as TrustedInstaller.", 
                title="Permission Required", 
                style="yellow"
            )
            if Confirm.ask("[yellow bold]Restart with administrator privileges?[/yellow bold]"):
                elevate_with_admin()
            else:
                show_error("Access Denied", "Administrator privileges declined.")
                sys.exit(1)
        
        # System checks with progress indicator
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
            progress.add_task(description="Validating PowerShell installation...", total=None)
            check_powershell()
            
            progress.add_task(description="Checking TrustedInstaller service...", total=None)
            check_trustedinstaller_service()
            
            progress.add_task(description="Verifying NtObjectManager module...", total=None)
            install_ntobjectmanager()
        
        console.rule("[blue]Command Review & Execution[/blue]")
        show_command_preview(args.command)
        
        # Check for dangerous commands
        if check_dangerous_command(args.command):
            show_panel(
                "[bold red]⚠️  POTENTIALLY DESTRUCTIVE COMMAND DETECTED ⚠️[/bold red]\n\n"
                "This command may modify or delete system files.\n"
                "Double-check your command before proceeding.",
                title="High Risk Operation",
                style="red"
            )
        
        # Dry run mode
        if args.dry_run:
            show_panel(
                "DRY RUN MODE: The command above would be executed with TrustedInstaller privileges.",
                title="Dry Run",
                style="blue"
            )
            sys.exit(0)
        
        # Warning and confirmation
        if not args.no_warning:
            show_rich_warning()
            if not Confirm.ask("[red bold]Do you understand the risks and want to continue?[/red bold]"):
                console.print("[yellow]Operation cancelled by user.[/yellow]")
                sys.exit(0)
        
        # Final execution confirmation
        if not Confirm.ask("[bold]Execute the command as TrustedInstaller?[/bold]"):
            console.print("[yellow]Execution cancelled.[/yellow]")
            sys.exit(0)
        
        show_panel("Launching command as TrustedInstaller...", title="Executing", style="blue")
        
        # Execute the command
        run_as_trustedinstaller(args.command)
        
        show_panel(
            "Command launched successfully in a new console window.\n"
            "Check the new window for command output and results.",
            title="Success",
            style="green"
        )
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(1)
    except (SADOError, ValueError) as e:
        show_error("Operation Failed", str(e))
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error occurred")
        show_error("Unexpected Error", f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
