#!/usr/bin/env python3
"""
🥭 PaoPao CLI Framework - Refactored Version
A plugin-based CLI system with command management capabilities.
"""

import argparse
import sys
import json
import subprocess
import shutil
import datetime
import importlib.util
import inspect
import os
from pathlib import Path
from typing import Dict, Tuple, Optional

import rich_argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

# ---- Configuration ----
class Config:
    """Configuration constants for the CLI framework."""
    COMMANDS_DIR = Path(__file__).parent / "ppc_commands"
    COMMUNITY_COMMANDS_DIR = Path(__file__).parent / "ppc_commands"
    PROJECT_META_FILE = "ppc.project.json"
    GIT_META_FILE = ".ppc.git"
    
console = Console()

# ---- Core Classes ----
class CommandManager:
    """Handles command discovery, loading, and metadata management."""
    
    def __init__(self):
        self.config = Config()
    
    def get_available_commands(self) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
        Scan for available commands and return their paths and sources.
        
        Returns:
            Tuple of (commands_dict, sources_dict)
        """
        def scan_directory(folder: str) -> Dict[str, str]:
            """Scan a directory for Python command files."""
            if not os.path.isdir(folder):
                return {}
            
            commands = {}
            # Scan for direct .py files
            for fname in os.listdir(folder):
                if fname.endswith(".py") and not fname.startswith("_"):
                    commands[fname[:-3]] = os.path.join(folder, fname)
            
            # Scan for subdirectories with main.py
            for root, dirs, _ in os.walk(folder):
                for directory in dirs:
                    main_py = os.path.join(root, directory, "main.py")
                    if os.path.isfile(main_py):
                        commands[directory] = main_py
            
            return commands
        
        official_commands = scan_directory(str(self.config.COMMANDS_DIR))
        community_commands = scan_directory(str(self.config.COMMUNITY_COMMANDS_DIR))
        
        # Combine commands (community overrides official)
        all_commands = {**community_commands, **official_commands}
        
        # Determine sources
        sources = {
            name: "official" if name in official_commands else "community"
            for name in all_commands
        }
        
        return all_commands, sources
    
    def get_project_metadata(self, folder: Path) -> Dict:
        """Load project metadata from ppc.project.json file."""
        project_file = Path(folder) / self.config.PROJECT_META_FILE
        if project_file.exists():
            try:
                return json.loads(project_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                console.print(f"[yellow]⚠️ Warning: Could not read metadata from {project_file}[/yellow]")
        return {}
    
    def load_and_run_command(self, command_name: str, argv: list):
        """Dynamically load and execute a command module."""
        commands, _ = self.get_available_commands()
        
        if command_name not in commands:
            console.print(f"[red]❌ Unknown command:[/red] {command_name}")
            self.show_help()
            sys.exit(1)
        
        command_path = commands[command_name]
        
        try:
            spec = importlib.util.spec_from_file_location(command_name, command_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if hasattr(module, "main") and callable(module.main):
                module.main(argv)
            else:
                console.print(f"[red]❌ Module '{command_name}' has no callable main() function[/red]")
                sys.exit(1)
                
        except Exception as e:
            console.print(f"[red]❌ Error loading command '{command_name}': {e}[/red]")
            sys.exit(1)
    
    def show_help(self):
        """Display available commands in a formatted table."""
        commands, sources = self.get_available_commands()
        
        if not commands:
            console.print("[bold red]❌ No command modules found.[/bold red]")
            return
        
        table = Table(title="📦 Available Commands", box=box.SIMPLE_HEAVY)
        table.add_column("Command", style="cyan bold", no_wrap=True)
        table.add_column("Version", style="yellow")
        table.add_column("Source", style="magenta")
        table.add_column("Author", style="blue")
        table.add_column("Description", style="green")
        
        for name in sorted(commands):
            source = sources[name]
            src_label = "🛠️ Official" if source == "official" else "🌍 Community"
            
            folder = Path(commands[name]).parent
            meta = self.get_project_metadata(folder)
            
            # Set defaults based on source
            if source == "official":
                version = meta.get("version", "Built-In")
                author = meta.get("author", "PaoPaoDev")
                description = meta.get("description") or "Built-in command."
            else:
                version = meta.get("version", "[italic dim]N/A[/italic dim]")
                author = meta.get("author", "[italic dim]Unknown[/italic dim]")
                description = meta.get("description") or "[italic dim]No description available.[/italic dim]"
            
            table.add_row(name, version, src_label, author, description)
        
        console.print(Panel.fit(table, title="[bold yellow]🥭 PaoPao CLI Framework[/bold yellow]", border_style="bright_blue"))
        
        # Usage instructions
        console.rule("[bold yellow]Usage: ppc <command> [args][/bold yellow]")
        console.print("")
        console.print("[bold yellow]Management Commands:[/bold yellow]")
        console.print("  • [cyan]ppc list[/cyan] - Show installed community commands")
        console.print("  • [cyan]ppc install <repo_url>[/cyan] - Install a community command")
        console.print("  • [cyan]ppc uninstall <name>[/cyan] - Remove a community command")
        console.print("  • [cyan]ppc update <name>[/cyan] - Update a community command")
        console.print("  • [cyan]ppc test[/cyan] - Test a local command")
        console.print("")
        console.print("[bold yellow]Example:[/bold yellow] ppc install https://github.com/user/my-command")

class BuiltinCommands:
    """Built-in command implementations."""
    
    def __init__(self, command_manager: CommandManager):
        self.cm = command_manager
        self.config = Config()
    
    def install(self, argv: list):
        """Install a community command from a git repository."""
        parser = argparse.ArgumentParser(
            prog="ppc install",
            description="Install a community command from a git repository"
        )
        parser.add_argument("repo_url", help="Git repository URL")
        parser.add_argument("-n", "--name", help="Custom name for the command")
        parser.add_argument("--no-shallow", action="store_true", help="Clone full repository history")
        parser.add_argument("-f", "--force", action="store_true", help="Force overwrite existing command")
        
        try:
            args = parser.parse_args(argv)
        except SystemExit:
            return
        
        # Determine folder name
        folder_name = args.name or args.repo_url.rstrip("/").split("/")[-1].removesuffix(".git")
        target_dir = self.config.COMMUNITY_COMMANDS_DIR / folder_name
        
        # Check if already exists
        if target_dir.exists() and not args.force:
            console.print(f"[yellow]⚠️ Command '{folder_name}' already exists. Use --force to overwrite.[/yellow]")
            return
        
        if target_dir.exists():
            console.print(f"[blue]🗑️ Removing existing installation...[/blue]")
            shutil.rmtree(target_dir)
        
        # Clone repository
        cmd = ["git", "clone"]
        if not args.no_shallow:
            cmd.extend(["--depth", "1"])
        cmd.extend([args.repo_url, str(target_dir)])
        
        try:
            console.print(f"[blue]📥 Installing '{folder_name}' from {args.repo_url}...[/blue]")
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Save installation metadata
            meta_data = {
                "repo_url": args.repo_url,
                "folder_name": folder_name,
                "installed_date": datetime.datetime.now().isoformat(),
                "shallow": not args.no_shallow
            }
            
            meta_file = target_dir / self.config.GIT_META_FILE
            meta_file.write_text(json.dumps(meta_data, indent=2), encoding="utf-8")
            
            console.print(f"[green]✅ Successfully installed:[/green] {folder_name}")
            
        except subprocess.CalledProcessError as e:
            console.print(f"[red]❌ Failed to install '{folder_name}': {e}[/red]")
            if target_dir.exists():
                shutil.rmtree(target_dir)
        except Exception as e:
            console.print(f"[red]❌ Unexpected error during installation: {e}[/red]")
    
    def uninstall(self, argv: list):
        """Uninstall a community command."""
        parser = argparse.ArgumentParser(
            prog="ppc uninstall",
            description="Uninstall a community command"
        )
        parser.add_argument("name", help="Name of command to uninstall")
        
        try:
            args = parser.parse_args(argv)
        except SystemExit:
            return
        
        target_dir = self.config.COMMUNITY_COMMANDS_DIR / args.name
        
        if target_dir.exists() and target_dir.is_dir():
            shutil.rmtree(target_dir)
            console.print(f"[green]🗑️ Successfully uninstalled:[/green] {args.name}")
        else:
            console.print(f"[red]❌ Command not found:[/red] {args.name}")
    
    def list_commands(self, argv: list):
        """List all installed community commands."""
        parser = argparse.ArgumentParser(
            prog="ppc list",
            description="List installed community commands"
        )
        parser.parse_args(argv)
        
        table = Table(title="🌍 Installed Community Commands", box=box.SIMPLE_HEAVY)
        table.add_column("Name", style="cyan bold")
        table.add_column("Version", style="yellow")
        table.add_column("Author", style="blue")
        table.add_column("Description", style="green")
        table.add_column("Installed", style="dim")
        
        found_commands = False
        
        if not self.config.COMMUNITY_COMMANDS_DIR.exists():
            console.print("[yellow]No community commands directory found.[/yellow]")
            return
        
        for entry in sorted(self.config.COMMUNITY_COMMANDS_DIR.iterdir()):
            if entry.is_dir() and (entry / "main.py").exists():
                meta = self.cm.get_project_metadata(entry)
                
                # Get installation date
                git_meta_file = entry / self.config.GIT_META_FILE
                install_date = "Unknown"
                if git_meta_file.exists():
                    try:
                        git_meta = json.loads(git_meta_file.read_text(encoding="utf-8"))
                        install_date = git_meta.get("installed_date", "Unknown")
                        if install_date != "Unknown":
                            # Format date
                            dt = datetime.datetime.fromisoformat(install_date)
                            install_date = dt.strftime("%Y-%m-%d")
                    except (json.JSONDecodeError, ValueError):
                        pass
                
                table.add_row(
                    entry.name,
                    meta.get("version", "-"),
                    meta.get("author", "-"),
                    meta.get("description", "-"),
                    install_date
                )
                found_commands = True
        
        if found_commands:
            console.print(table)
        else:
            console.print("[yellow]No community commands installed.[/yellow]")
            console.print("[dim]Use 'ppc install <repo_url>' to install community commands.[/dim]")
    
    def update(self, argv: list):
        """Update a community command."""
        parser = argparse.ArgumentParser(
            prog="ppc update",
            description="Update a community command from its git repository"
        )
        parser.add_argument("name", help="Name of command to update")
        
        try:
            args = parser.parse_args(argv)
        except SystemExit:
            return
        
        target_dir = self.config.COMMUNITY_COMMANDS_DIR / args.name
        
        if not target_dir.exists():
            console.print(f"[red]❌ Command not found:[/red] {args.name}")
            return
        
        meta_file = target_dir / self.config.GIT_META_FILE
        if not meta_file.exists():
            console.print(f"[red]❌ Cannot update '{args.name}': Not installed via git.[/red]")
            return
        
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            repo_url = meta.get("repo_url")
            shallow = meta.get("shallow", False)
            
            if not repo_url:
                console.print(f"[red]❌ No repository URL found for '{args.name}'.[/red]")
                return
            
            console.print(f"[blue]🔄 Updating '{args.name}' from {repo_url}...[/blue]")
            
            # Fetch latest changes
            fetch_cmd = ["git", "-C", str(target_dir), "fetch", "origin"]
            if shallow:
                fetch_cmd.extend(["--depth", "1"])
            
            subprocess.run(fetch_cmd, check=True, capture_output=True)
            
            # Reset to latest
            subprocess.run(
                ["git", "-C", str(target_dir), "reset", "--hard", "origin/HEAD"],
                check=True, capture_output=True
            )
            
            console.print(f"[green]✅ Successfully updated:[/green] {args.name}")
            
        except json.JSONDecodeError:
            console.print(f"[red]❌ Error reading metadata for '{args.name}'.[/red]")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]❌ Git error updating '{args.name}': {e}[/red]")
        except Exception as e:
            console.print(f"[red]❌ Unexpected error updating '{args.name}': {e}[/red]")
    
    def test(self, argv: list):
        """Test a local command script."""
        parser = argparse.ArgumentParser(
            prog="ppc test",
            description="Test a local command script"
        )
        parser.add_argument("--file", default="main.py", help="Script to test (default: main.py)")
        parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments to pass to the script")
        
        try:
            args = parser.parse_args(argv)
        except SystemExit:
            return
        
        script_path = Path.cwd() / args.file
        
        if not script_path.exists():
            console.print(f"[red]❌ File not found:[/red] {args.file}")
            return
        
        try:
            spec = importlib.util.spec_from_file_location("test_module", str(script_path))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if not (hasattr(module, "main") and inspect.isfunction(module.main)):
                console.print(f"[red]❌ '{args.file}' must contain a 'main' function.[/red]")
                return
            
            console.print(f"[blue]🧪 Testing {args.file}...[/blue]")
            module.main(args.args)
            console.print(f"[green]✅ Test completed successfully.[/green]")
            
        except Exception as e:
            console.print(f"[red]❌ Error during test: {e}[/red]")
            sys.exit(1)

# ---- Main CLI Class ----
class PaoPaoCLI:
    """Main CLI application class."""
    
    def __init__(self):
        self.command_manager = CommandManager()
        self.builtin_commands = BuiltinCommands(self.command_manager)
        
        # Map builtin commands
        self.builtin_map = {
            "install": self.builtin_commands.install,
            "uninstall": self.builtin_commands.uninstall,
            "list": self.builtin_commands.list_commands,
            "update": self.builtin_commands.update,
            "test": self.builtin_commands.test,
        }
    
    def run(self):
        """Main entry point for the CLI."""
        parser = argparse.ArgumentParser(
            prog="ppc",
            description="🥭 PaoPao CLI Framework",
            formatter_class=rich_argparse.RichHelpFormatter,
            add_help=False
        )
        parser.add_argument(
            "command", 
            nargs="?", 
            help="Command to run (e.g., install, uninstall, list, or any installed command)"
        )
        parser.add_argument(
            "args", 
            nargs=argparse.REMAINDER, 
            help="Arguments to pass to the command"
        )
        
        args = parser.parse_args()
        
        # Show help if no command provided
        if args.command is None:
            self.command_manager.show_help()
            return
        
        # Handle builtin commands
        if args.command in self.builtin_map:
            self.builtin_map[args.command](args.args)
        else:
            # Handle plugin commands
            self.command_manager.load_and_run_command(args.command, args.args)

# ---- Entry Point ----
def main():
    """Main entry point."""
    try:
        cli = PaoPaoCLI()
        cli.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Operation cancelled by user.[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main()