#!/usr/bin/env python3
"""
🥭 PaoPao CLI Framework
A plugin-based CLI system with command management capabilities.
Enhanced version with improved security, caching, and features.
"""

# core import
import paopao_cli

# standard libraries
import argparse
import sys
import json
import subprocess
import shutil
import datetime
import importlib.util
import inspect
import os
import hashlib
import time
import threading
import code

# third-party libraries
from pathlib import Path
from typing import Dict, Tuple, Optional, List, Any
from urllib.parse import urlparse
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, TimeoutError

# rich libraries
import rich_argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich import box
from rich.live import Live
from rich.text import Text

# ---- Configuration ----
@dataclass
class Config:
    """Configuration constants for the CLI framework."""
    COMMANDS_DIR: Path = Path(__file__).parent / "ppc_commands"
    COMMUNITY_COMMANDS_DIR: Path = Path(__file__).parent / "ppc_addon"
    CACHE_DIR: Path = Path(__file__).parent / ".ppc_cache"
    PROJECT_META_FILE: str = "ppc.project.json"
    GIT_META_FILE: str = ".ppc.git"
    LOCK_FILE: str = ".ppc.lock"
    CACHE_EXPIRY_HOURS: int = 24
    MAX_INSTALL_TIME_SECONDS: int = 300  # 5 minutes
    ALLOWED_URL_SCHEMES: List[str] = ("https", "git", "ssh")
    
    def __post_init__(self):
        """Create necessary directories."""
        self.COMMANDS_DIR.mkdir(exist_ok=True)
        self.COMMUNITY_COMMANDS_DIR.mkdir(exist_ok=True)
        self.CACHE_DIR.mkdir(exist_ok=True)

@dataclass
class CommandMetadata:
    """Structured command metadata."""
    name: str
    version: str = "Unknown"
    author: str = "Unknown"
    description: str = "No description available"
    source: str = "community"
    repo_url: Optional[str] = None
    installed_date: Optional[str] = None
    last_updated: Optional[str] = None
    dependencies: List[str] = None
    python_version: str = "3.6+"
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []

console = Console()

# ---- REPL mode ----
class REPL(code.InteractiveConsole):
    """Enhanced REPL for testing command scripts with PaoPao integration."""
    
    def __init__(self, local_vars=None, command_manager=None):
        super().__init__(locals=local_vars)
        self.stop_event = threading.Event()
        self.command_manager = command_manager
        self.history = []
        self.max_history = 100
        self._should_exit = False
        
        # Setup default environment
        if local_vars is None:
            self.setup_default_environment()
    
    def setup_default_environment(self):
        """Setup default REPL environment with useful imports and variables."""
        # Import common modules
        import os
        import sys
        import json
        import subprocess
        import shutil
        from pathlib import Path
        
        # Make them available in REPL
        self.locals.update({
            'os': os,
            'sys': sys,
            'json': json,
            'subprocess': subprocess,
            'shutil': shutil,
            'Path': Path,
            'console': console,
            'cm': self.command_manager,
            'help': self.show_help,
            'exit': self.exit_repl,
            'quit': self.exit_repl,
            'clear': self.clear_screen,
            'history': self.show_history,
            'load_command': self.load_command_test,
            'run_command': self.run_command_safe
        })
    
    def load_command_test(self, command_name):
        """Load a command for testing in REPL."""
        if self.command_manager:
            commands_metadata, command_paths = self.command_manager.get_available_commands()
            if command_name in command_paths:
                try:
                    spec = importlib.util.spec_from_file_location(command_name, command_paths[command_name])
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        self.locals[command_name] = module
                        console.print(f"[green]✅ Loaded command '{command_name}' as variable '{command_name}'[/green]")
                        return module
                except Exception as e:
                    console.print(f"[red]❌ Error loading command: {e}[/red]")
        else:
            console.print("[yellow]⚠️ Command manager not available[/yellow]")
        return None
    
    def run_command_safe(self, command_name, args=None):
        """
        Safely run a command without exiting REPL on error.
        
        Args:
            command_name: Name of the command or loaded module
            args: List of arguments to pass to the command
        """
        if args is None:
            args = []
        
        try:
            # Check if it's a loaded module
            if isinstance(command_name, str) and command_name in self.locals:
                module = self.locals[command_name]
            elif hasattr(command_name, 'main'):
                module = command_name
            else:
                console.print(f"[red]❌ Command '{command_name}' not found or not loaded[/red]")
                return False
            
            # Run the command with error handling
            module.main(args)
            return True
            
        except SystemExit as e:
            # Catch argparse SystemExit but don't exit REPL
            console.print(f"[yellow]⚠️ Command exited with code {e.code}[/yellow]")
            return False
        except Exception as e:
            console.print(f"[red]❌ Error running command: {e}[/red]")
            return False
    
    def show_help(self):
        """Show REPL help information."""
        help_text = """
[bold]PaoPao REPL Mode Help:[/bold]

[cyan]Available built-in variables:[/cyan]
  os, sys, json, subprocess, shutil, Path, console, cm

[cyan]Available built-in functions:[/cyan]
  help()      - Show this help
  exit()      - Exit REPL mode
  clear()     - Clear screen
  history()   - Show command history
  load_command(name) - Load a PaoPao command for testing
  run_command(cmd, args) - Safely run a command without exiting REPL

[cyan]Example usage:[/cyan]
  >>> result = subprocess.run(['ls', '-la'], capture_output=True, text=True)
  >>> print(result.stdout)
  >>> passgen = load_command('passgen')
  >>> run_command(passgen, ['--length', '12'])  # Safe execution
  >>> passgen.main(['--length', '12'])          - Direct execution (may exit)

[cyan]Use Ctrl-D or type 'exit()' to quit.[/cyan]
"""
        console.print(Panel.fit(help_text, title="🧪 REPL Help", border_style="blue"))
    
    def exit_repl(self):
        """Exit the REPL."""
        self._should_exit = True
        raise SystemExit("Exiting REPL")
    
    def clear_screen(self):
        """Clear the console screen."""
        console.clear()
        return "Screen cleared"
    
    def show_history(self):
        """Show command history."""
        if not self.history:
            console.print("[dim]No history yet[/dim]")
            return
        
        table = Table(title="📜 Command History", box=box.SIMPLE)
        table.add_column("#", style="dim")
        table.add_column("Command", style="cyan")
        
        for i, cmd in enumerate(self.history[-10:], 1):  # Show last 10 commands
            table.add_row(str(i), cmd)
        
        console.print(table)
        return f"Showing {len(self.history)} commands in history"
    
    def runsource(self, source, filename="<input>", symbol="single"):
        """Override to capture history and handle multi-line input."""
        self.history.append(source)
        if len(self.history) > self.max_history:
            self.history.pop(0)
        
        try:
            result = super().runsource(source, filename, symbol)
            # If user called exit(), we need to propagate the SystemExit
            if self._should_exit:
                raise SystemExit("Exiting REPL")
            return result
        except SystemExit as e:
            # Only show warning if it wasn't a user-initiated exit
            if not self._should_exit:
                console.print("[yellow]⚠️ Command attempted to exit REPL - caught and prevented[/yellow]")
                return False
            else:
                # Re-raise if it was a user exit
                raise
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return False
    
    def raw_input(self, prompt=""):
        """Custom raw_input that handles exit flag."""
        if self._should_exit:
            raise SystemExit("Exiting REPL")
        return super().raw_input(prompt)
    
    def run(self, banner=None):
        """Run the enhanced REPL."""
        if banner is None:
            banner = """
[bold green]🧪 PaoPao REPL Mode (experiment)[/bold green]
[dim]Type 'help()' for assistance, 'exit()' to quit.[/dim]
[dim]Loaded commands available through load_command('name')[/dim]
[dim]Use run_command() for safe execution without exiting REPL[/dim]
"""
        
        console.print(banner)
        
        try:
            # Use the standard interact method but with our custom handling
            more = 0
            while not self._should_exit:
                try:
                    # Use standard Python REPL prompts
                    if more:
                        prompt = "... "  # Secondary prompt for multi-line input
                    else:
                        prompt = ">>> "  # Primary prompt
                    
                    try:
                        line = self.raw_input(prompt)
                    except EOFError:
                        console.print("\n[blue]👋 Exiting REPL mode (EOF)...[/blue]")
                        break
                    except SystemExit:
                        # This handles the case where exit() is called during raw_input
                        console.print("[blue]👋 Exiting REPL mode...[/blue]")
                        break
                    
                    more = self.push(line)
                    
                except KeyboardInterrupt:
                    console.print("\n[yellow]KeyboardInterrupt[/yellow]")
                    self.resetbuffer()
                    more = 0
                except SystemExit as e:
                    if "Exiting REPL" in str(e):
                        console.print("[blue]👋 Exiting REPL mode...[/blue]")
                        break
                    else:
                        console.print("[yellow]⚠️ Command attempted to exit REPL - caught and prevented[/yellow]")
                        self.resetbuffer()
                        more = 0
                        
        except Exception as e:
            console.print(f"[red]Unexpected error in REPL: {e}[/red]")
            import traceback
            console.print(traceback.format_exc())

# ---- Utility Classes ----
class SecurityValidator:
    """Security validation for repository URLs and installations."""
    
    @staticmethod
    def validate_url(url: str, allowed_schemes: List[str]) -> Tuple[bool, str]:
        """Validate repository URL for security."""
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme not in allowed_schemes:
                return False, f"URL scheme '{parsed.scheme}' not allowed. Use: {', '.join(allowed_schemes)}"
            
            # Check for suspicious patterns
            suspicious_patterns = ['localhost', '127.0.0.1', '0.0.0.0', 'file://', '..']
            url_lower = url.lower()
            
            for pattern in suspicious_patterns:
                if pattern in url_lower:
                    return False, f"Suspicious pattern detected: {pattern}"
            
            # Validate hostname for HTTPS
            if parsed.scheme == 'https':
                if not parsed.netloc:
                    return False, "Invalid hostname"
                
                # Common git hosting providers
                trusted_hosts = ['github.com', 'gitlab.com', 'bitbucket.org', 'codeberg.org']
                if not any(host in parsed.netloc.lower() for host in trusted_hosts):
                    console.print(f"[yellow]⚠️ Warning: Unknown git host '{parsed.netloc}'[/yellow]")
            
            return True, "URL is valid"
            
        except Exception as e:
            return False, f"Invalid URL: {e}"
    
    @staticmethod
    def validate_command_file(file_path: Path) -> Tuple[bool, str]:
        """Basic validation of command file security."""
        try:
            if not file_path.exists():
                return False, "File does not exist"
            
            if file_path.stat().st_size > 10 * 1024 * 1024:  # 10MB limit
                return False, "File too large (>10MB)"
            
            # Check for suspicious imports (basic check)
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            suspicious_imports = ['subprocess', 'os.system', 'eval', 'exec', '__import__']
            
            found_suspicious = []
            for imp in suspicious_imports:
                if imp in content:
                    found_suspicious.append(imp)
            
            if found_suspicious:
                console.print(f"[yellow]⚠️ Warning: Found potentially risky imports: {', '.join(found_suspicious)}[/yellow]")
                if not Confirm.ask("Continue installation?", default=False):
                    return False, "Installation cancelled by user"
            
            return True, "File appears safe"
            
        except Exception as e:
            return False, f"Error validating file: {e}"

class CacheManager:
    """Manage command metadata caching."""
    
    def __init__(self, cache_dir: Path, expiry_hours: int = 24):
        self.cache_dir = cache_dir
        self.expiry_seconds = expiry_hours * 3600
        self.cache_file = cache_dir / "commands_cache.json"
    
    def get_cache_key(self, path: str) -> str:
        """Generate cache key from path."""
        return hashlib.md5(path.encode()).hexdigest()
    
    def is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self.cache_file.exists():
            return False
        
        cache_age = time.time() - self.cache_file.stat().st_mtime
        return cache_age < self.expiry_seconds
    
    def load_cache(self) -> Dict[str, Any]:
        """Load cache data."""
        if not self.is_cache_valid():
            return {}
        
        try:
            return json.loads(self.cache_file.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, IOError):
            return {}
    
    def save_cache(self, data: Dict[str, Any]) -> None:
        """Save cache data."""
        try:
            self.cache_file.write_text(json.dumps(data, indent=2), encoding='utf-8')
        except IOError:
            console.print("[yellow]⚠️ Warning: Could not save cache[/yellow]")

class LockManager:
    """Simple file-based locking mechanism."""
    
    def __init__(self, lock_file: Path):
        self.lock_file = lock_file
    
    def __enter__(self):
        if self.lock_file.exists():
            console.print("[yellow]⚠️ Another PPC operation is in progress. Please wait...[/yellow]")
            # Wait for lock to be released (up to 30 seconds)
            for _ in range(30):
                if not self.lock_file.exists():
                    break
                time.sleep(1)
            else:
                console.print("[red]❌ Lock timeout. If no other PPC process is running, delete the lock file.[/red]")
                sys.exit(1)
        
        try:
            self.lock_file.write_text(str(os.getpid()), encoding='utf-8')
        except IOError:
            console.print("[red]❌ Could not create lock file[/red]")
            sys.exit(1)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.lock_file.unlink(missing_ok=True)
        except Exception:
            pass

# ---- Enhanced Core Classes ----
class CommandManager:
    """Enhanced command discovery, loading, and metadata management."""
    
    def __init__(self, config: Config):
        self.config = config
        self.cache_manager = CacheManager(config.CACHE_DIR, config.CACHE_EXPIRY_HOURS)
        self.security_validator = SecurityValidator()
    
    def get_available_commands(self, use_cache: bool = True) -> Tuple[Dict[str, CommandMetadata], Dict[str, str]]:
        """
        Scan for available commands with caching support.
        
        Returns:
            Tuple of (commands_metadata, command_paths)
        """
        cache_data = self.cache_manager.load_cache() if use_cache else {}
        
        def scan_directory(folder: Path, source: str) -> Dict[str, Tuple[CommandMetadata, str]]:
            """Scan a directory for Python command files with metadata."""
            if not folder.exists():
                return {}
            
            commands = {}
            
            # Scan for direct .py files
            for file_path in folder.glob("*.py"):
                if not file_path.name.startswith("_"):
                    name = file_path.stem
                    cache_key = self.cache_manager.get_cache_key(str(file_path))
                    
                    if cache_key in cache_data and file_path.stat().st_mtime <= cache_data[cache_key].get('mtime', 0):
                        # Use cached metadata
                        meta = CommandMetadata(**cache_data[cache_key]['metadata'])
                    else:
                        # Load fresh metadata
                        meta = self.load_command_metadata(file_path.parent, name, source)
                        cache_data[cache_key] = {
                            'metadata': asdict(meta),
                            'mtime': file_path.stat().st_mtime
                        }
                    
                    commands[name] = (meta, str(file_path))
            
            # Scan for subdirectories with main.py
            for dir_path in folder.iterdir():
                if dir_path.is_dir() and (dir_path / "main.py").exists():
                    name = dir_path.name
                    main_py = dir_path / "main.py"
                    cache_key = self.cache_manager.get_cache_key(str(main_py))
                    
                    if cache_key in cache_data and main_py.stat().st_mtime <= cache_data[cache_key].get('mtime', 0):
                        # Use cached metadata
                        meta = CommandMetadata(**cache_data[cache_key]['metadata'])
                    else:
                        # Load fresh metadata
                        meta = self.load_command_metadata(dir_path, name, source)
                        cache_data[cache_key] = {
                            'metadata': asdict(meta),
                            'mtime': main_py.stat().st_mtime
                        }
                    
                    commands[name] = (meta, str(main_py))
            
            return commands
        
        official_commands = scan_directory(self.config.COMMANDS_DIR, "official")
        community_commands = scan_directory(self.config.COMMUNITY_COMMANDS_DIR, "community")
        
        # Community commands override official ones
        all_commands_data = {**official_commands, **community_commands}
        
        # Separate metadata and paths
        commands_metadata = {name: data[0] for name, data in all_commands_data.items()}
        command_paths = {name: data[1] for name, data in all_commands_data.items()}
        
        # Save updated cache
        if use_cache:
            self.cache_manager.save_cache(cache_data)
        
        return commands_metadata, command_paths
    
    def load_command_metadata(self, folder: Path, name: str, source: str) -> CommandMetadata:
        """Load comprehensive metadata for a command."""
        # Load project metadata from JSON
        project_file = folder / self.config.PROJECT_META_FILE
        project_data = {}
        
        if project_file.exists():
            try:
                project_data = json.loads(project_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                pass
        
        # Load git metadata
        git_meta_file = folder / self.config.GIT_META_FILE
        git_data = {}
        
        if git_meta_file.exists():
            try:
                git_data = json.loads(git_meta_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                pass
        
        # Set defaults based on source
        defaults = {
            "official": {"version": "Built-In", "author": "PaoPaoDev", "description": "Built-in command"},
            "community": {"version": "Unknown", "author": "Unknown", "description": "Community command"}
        }
        
        return CommandMetadata(
            name=name,
            version=project_data.get("version", defaults[source]["version"]),
            author=project_data.get("author", defaults[source]["author"]),
            description=project_data.get("description", defaults[source]["description"]),
            source=source,
            repo_url=git_data.get("repo_url"),
            installed_date=git_data.get("installed_date"),
            last_updated=git_data.get("last_updated"),
            dependencies=project_data.get("dependencies", []),
            python_version=project_data.get("python_version", "3.6+")
        )
    
    def load_and_run_command(self, command_name: str, argv: list):
        """Dynamically load and execute a command module with enhanced error handling."""
        commands_metadata, command_paths = self.get_available_commands()
        
        if command_name not in command_paths:
            console.print(f"[red]❌ Unknown command:[/red] {command_name}")
            self.show_help()
            sys.exit(1)
        
        command_path = command_paths[command_name]
        command_meta = commands_metadata[command_name]
        
        # Security validation for community commands
        if command_meta.source == "community":
            is_safe, message = self.security_validator.validate_command_file(Path(command_path))
            if not is_safe:
                console.print(f"[red]❌ Security validation failed: {message}[/red]")
                sys.exit(1)
        
        try:
            spec = importlib.util.spec_from_file_location(command_name, command_path)
            if spec is None or spec.loader is None:
                console.print(f"[red]❌ Could not load command module: {command_name}[/red]")
                sys.exit(1)
            
            module = importlib.util.module_from_spec(spec)
            
            # Execute module with timeout
            def load_module():
                spec.loader.exec_module(module)
            
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(load_module)
                try:
                    future.result(timeout=10)  # 10 second timeout for loading
                except TimeoutError:
                    console.print(f"[red]❌ Timeout loading command '{command_name}'[/red]")
                    sys.exit(1)
            
            if not (hasattr(module, "main") and callable(module.main)):
                console.print(f"[red]❌ Module '{command_name}' has no callable main() function[/red]")
                sys.exit(1)
            
            # Execute the command
            module.main(argv)
            
        except ImportError as e:
            console.print(f"[red]❌ Import error in command '{command_name}': {e}[/red]")
            if command_meta.dependencies:
                console.print(f"[yellow]💡 This command requires: {', '.join(command_meta.dependencies)}[/yellow]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]❌ Error loading command '{command_name}': {e}[/red]")
            sys.exit(1)
    
    def show_help(self):
        """Display available commands with enhanced formatting."""
        commands_metadata, _ = self.get_available_commands()
        
        if not commands_metadata:
            console.print("[bold red]❌ No command modules found.[/bold red]")
            return
        
        # Separate commands by source
        official_commands = {k: v for k, v in commands_metadata.items() if v.source == "official"}
        community_commands = {k: v for k, v in commands_metadata.items() if v.source == "community"}
        
        def create_commands_table(commands: Dict[str, CommandMetadata], title: str, icon: str):
            if not commands:
                return None
            
            table = Table(title=f"{icon} {title}", box=box.SIMPLE_HEAVY)
            table.add_column("Command", style="cyan bold", no_wrap=True)
            table.add_column("Version", style="yellow")
            table.add_column("Author", style="blue")
            table.add_column("Description", style="green")
            
            for name in sorted(commands.keys()):
                meta = commands[name]
                table.add_row(name, meta.version, meta.author, meta.description)
            
            return table
        
        # Show official commands
        official_table = create_commands_table(official_commands, "Official Commands", "🛠️")
        if official_table:
            console.print(official_table)
            console.print()
        
        # Show community commands
        community_table = create_commands_table(community_commands, "Community Commands", "🌍")
        if community_table:
            console.print(community_table)
            console.print()
        
        # Enhanced usage instructions
        console.rule("[bold yellow]Usage: ppc <command> [args][/bold yellow]")
        console.print()
        
        usage_table = Table(show_header=False, box=box.SIMPLE)
        usage_table.add_column("Command", style="cyan")
        usage_table.add_column("Description", style="white")
        
        usage_table.add_row("ppc list", "Show detailed information about installed commands")
        usage_table.add_row("ppc install <repo_url>", "Install a community command from git")
        usage_table.add_row("ppc uninstall <name>", "Remove a community command")
        usage_table.add_row("ppc update <name>", "Update a community command")
        usage_table.add_row("ppc search <term>", "Search for commands")
        usage_table.add_row("ppc info <name>", "Show detailed command information")
        usage_table.add_row("ppc test [--file script.py]", "Test a local command script")
        usage_table.add_row("ppc doctor", "Check system health and dependencies")
        usage_table.add_row("ppc repl", "Enter REPL mode for testing commands")
        
        console.print(Panel.fit(usage_table, title="[bold yellow]📋 Management Commands[/bold yellow]", border_style="bright_blue"))

class BuiltinCommands:
    """Enhanced built-in command implementations."""
    
    def __init__(self, command_manager: CommandManager, config: Config):
        self.cm = command_manager
        self.config = config
        self.security_validator = SecurityValidator()
    
    def install(self, argv: list):
        """Install a community command with enhanced features."""
        parser = argparse.ArgumentParser(
            prog="ppc install",
            description="Install a community command from a git repository"
        )
        parser.add_argument("repo_url", help="Git repository URL")
        parser.add_argument("-n", "--name", help="Custom name for the command")
        parser.add_argument("--no-shallow", action="store_true", help="Clone full repository history")
        parser.add_argument("-f", "--force", action="store_true", help="Force overwrite existing command")
        parser.add_argument("--branch", help="Specific branch to install")
        parser.add_argument("--no-verify", action="store_true", help="Skip security validation")
        
        try:
            args = parser.parse_args(argv)
        except SystemExit:
            return
        
        # Security validation
        if not args.no_verify:
            is_valid, message = self.security_validator.validate_url(args.repo_url, self.config.ALLOWED_URL_SCHEMES)
            if not is_valid:
                console.print(f"[red]❌ {message}[/red]")
                return
        
        # Determine folder name
        folder_name = args.name or args.repo_url.rstrip("/").split("/")[-1].removesuffix(".git")
        target_dir = self.config.COMMUNITY_COMMANDS_DIR / folder_name
        
        # Check if already exists
        if target_dir.exists() and not args.force:
            console.print(f"[yellow]⚠️ Command '{folder_name}' already exists. Use --force to overwrite.[/yellow]")
            if not Confirm.ask("Overwrite existing command?", default=False):
                return
        
        # Use lock to prevent concurrent installations
        lock_file = self.config.CACHE_DIR / f"{folder_name}.install.lock"
        
        with LockManager(lock_file):
            if target_dir.exists():
                console.print(f"[blue]🗑️ Removing existing installation...[/blue]")
                shutil.rmtree(target_dir)
            
            # Build git clone command
            cmd = ["git", "clone"]
            if not args.no_shallow:
                cmd.extend(["--depth", "1"])
            if args.branch:
                cmd.extend(["--branch", args.branch])
            cmd.extend([args.repo_url, str(target_dir)])
            
            try:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task(f"Installing '{folder_name}' from {args.repo_url}...", total=None)
                    
                    # Run with timeout
                    def run_install():
                        return subprocess.run(cmd, check=True, capture_output=True, text=True, 
                                            timeout=self.config.MAX_INSTALL_TIME_SECONDS)
                    
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(run_install)
                        result = future.result(timeout=self.config.MAX_INSTALL_TIME_SECONDS + 10)
                    
                    progress.update(task, completed=True)
                
                # Validate installed command
                main_py = target_dir / "main.py"
                if not main_py.exists():
                    # Look for alternative entry points
                    py_files = list(target_dir.glob("*.py"))
                    if not py_files:
                        console.print(f"[red]❌ No Python files found in repository[/red]")
                        shutil.rmtree(target_dir)
                        return
                    
                    console.print(f"[yellow]⚠️ No main.py found. Available files: {[f.name for f in py_files]}[/yellow]")
                
                # Security validation of installed files
                if not args.no_verify:
                    for py_file in target_dir.rglob("*.py"):
                        is_safe, message = self.security_validator.validate_command_file(py_file)
                        if not is_safe:
                            console.print(f"[red]❌ Security check failed for {py_file.name}: {message}[/red]")
                            shutil.rmtree(target_dir)
                            return
                
                # Save installation metadata
                meta_data = {
                    "repo_url": args.repo_url,
                    "folder_name": folder_name,
                    "installed_date": datetime.datetime.now().isoformat(),
                    "last_updated": datetime.datetime.now().isoformat(),
                    "shallow": not args.no_shallow,
                    "branch": args.branch,
                    "install_args": vars(args)
                }
                
                meta_file = target_dir / self.config.GIT_META_FILE
                meta_file.write_text(json.dumps(meta_data, indent=2), encoding="utf-8")
                
                # Clear cache
                self.cm.cache_manager.cache_file.unlink(missing_ok=True)
                
                console.print(f"[green]✅ Successfully installed:[/green] {folder_name}")
                
                # Show command info
                self.info([folder_name])
                
            except subprocess.TimeoutExpired:
                console.print(f"[red]❌ Installation timeout (>{self.config.MAX_INSTALL_TIME_SECONDS}s)[/red]")
                if target_dir.exists():
                    shutil.rmtree(target_dir)
            except subprocess.CalledProcessError as e:
                console.print(f"[red]❌ Git error: {e.stderr if e.stderr else str(e)}[/red]")
                if target_dir.exists():
                    shutil.rmtree(target_dir)
            except Exception as e:
                console.print(f"[red]❌ Unexpected error during installation: {e}[/red]")
                if target_dir.exists():
                    shutil.rmtree(target_dir)
    
    def info(self, argv: list):
        """Show detailed information about a command."""
        parser = argparse.ArgumentParser(
            prog="ppc info",
            description="Show detailed information about a command"
        )
        parser.add_argument("name", help="Name of command to show info for")
        
        try:
            args = parser.parse_args(argv)
        except SystemExit:
            return
        
        commands_metadata, command_paths = self.cm.get_available_commands()
        
        if args.name not in commands_metadata:
            console.print(f"[red]❌ Command not found:[/red] {args.name}")
            return
        
        meta = commands_metadata[args.name]
        command_path = command_paths[args.name]
        
        # Create info table
        info_table = Table(show_header=False, box=box.SIMPLE)
        info_table.add_column("Property", style="cyan bold")
        info_table.add_column("Value", style="white")
        
        info_table.add_row("Name", meta.name)
        info_table.add_row("Version", meta.version)
        info_table.add_row("Author", meta.author)
        info_table.add_row("Description", meta.description)
        info_table.add_row("Source", f"{'🛠️ Official' if meta.source == 'official' else '🌍 Community'}")
        info_table.add_row("Python Version", meta.python_version)
        info_table.add_row("File Path", str(command_path))
        
        if meta.dependencies:
            info_table.add_row("Dependencies", ", ".join(meta.dependencies))
        
        if meta.repo_url:
            info_table.add_row("Repository", meta.repo_url)
        
        if meta.installed_date:
            try:
                dt = datetime.datetime.fromisoformat(meta.installed_date)
                formatted_date = dt.strftime("%Y-%m-%d %H:%M")
                info_table.add_row("Installed", formatted_date)
            except ValueError:
                info_table.add_row("Installed", meta.installed_date)
        
        if meta.last_updated and meta.last_updated != meta.installed_date:
            try:
                dt = datetime.datetime.fromisoformat(meta.last_updated)
                formatted_date = dt.strftime("%Y-%m-%d %H:%M")
                info_table.add_row("Last Updated", formatted_date)
            except ValueError:
                info_table.add_row("Last Updated", meta.last_updated)
        
        console.print(Panel.fit(info_table, title=f"[bold cyan]📋 Command Info: {args.name}[/bold cyan]", border_style="bright_blue"))
    
    def search(self, argv: list):
        """Search for commands by name or description."""
        parser = argparse.ArgumentParser(
            prog="ppc search",
            description="Search for commands by name or description"
        )
        parser.add_argument("term", help="Search term")
        parser.add_argument("-s", "--source", choices=["official", "community", "all"], default="all", 
                          help="Filter by command source")
        
        try:
            args = parser.parse_args(argv)
        except SystemExit:
            return
        
        commands_metadata, _ = self.cm.get_available_commands()
        
        # Filter commands
        matches = []
        search_term = args.term.lower()
        
        for name, meta in commands_metadata.items():
            if args.source != "all" and meta.source != args.source:
                continue
            
            # Search in name, description, and author
            searchable_text = f"{name} {meta.description} {meta.author}".lower()
            if search_term in searchable_text:
                matches.append((name, meta))
        
        if not matches:
            console.print(f"[yellow]No commands found matching '{args.term}'[/yellow]")
            return
        
        # Display results
        table = Table(title=f"🔍 Search Results for '{args.term}'", box=box.SIMPLE_HEAVY)
        table.add_column("Command", style="cyan bold")
        table.add_column("Version", style="yellow")
        table.add_column("Source", style="magenta")
        table.add_column("Author", style="blue")
        table.add_column("Description", style="green")
        
        for name, meta in sorted(matches):
            source_icon = "🛠️" if meta.source == "official" else "🌍"
            table.add_row(name, meta.version, f"{source_icon} {meta.source.title()}", 
                         meta.author, meta.description)
        
        console.print(table)
    
    def doctor(self, argv: list):
        """System health check and diagnostics."""
        parser = argparse.ArgumentParser(
            prog="ppc doctor",
            description="Check system health and diagnose issues"
        )
        parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed output")
        
        try:
            args = parser.parse_args(argv)
        except SystemExit:
            return
        
        console.print("[bold blue]🏥 PPC System Health Check[/bold blue]\n")
        
        checks = [
            ("Checking directories", self._check_directories),
            ("Validating commands", self._check_commands),
            ("Checking dependencies", self._check_dependencies),
            ("Testing git access", self._check_git),
            ("Cache status", self._check_cache),
        ]
        
        results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            for description, check_func in checks:
                task = progress.add_task(description, total=None)
                try:
                    result = check_func(args.verbose)
                    results.append((description, True, result))
                    progress.update(task, completed=True)
                except Exception as e:
                    results.append((description, False, str(e)))
                    progress.update(task, completed=True)
        
        console.print()
        
        # Display results
        status_table = Table(title="🏥 Health Check Results", box=box.SIMPLE_HEAVY)
        status_table.add_column("Check", style="cyan")
        status_table.add_column("Status", justify="center")
        status_table.add_column("Details", style="dim")
        
        all_passed = True
        for description, passed, details in results:
            if passed:
                status_table.add_row(description, "✅ PASS", details)
            else:
                status_table.add_row(description, "❌ FAIL", details)
                all_passed = False
        
        console.print(status_table)
        
        if all_passed:
            console.print("\n[green]🎉 All checks passed! Your PPC installation is healthy.[/green]")
        else:
            console.print("\n[yellow]⚠️ Some issues were found. Please address them for optimal performance.[/yellow]")
    
    def _check_directories(self, verbose: bool) -> str:
        """Check if all required directories exist and are writable."""
        dirs_to_check = [
            self.config.COMMANDS_DIR,
            self.config.COMMUNITY_COMMANDS_DIR,
            self.config.CACHE_DIR
        ]
        
        issues = []
        for dir_path in dirs_to_check:
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
            
            if not os.access(dir_path, os.W_OK):
                issues.append(f"{dir_path} not writable")
        
        if issues:
            raise Exception("; ".join(issues))
        
        return f"All directories OK ({len(dirs_to_check)} checked)"
    
    def _check_commands(self, verbose: bool) -> str:
        """Validate all installed commands."""
        commands_metadata, command_paths = self.cm.get_available_commands(use_cache=False)
        
        issues = []
        for name, path in command_paths.items():
            try:
                if not Path(path).exists():
                    issues.append(f"{name}: file missing")
                    continue
                
                # Try to load the module
                spec = importlib.util.spec_from_file_location(name, path)
                if spec is None or spec.loader is None:
                    issues.append(f"{name}: cannot create module spec")
                    continue
                
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                if not (hasattr(module, "main") and callable(module.main)):
                    issues.append(f"{name}: no main() function")
                
            except Exception as e:
                issues.append(f"{name}: {str(e)[:50]}...")
        
        if issues:
            if verbose:
                raise Exception("; ".join(issues))
            else:
                raise Exception(f"{len(issues)} commands have issues")
        
        return f"{len(commands_metadata)} commands validated"
    
    def _check_dependencies(self, verbose: bool) -> str:
        """Check if required Python packages are available."""
        required_packages = ['rich', 'rich_argparse']
        missing = []
        
        for package in required_packages:
            try:
                importlib.import_module(package)
            except ImportError:
                missing.append(package)
        
        if missing:
            raise Exception(f"Missing packages: {', '.join(missing)}")
        
        return f"All required packages available"
    
    def _check_git(self, verbose: bool) -> str:
        """Check if git is available and working."""
        try:
            result = subprocess.run(['git', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                raise Exception("git command failed")
            
            version = result.stdout.strip()
            return version if verbose else "Git available"
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            raise Exception("Git not found or not working")
    
    def _check_cache(self, verbose: bool) -> str:
        """Check cache status and health."""
        cache_file = self.cm.cache_manager.cache_file
        
        if not cache_file.exists():
            return "No cache file (will be created on first use)"
        
        try:
            cache_data = self.cm.cache_manager.load_cache()
            is_valid = self.cm.cache_manager.is_cache_valid()
            
            status = "valid" if is_valid else "expired"
            size = len(cache_data)
            
            if verbose:
                age_hours = (time.time() - cache_file.stat().st_mtime) / 3600
                return f"Cache {status}, {size} entries, {age_hours:.1f}h old"
            else:
                return f"Cache {status} ({size} entries)"
            
        except Exception as e:
            raise Exception(f"Cache corrupted: {e}")
    
    def uninstall(self, argv: list):
        """Enhanced uninstall with confirmation and cleanup."""
        parser = argparse.ArgumentParser(
            prog="ppc uninstall",
            description="Uninstall a community command"
        )
        parser.add_argument("name", help="Name of command to uninstall")
        parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt")
        
        try:
            args = parser.parse_args(argv)
        except SystemExit:
            return
        
        target_dir = self.config.COMMUNITY_COMMANDS_DIR / args.name
        
        if not target_dir.exists():
            console.print(f"[red]❌ Command not found:[/red] {args.name}")
            return
        
        # Show command info before uninstalling
        commands_metadata, _ = self.cm.get_available_commands()
        if args.name in commands_metadata:
            meta = commands_metadata[args.name]
            console.print(f"[yellow]About to uninstall:[/yellow]")
            console.print(f"  Name: {meta.name}")
            console.print(f"  Version: {meta.version}")
            console.print(f"  Author: {meta.author}")
            if meta.repo_url:
                console.print(f"  Repository: {meta.repo_url}")
        
        # Confirmation
        if not args.yes and not Confirm.ask(f"Are you sure you want to uninstall '{args.name}'?", default=False):
            console.print("[yellow]Uninstall cancelled.[/yellow]")
            return
        
        try:
            shutil.rmtree(target_dir)
            
            # Clear cache
            self.cm.cache_manager.cache_file.unlink(missing_ok=True)
            
            console.print(f"[green]🗑️ Successfully uninstalled:[/green] {args.name}")
            
        except Exception as e:
            console.print(f"[red]❌ Error during uninstall: {e}[/red]")
    
    def list_commands(self, argv: list):
        """Enhanced list command with filtering and sorting options."""
        parser = argparse.ArgumentParser(
            prog="ppc list",
            description="List installed commands with detailed information"
        )
        parser.add_argument("-s", "--source", choices=["official", "community", "all"], default="all",
                          help="Filter by command source")
        parser.add_argument("--sort", choices=["name", "version", "author", "installed"], default="name",
                          help="Sort commands by field")
        parser.add_argument("--reverse", action="store_true", help="Reverse sort order")
        parser.add_argument("--detailed", action="store_true", help="Show additional details")
        
        try:
            args = parser.parse_args(argv)
        except SystemExit:
            return
        
        commands_metadata, _ = self.cm.get_available_commands()
        
        # Filter commands
        if args.source != "all":
            commands_metadata = {k: v for k, v in commands_metadata.items() if v.source == args.source}
        
        if not commands_metadata:
            source_msg = f" ({args.source})" if args.source != "all" else ""
            console.print(f"[yellow]No commands found{source_msg}.[/yellow]")
            return
        
        # Sort commands
        def sort_key(item):
            name, meta = item
            if args.sort == "name":
                return name.lower()
            elif args.sort == "version":
                return meta.version.lower()
            elif args.sort == "author":
                return meta.author.lower()
            elif args.sort == "installed":
                return meta.installed_date or "0000"
            return name.lower()
        
        sorted_commands = sorted(commands_metadata.items(), key=sort_key, reverse=args.reverse)
        
        # Create table
        table = Table(title="📦 Installed Commands", box=box.SIMPLE_HEAVY)
        table.add_column("Command", style="cyan bold", no_wrap=True)
        table.add_column("Version", style="yellow")
        table.add_column("Source", style="magenta")
        table.add_column("Author", style="blue")
        table.add_column("Description", style="green")
        
        if args.detailed:
            table.add_column("Installed", style="dim")
            table.add_column("Dependencies", style="dim")
        
        for name, meta in sorted_commands:
            source_icon = "🛠️" if meta.source == "official" else "🌍"
            source_label = f"{source_icon} {meta.source.title()}"
            
            row = [name, meta.version, source_label, meta.author, meta.description]
            
            if args.detailed:
                # Format installed date
                install_date = "Built-in"
                if meta.installed_date:
                    try:
                        dt = datetime.datetime.fromisoformat(meta.installed_date)
                        install_date = dt.strftime("%Y-%m-%d")
                    except ValueError:
                        install_date = meta.installed_date
                
                # Format dependencies
                deps = ", ".join(meta.dependencies) if meta.dependencies else "None"
                
                row.extend([install_date, deps])
            
            table.add_row(*row)
        
        console.print(table)
        
        # Summary
        official_count = sum(1 for meta in commands_metadata.values() if meta.source == "official")
        community_count = len(commands_metadata) - official_count
        
        summary = f"Total: {len(commands_metadata)} commands"
        if args.source == "all":
            summary += f" ({official_count} official, {community_count} community)"
        
        console.print(f"\n[dim]{summary}[/dim]")
    
    def update(self, argv: list):
        """Enhanced update command with better error handling."""
        parser = argparse.ArgumentParser(
            prog="ppc update",
            description="Update a community command from its git repository"
        )
        parser.add_argument("name", help="Name of command to update")
        parser.add_argument("--force", action="store_true", help="Force update even if no changes")
        
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
            console.print(f"[dim]Hint: Only commands installed with 'ppc install' can be updated.[/dim]")
            return
        
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            repo_url = meta.get("repo_url")
            shallow = meta.get("shallow", True)
            
            if not repo_url:
                console.print(f"[red]❌ No repository URL found for '{args.name}'.[/red]")
                return
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task(f"Updating '{args.name}' from {repo_url}...", total=None)
                
                # Check if repository has changes
                try:
                    fetch_cmd = ["git", "-C", str(target_dir), "fetch", "origin"]
                    if shallow:
                        fetch_cmd.extend(["--depth", "1"])
                    
                    subprocess.run(fetch_cmd, check=True, capture_output=True, text=True, timeout=60)
                    
                    # Check for updates
                    status_result = subprocess.run(
                        ["git", "-C", str(target_dir), "status", "-uno", "--porcelain"],
                        check=True, capture_output=True, text=True, timeout=10
                    )
                    
                    rev_list_result = subprocess.run(
                        ["git", "-C", str(target_dir), "rev-list", "--count", "HEAD..origin/HEAD"],
                        check=True, capture_output=True, text=True, timeout=10
                    )
                    
                    commits_behind = int(rev_list_result.stdout.strip())
                    
                    if commits_behind == 0 and not args.force:
                        progress.update(task, completed=True)
                        console.print(f"[green]✅ '{args.name}' is already up to date.[/green]")
                        return
                    
                    # Reset to latest
                    subprocess.run(
                        ["git", "-C", str(target_dir), "reset", "--hard", "origin/HEAD"],
                        check=True, capture_output=True, text=True, timeout=30
                    )
                    
                    progress.update(task, completed=True)
                except Exception as e:
                    raise Exception(f"Error during git update: {e}")
                
                # Update metadata
                meta["last_updated"] = datetime.datetime.now().isoformat()
                meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")
                
                # Clear cache
                self.cm.cache_manager.cache_file.unlink(missing_ok=True)
                
                if commits_behind > 0:
                    console.print(f"[green]✅ Successfully updated '{args.name}' ({commits_behind} new commits)[/green]")
                else:
                    console.print(f"[green]✅ Force updated '{args.name}'[/green]")
        
        except json.JSONDecodeError:
            console.print(f"[red]❌ Error reading metadata for '{args.name}'.[/red]")
        except subprocess.TimeoutExpired:
            console.print(f"[red]❌ Update timeout for '{args.name}'.[/red]")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else str(e)
            console.print(f"[red]❌ Git error updating '{args.name}': {error_msg}[/red]")
        except Exception as e:
            console.print(f"[red]❌ Unexpected error updating '{args.name}': {e}[/red]")
    
    def test(self, argv: list):
        """Enhanced test command with better validation."""
        parser = argparse.ArgumentParser(
            prog="ppc test",
            description="Test a local command script with validation"
        )
        parser.add_argument("--file", default="main.py", help="Script to test (default: main.py)")
        parser.add_argument("--validate", action="store_true", help="Run security validation")
        parser.add_argument("--timeout", type=int, default=30, help="Test timeout in seconds")
        parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments to pass to the script")
        
        try:
            args = parser.parse_args(argv)
        except SystemExit:
            return
        
        script_path = Path.cwd() / args.file
        
        if not script_path.exists():
            console.print(f"[red]❌ File not found:[/red] {args.file}")
            return
        
        # Security validation
        if args.validate:
            is_safe, message = self.security_validator.validate_command_file(script_path)
            if not is_safe:
                console.print(f"[red]❌ Security validation failed: {message}[/red]")
                return
            console.print("[green]✅ Security validation passed[/green]")
        
        try:
            spec = importlib.util.spec_from_file_location("test_module", str(script_path))
            if spec is None or spec.loader is None:
                console.print(f"[red]❌ Cannot create module spec for '{args.file}'[/red]")
                return
            
            module = importlib.util.module_from_spec(spec)
            
            # Load module with timeout
            def load_and_check():
                spec.loader.exec_module(module)
                
                if not (hasattr(module, "main") and inspect.isfunction(module.main)):
                    return False, "No main() function found"
                
                # Check main function signature
                sig = inspect.signature(module.main)
                if len(sig.parameters) != 1:
                    return False, "main() function must accept exactly one parameter (argv list)"
                
                return True, "Module loaded successfully"
            
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(load_and_check)
                try:
                    success, msg = future.result(timeout=10)
                    if not success:
                        console.print(f"[red]❌ {msg}[/red]")
                        return
                except TimeoutError:
                    console.print(f"[red]❌ Timeout loading module[/red]")
                    return
            
            console.print(f"[blue]🧪 Testing {args.file} with timeout {args.timeout}s...[/blue]")
            console.print(f"[dim]Arguments: {args.args if args.args else '(none)'}[/dim]")
            console.print()
            
            # Run the test with timeout
            def run_test():
                module.main(args.args)
            
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_test)
                try:
                    future.result(timeout=args.timeout)
                    console.print(f"\n[green]✅ Test completed successfully.[/green]")
                except TimeoutError:
                    console.print(f"\n[red]❌ Test timeout ({args.timeout}s)[/red]")
                    sys.exit(1)
            
        except ImportError as e:
            console.print(f"[red]❌ Import error: {e}[/red]")
            console.print("[dim]Hint: Make sure all required packages are installed[/dim]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]❌ Error during test: {e}[/red]")
            sys.exit(1)

# ---- Enhanced Main CLI Class ----
class PaoPaoCLI:
    """Enhanced main CLI application class."""
    
    def __init__(self):
        self.config = Config()
        self.command_manager = CommandManager(self.config)
        self.builtin_commands = BuiltinCommands(self.command_manager, self.config)
        
        # Map builtin commands
        self.builtin_map = {
            "install": self.builtin_commands.install,
            "uninstall": self.builtin_commands.uninstall,
            "list": self.builtin_commands.list_commands,
            "update": self.builtin_commands.update,
            "test": self.builtin_commands.test,
            "info": self.builtin_commands.info,
            "search": self.builtin_commands.search,
            "doctor": self.builtin_commands.doctor,
            "repl": self.enter_repl_mode,  # Add REPL command
        }
    
    def enter_repl_mode(self, argv: list):
        """Enter REPL mode with optional command loading."""
        parser = argparse.ArgumentParser(
            prog="ppc repl",
            description="Enter interactive REPL mode for testing and development"
        )
        parser.add_argument("-c", "--command", help="Pre-load a command into REPL")
        parser.add_argument("-e", "--exec", help="Execute a command and stay in REPL")
        parser.add_argument("--no-banner", action="store_true", help="Don't show banner")
        
        try:
            args = parser.parse_args(argv)
        except SystemExit:
            return
        
        # Create REPL instance
        repl = REPL(command_manager=self.command_manager)
        
        # Pre-load command if specified
        if args.command:
            repl.load_command_test(args.command)
        
        # Execute command if specified
        if args.exec:
            console.print(f"[dim]Executing: {args.exec}[/dim]")
            try:
                # Use runsource to execute the command
                repl.runsource(args.exec)
            except Exception as e:
                console.print(f"[red]Error executing command: {e}[/red]")
        
        # Run REPL
        banner = None if args.no_banner else None  # Let REPL class handle default banner
        repl.run(banner)
    
    def run(self):
        """Enhanced main entry point for the CLI."""
        parser = argparse.ArgumentParser(
            prog="ppc",
            description="🥭 PaoPao CLI Framework - Enhanced plugin-based command system",
            formatter_class=rich_argparse.RichHelpFormatter,
            add_help=False
        )
        parser.add_argument(
            "command", 
            nargs="?", 
            help="Command to run (use 'ppc' without arguments to see available commands)"
        )
        parser.add_argument(
            "args", 
            nargs=argparse.REMAINDER, 
            help="Arguments to pass to the command"
        )
        parser.add_argument(
            "--version", 
            action="version", 
            version=f"PaoPao CLI Framework ${paopao_cli.ppc_core.get_version()}"
        )
        parser.add_argument(
            "--repl",
            action="store_true",
            help="Enter REPL mode for interactive testing"
        )
        
        args = parser.parse_args()
        
        # Handle --repl flag
        if args.repl:
            self.enter_repl_mode([])
            return
        
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

def main():
    """Main entry point with enhanced error handling."""
    try:
        cli = PaoPaoCLI()
        cli.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Operation cancelled by user.[/yellow]")
        sys.exit(130)
    except PermissionError as e:
        console.print(f"[red]❌ Permission denied: {e}[/red]")
        console.print("[dim]Try running with appropriate permissions or check file ownership.[/dim]")
        sys.exit(1)
    except FileNotFoundError as e:
        console.print(f"[red]❌ File not found: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        if "--debug" in sys.argv:
            import traceback
            console.print("[dim]Debug traceback:[/dim]")
            console.print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
