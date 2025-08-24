#!/usr/bin/env python3
"""
🥭 SADO — Super Administrator Do
Run any command with TrustedInstaller privileges.
"""

import argparse
import subprocess
import sys
import os
import ctypes
import time
import logging
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.columns import Columns
from rich.tree import Tree
from rich.layout import Layout
from rich.live import Live
from rich.status import Status
from rich import box
from rich.markdown import Markdown

# Initialize Rich console
console = Console()

# ─────────────────────────────────────────────────────────────────────────────
# Configuration & Logging
# ─────────────────────────────────────────────────────────────────────────────
class SADOConfig:
    VERSION = "1.0.0"
    APP_NAME = "SADO"
    FULL_NAME = "Super Administrator Do"
    EMOJI = "🥭"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("sado")

# ─────────────────────────────────────────────────────────────────────────────
# Rich UI Components
# ─────────────────────────────────────────────────────────────────────────────
class SADOUI:
    def __init__(self):
        self.console = console
        
    def clear_screen(self):
        """Clear the terminal screen"""
        self.console.clear()
    
    def show_header(self):
        """Display the application header with branding"""
        self.clear_screen()
        
        # Create title with emoji and styling
        title_text = Text()
        title_text.append(f"{SADOConfig.EMOJI} ", style="bold green")
        title_text.append(f"{SADOConfig.APP_NAME}", style="bold white on green")
        title_text.append(" — ", style="bold green")
        title_text.append(f"{SADOConfig.FULL_NAME}", style="bold white on green")
        title_text.append(f" v{SADOConfig.VERSION}", style="dim white")
        
        self.console.print()
        self.console.print(Align.center(title_text))
        self.console.rule(style="green", characters="─")
        self.console.print()
    
    def show_system_info(self):
        """Display system information table"""
        table = Table(title="System Information", box=box.ROUNDED, border_style="blue")
        table.add_column("Property", style="cyan", width=20)
        table.add_column("Value", style="white")
        
        table.add_row("Platform", os.name.upper())
        table.add_row("Python Version", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        table.add_row("Admin Status", "✅ Administrator" if self.is_admin() else "❌ Standard User")
        table.add_row("Working Directory", str(Path.cwd()))
        
        self.console.print(table)
        self.console.print()
    
    def show_panel(self, message: str, title: str = "Notice", style: str = "cyan", 
                   subtitle: Optional[str] = None) -> None:
        """Display a styled panel with message"""
        panel = Panel(
            message,
            title=f"[{style}]{title}[/{style}]",
            subtitle=subtitle,
            border_style=style,
            box=box.ROUNDED,
            padding=(1, 2)
        )
        self.console.print(panel)
        self.console.print()
    
    def show_warning_panel(self):
        """Display the TrustedInstaller warning"""
        warning_text = Text()
        warning_text.append("⚠️  ", style="bold red")
        warning_text.append("DANGER ZONE", style="bold red")
        warning_text.append(" ⚠️\n\n", style="bold red")
        warning_text.append("You are about to run commands with ", style="white")
        warning_text.append("TrustedInstaller", style="bold yellow")
        warning_text.append(" privileges.\n\n", style="white")
        warning_text.append("This is the highest permission level in Windows and can:\n", style="white")
        warning_text.append("• Modify critical system files\n", style="red")
        warning_text.append("• Break Windows functionality\n", style="red")
        warning_text.append("• Cause permanent system damage\n", style="red")
        warning_text.append("\nOnly proceed if you understand the risks!", style="bold white")
        
        panel = Panel(
            warning_text,
            title="[bold red]⚠️  CRITICAL WARNING  ⚠️[/]",
            border_style="red",
            box=box.DOUBLE,
            padding=(1, 2)
        )
        self.console.print(panel)
    
    def show_command_preview(self, command: List[str]):
        """Display the command that will be executed"""
        command_str = ' '.join(command)
        
        # Create syntax highlighted command
        syntax = Syntax(
            command_str, 
            "powershell", 
            theme="monokai", 
            word_wrap=True,
            line_numbers=False,
            background_color="default"
        )
        
        # Create info table
        info_table = Table(box=None, show_header=False, padding=(0, 1))
        info_table.add_column("Key", style="cyan")
        info_table.add_column("Value", style="white")
        info_table.add_row("Command:", command[0])
        info_table.add_row("Arguments:", ' '.join(command[1:]) if len(command) > 1 else "None")
        info_table.add_row("Privilege Level:", "[bold red]TrustedInstaller[/]")
        
        # Combine in columns
        command_panel = Panel(
            syntax,
            title="[bold blue]Command to Execute[/]",
            border_style="blue",
            box=box.ROUNDED
        )
        
        info_panel = Panel(
            info_table,
            title="[bold cyan]Execution Details[/]",
            border_style="cyan",
            box=box.ROUNDED
        )
        
        self.console.print(Columns([command_panel, info_panel], equal=True))
        self.console.print()
    
    def show_error(self, title: str, message: str, details: Optional[str] = None):
        """Display an error message with optional details"""
        error_text = Text()
        error_text.append("❌ ", style="bold red")
        error_text.append(message, style="white")
        
        if details:
            error_text.append("\n\n")
            error_text.append("Details:\n", style="bold white")
            error_text.append(details, style="dim white")
        
        panel = Panel(
            error_text,
            title=f"[bold red]{title}[/]",
            border_style="red",
            box=box.ROUNDED,
            padding=(1, 2)
        )
        self.console.print(panel)
    
    def show_success(self, message: str):
        """Display a success message"""
        success_text = Text()
        success_text.append("✅ ", style="bold green")
        success_text.append(message, style="white")
        
        panel = Panel(
            success_text,
            title="[bold green]Success[/]",
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 2)
        )
        self.console.print(panel)
    
    def show_progress_task(self, description: str):
        """Show a progress spinner for a task"""
        with Status(f"[cyan]{description}[/cyan]", spinner="dots") as status:
            return status
    
    def confirm_action(self, message: str, default: bool = False) -> bool:
        """Ask for user confirmation with Rich styling"""
        return Confirm.ask(
            f"[bold yellow]{message}[/bold yellow]",
            default=default
        )
    
    def prompt_input(self, message: str, default: Optional[str] = None) -> str:
        """Get user input with Rich styling"""
        return Prompt.ask(
            f"[bold blue]{message}[/bold blue]",
            default=default
        )
    
    def show_help_panel(self):
        """Display help information"""
        help_md = """
# SADO Usage Examples

## Basic Commands
```bash
sado powershell -Command "Stop-Service wuauserv"
sado cmd /c "echo Hello from TrustedInstaller"
sado reg delete "HKLM\\SOFTWARE\\MyKey" /f
```

## Advanced Usage
```bash
# Disable Windows Update (requires restart)
sado powershell -Command "Set-Service wuauserv -StartupType Disabled"

# Modify system files
sado takeown /f "C:\\Windows\\System32\\example.dll"

# Registry operations
sado reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\MyService" /v Start /t REG_DWORD /d 4
```

## Safety Tips
- Always test commands on a virtual machine first
- Create system restore point before making changes
- Keep backups of modified files
- Use the preview feature to verify commands
        """
        
        self.console.print(Markdown(help_md))
    
    @staticmethod
    def is_admin() -> bool:
        """Check if running with administrator privileges"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except Exception:
            return False

# ─────────────────────────────────────────────────────────────────────────────
# Core Functionality
# ─────────────────────────────────────────────────────────────────────────────
class SADOCore:
    def __init__(self):
        self.ui = SADOUI()
    
    def elevate_with_admin(self):
        """Elevate to administrator privileges"""
        script = os.path.abspath(sys.argv[0])
        args = " ".join(f'"{arg}"' for arg in sys.argv[1:])
        command = f"Start-Process -FilePath 'python.exe' -ArgumentList '{script} {args}' -Verb RunAs"
        
        try:
            with self.ui.show_progress_task("Requesting elevation..."):
                result = subprocess.run(
                    ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
                    capture_output=True, text=True,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            
            if result.returncode != 0:
                self.ui.show_error(
                    "Elevation Failed", 
                    "User canceled elevation or it was blocked by system policy."
                )
            sys.exit(result.returncode)
            
        except Exception as e:
            self.ui.show_error("Elevation Failed", str(e))
            sys.exit(1)
    
    def check_powershell(self):
        """Verify PowerShell is available and functional"""
        with self.ui.show_progress_task("Checking PowerShell availability..."):
            result = subprocess.run(
                ["powershell", "-Command", "Get-Host"],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                raise RuntimeError("PowerShell execution failed or is not available.")
    
    def install_ntobjectmanager(self):
        """Install NtObjectManager module if not present"""
        with self.ui.show_progress_task("Checking NtObjectManager module..."):
            result = subprocess.run(
                ["powershell", "-Command", "Get-Module -ListAvailable -Name NtObjectManager"],
                capture_output=True, text=True
            )
        
        if "NtObjectManager" not in result.stdout:
            with self.ui.show_progress_task("Installing NtObjectManager module..."):
                install_result = subprocess.run([
                    "powershell", "-Command",
                    "Install-Module NtObjectManager -Force -Scope CurrentUser -AllowClobber"
                ])
                if install_result.returncode != 0:
                    raise RuntimeError("Failed to install NtObjectManager module.")
            
            self.ui.show_success("NtObjectManager module installed successfully.")
        else:
            logger.info("NtObjectManager module is already available.")
    
    def run_as_trustedinstaller(self, command: List[str]):
        """Execute command with TrustedInstaller privileges"""
        base_command = subprocess.list2cmdline(command)
        ps_script = f"""
        Set-ExecutionPolicy Bypass -Scope Process -Force;
        Import-Module NtObjectManager -Force;
        sc.exe start TrustedInstaller | Out-Null;
        Start-Sleep -Seconds 2;
        $proc = Get-NtProcess -Name TrustedInstaller.exe -ErrorAction SilentlyContinue;
        if (-not $proc) {{ 
            Write-Error 'TrustedInstaller service not found or not running'; 
            exit 1; 
        }}
        Write-Host "Launching command with TrustedInstaller privileges...";
        New-Win32Process "cmd.exe /c {base_command}" -CreationFlags NewConsole -ParentProcess $proc[0];
        Write-Host "Command launched successfully.";
        """
        
        with self.ui.show_progress_task("Executing command as TrustedInstaller..."):
            result = subprocess.run(
                ['powershell', '-NoProfile', '-NonInteractive', '-Command', ps_script],
                capture_output=True, text=True
            )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() or "Unknown error occurred during execution."
            raise RuntimeError(error_msg)
        
        return result.stdout

# ─────────────────────────────────────────────────────────────────────────────
# Main Application
# ─────────────────────────────────────────────────────────────────────────────
def main(argv):
    core = SADOCore()
    ui = core.ui
    
    # Parse arguments
    parser = argparse.ArgumentParser(
        description=f"{SADOConfig.APP_NAME} - {SADOConfig.FULL_NAME}",
        epilog="""
Examples:
  sado powershell -Command "Stop-Service wuauserv"
  sado cmd /c "echo Hello from TrustedInstaller"
  sado --help-extended  # Show detailed help with examples
        """,
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument(
        "command", 
        nargs=argparse.REMAINDER, 
        help="The command to run with TrustedInstaller privileges"
    )
    parser.add_argument(
        "--no-warning", 
        action="store_true", 
        help="Skip the safety warning (not recommended)"
    )
    parser.add_argument(
        "--system-info", 
        action="store_true", 
        help="Display system information and exit"
    )
    parser.add_argument(
        "--help-extended", 
        action="store_true", 
        help="Show extended help with examples"
    )
    
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return
    
    # Show header
    ui.show_header()
    
    # Handle special flags
    if args.help_extended:
        ui.show_help_panel()
        return
    
    if args.system_info:
        ui.show_system_info()
        return
    
    # Validate command
    if not args.command:
        ui.show_error(
            "Missing Command", 
            "No command specified. Please provide a command to execute.",
            "Use --help for usage information or --help-extended for examples."
        )
        return
    
    # Check administrator privileges
    if not ui.is_admin():
        ui.show_panel(
            "Administrator privileges are required to use TrustedInstaller.",
            title="Permission Required",
            style="yellow"
        )
        
        if ui.confirm_action("Request administrator elevation?"):
            core.elevate_with_admin()
        else:
            ui.show_error("Access Denied", "Operation requires administrator privileges.")
            return
    
    # System checks
    try:
        ui.show_panel("Performing system checks...", style="blue")
        core.check_powershell()
        core.install_ntobjectmanager()
        ui.show_success("System checks completed successfully.")
        
    except Exception as e:
        ui.show_error("System Check Failed", str(e))
        return
    
    # Display command preview
    console.rule("[blue]Command Preview & Confirmation[/]")
    ui.show_command_preview(args.command)
    
    # Show warning (unless disabled)
    if not args.no_warning:
        ui.show_warning_panel()
        if not ui.confirm_action("Do you want to proceed with this potentially dangerous operation?"):
            ui.show_panel("Operation cancelled by user.", style="yellow", title="Cancelled")
            time.sleep(1)
            return
    
    # Execute command
    console.rule("[green]Execution[/]")
    try:
        output = core.run_as_trustedinstaller(args.command)
        ui.show_success("Command executed successfully with TrustedInstaller privileges.")
        
        if output.strip():
            ui.show_panel(
                output.strip(),
                title="Command Output",
                style="green"
            )
            
    except Exception as e:
        ui.show_error("Execution Failed", str(e))
        logger.error("Command execution failed", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {e}[/red]")
        sys.exit(1)