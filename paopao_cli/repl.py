"""
REPL functionality for PaoPao CLI Framework.
"""

import code
import threading
import importlib.util
from pathlib import Path
from typing import Dict, Optional

class REPL(code.InteractiveConsole):
    """Enhanced REPL for testing command scripts with PaoPao integration."""
    
    def __init__(self, local_vars=None, command_manager=None):
        if local_vars is None:
            local_vars = {}
        super().__init__(locals=local_vars)
        
        self.stop_event = threading.Event()
        self.command_manager = command_manager
        self.history = []
        self.max_history = 100
        self._should_exit = False
        
        # Setup default environment after parent initialization
        self.setup_default_environment()
    
    def setup_default_environment(self):
        """Setup default REPL environment with useful imports and variables."""
        # Import common modules with error handling
        modules_to_import = {
            'os': None,
            'sys': None,
            'json': None,
            'subprocess': None,
            'shutil': None,
        }
        
        for name in modules_to_import:
            try:
                modules_to_import[name] = __import__(name)
            except ImportError:
                print(f"Warning: Could not import {name}")
                modules_to_import[name] = None
        
        # Import Path separately
        try:
            from pathlib import Path
            modules_to_import['Path'] = Path
        except ImportError:
            print("Warning: Could not import Path from pathlib")
        
        # Make them available in REPL
        self.locals.update(modules_to_import)
        self.locals.update({
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
            try:
                commands_metadata, command_paths = self.command_manager.get_available_commands()
                if command_name in command_paths:
                    try:
                        spec = importlib.util.spec_from_file_location(command_name, command_paths[command_name])
                        if spec and spec.loader:
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            self.locals[command_name] = module
                            print(f"✅ Loaded command '{command_name}' as variable '{command_name}'")
                            return module
                    except Exception as e:
                        print(f"❌ Error loading command: {e}")
                else:
                    print(f"❌ Command '{command_name}' not found")
            except Exception as e:
                print(f"❌ Error accessing command manager: {e}")
        else:
            print("⚠️ Command manager not available")
        return None
    
    def run_command_safe(self, command_name, args=None):
        """Safely run a command without exiting REPL on error."""
        if args is None:
            args = []
        
        try:
            # Check if it's a loaded module
            if isinstance(command_name, str) and command_name in self.locals:
                module = self.locals[command_name]
            elif hasattr(command_name, 'main'):
                module = command_name
            else:
                print(f"❌ Command '{command_name}' not found or not loaded")
                return False
            
            # Run the command with error handling
            if hasattr(module, 'main') and callable(module.main):
                module.main(args)
                return True
            else:
                print(f"❌ Module has no callable main() function")
                return False
            
        except SystemExit as e:
            # Catch argparse SystemExit but don't exit REPL
            print(f"⚠️ Command exited with code {e.code}")
            return False
        except Exception as e:
            print(f"❌ Error running command: {e}")
            return False
    
    def show_help(self):
        """Show REPL help information."""
        help_text = """
PaoPao REPL Mode Help:

Available built-in variables:
  os, sys, json, subprocess, shutil, Path

Available built-in functions:
  help()      - Show this help
  exit()      - Exit REPL mode
  clear()     - Clear screen
  history()   - Show command history
  load_command(name) - Load a PaoPao command for testing
  run_command(cmd, args) - Safely run a command without exiting REPL

Example usage:
  >>> result = subprocess.run(['ls', '-la'], capture_output=True, text=True)
  >>> print(result.stdout)
  >>> passgen = load_command('passgen')
  >>> run_command(passgen, ['--length', '12'])  # Safe execution
  >>> passgen.main(['--length', '12'])          - Direct execution (may exit)

Use Ctrl-D or type 'exit()' to quit.
"""
        
        print("=" * 50)
        print("🧪 REPL Help")
        print("=" * 50)
        print(help_text)
        print("=" * 50)
    
    def exit_repl(self, *_):
        """Exit the REPL."""
        self._should_exit = True
        raise SystemExit("Exiting REPL")
    
    def clear_screen(self, *_):
        """Clear the console screen."""
        print("\033c", end="")  # ANSI escape code to clear screen
        return "Screen cleared"
    
    def show_history(self, *_):
        """Show command history."""
        if not self.history:
            print("No history yet")
            return
        
        print("📜 Command History:")
        for i, cmd in enumerate(self.history[-10:], 1):
            print(f"{i:2d}. {cmd}")
        
        return f"Showing {len(self.history)} commands in history"
    
    def runsource(self, source, filename="<input>", symbol="single"):
        """Override to capture history and handle multi-line input."""
        if source.strip():  # Only add non-empty commands to history
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
                print("⚠️ Command attempted to exit REPL - caught and prevented")
                return False
            else:
                # Re-raise if it was a user exit
                raise
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def raw_input(self, prompt=""):
        """Custom raw_input that handles exit flag."""
        if self._should_exit:
            raise SystemExit("Exiting REPL")
        return input(prompt)
    
    def run(self, banner=None):
        """Run the enhanced REPL."""
        if banner is None:
            banner = """
🧪 PaoPao REPL Mode (experiment)
Type 'help()' for assistance, 'exit()' to quit.
Loaded commands available through load_command('name')
Use run_command() for safe execution without exiting REPL
"""
        
        print(banner)
        
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
                        print("\n👋 Exiting REPL mode (EOF)...")
                        break
                    except SystemExit:
                        # This handles the case where exit() is called during raw_input
                        print("👋 Exiting REPL mode...")
                        break
                    
                    more = self.push(line)
                    
                except KeyboardInterrupt:
                    print("\nKeyboardInterrupt")
                    self.resetbuffer()
                    more = 0
                except SystemExit as e:
                    if "Exiting REPL" in str(e):
                        print("👋 Exiting REPL mode...")
                        break
                    else:
                        print("⚠️ Command attempted to exit REPL - caught and prevented")
                        self.resetbuffer()
                        more = 0
                        
        except Exception as e:
            print(f"Unexpected error in REPL: {e}")
            import traceback
            print(traceback.format_exc())