"""
PaoPao CLI Framework REPL with Terminal integration.
"""

import code
import threading
import importlib.util
from pathlib import Path
from typing import Optional, Dict
from ppc_src.terminal import Terminal  # <-- your event-driven Terminal class

class PaoPaoREPL(Terminal):
    """Enhanced REPL with PaoPao integration and Terminal events."""

    def __init__(self, local_vars=None, command_manager=None):
        super().__init__(locals=local_vars or {})
        self.command_manager = command_manager
        self.history = []
        self.max_history = 100
        self._should_exit = False

        # Setup default environment
        self.setup_default_environment()

    def setup_default_environment(self):
        """Add built-in modules, helpers, and REPL commands."""
        builtins = {
            'os': __import__('os'),
            'sys': __import__('sys'),
            'json': __import__('json'),
            'subprocess': __import__('subprocess'),
            'shutil': __import__('shutil'),
            'Path': Path,
            'help': self.show_help,
            'exit': self.exit_repl,
            'quit': self.exit_repl,
            'clear': self.clear_screen,
            'history': self.show_history,
            'load_command': self.load_command_test,
            'run_command': self.run_command_safe
        }
        self.locals.update(builtins)

    # ---------- Command Loading ----------
    def load_command_test(self, command_name: str):
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
                            print(f"✅ Loaded command '{command_name}'")
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

    # ---------- Safe Command Execution ----------
    def run_command_safe(self, command_name, args=None):
        """Run a command safely without exiting REPL."""
        args = args or []
        try:
            module = None
            if isinstance(command_name, str):
                module = self.locals.get(command_name)
            elif hasattr(command_name, "main"):
                module = command_name

            if module and callable(getattr(module, "main", None)):
                module.main(args)
                return True
            print(f"❌ Command '{command_name}' not loaded or has no main()")
            return False

        except SystemExit as e:
            print(f"⚠️ Command exited with code {e.code}")
            return False
        except Exception as e:
            print(f"❌ Error running command: {e}")
            return False

    # ---------- Helpers ----------
    def show_help(self):
        help_text = """
PaoPao REPL Help:

Built-ins:
  os, sys, json, subprocess, shutil, Path
Commands:
  help(), exit(), clear(), history(), load_command(), run_command()

Example:
  >>> run_command('passgen', ['--length', '12'])
"""
        print(help_text)

    def exit_repl(self, *_):
        """Exit the REPL."""
        self._should_exit = True
        raise SystemExit("Exiting REPL")

    def clear_screen(self, *_):
        print("\033c", end="")  # ANSI escape code
        return "Screen cleared"

    def show_history(self, *_):
        if not self.history:
            print("No history yet")
            return
        for i, cmd in enumerate(self.history[-10:], 1):
            print(f"{i:2d}. {cmd}")

    # ---------- Override runsource to capture history ----------
    def runsource(self, source, filename="<input>", symbol="single"):
        if source.strip():
            self.history.append(source)
            if len(self.history) > self.max_history:
                self.history.pop(0)
        return super().runsource(source, filename, symbol)

    # ---------- Override run() ----------
    def run(self, banner=None):
        if banner is None:
            banner = "🧪 PaoPao REPL (type help() for assistance, exit() to quit)"
        print(banner)

        more = 0
        while not self._should_exit:
            try:
                prompt = "... " if more else ">>> "
                try:
                    line = input(prompt)
                except EOFError:
                    print("\n👋 Exiting REPL (EOF)")
                    break

                self._trigger("on_input", line)  # Terminal events
                more = self.push(line)
                self._trigger("on_eval", line, more)

            except KeyboardInterrupt:
                print("\nKeyboardInterrupt")
                self.resetbuffer()
                more = 0
                self._trigger("on_interrupt")
            except SystemExit as e:
                if "Exiting REPL" in str(e):
                    print("👋 Exiting REPL...")
                    self._trigger("on_exit")
                    break
                else:
                    print("⚠️ Command attempted to exit REPL")
                    self.resetbuffer()
                    more = 0

if __name__ == "__main__":
    repl = PaoPaoREPL()
    repl.run()