#!/usr/bin/env python3
"""
Enhanced Python implementation of the Unix 'yes' command
Prints a string repeatedly with advanced features and robust error handling.
"""

import argparse
import sys
import signal
import time
import multiprocessing
import os
import threading
import queue
import random
from typing import Optional, List, Union, TextIO
from pathlib import Path
import contextlib

# ─────────────────────────────────────────────────────────────────────────────
# Safe Output and Error Handling
# ─────────────────────────────────────────────────────────────────────────────

class SafeOutput:
    def __init__(self, output_file: Optional[TextIO] = None, buffer_size: int = 65536):
        self.output_file = output_file or sys.stdout
        self.closed = False
        self.buffer = []
        self.buffer_size = buffer_size
        self.bytes_written = 0
        self.lines_written = 0

    def write(self, text: str) -> bool:
        if self.closed:
            return False
        try:
            self.buffer.append(text)
            if sum(len(x) for x in self.buffer) >= self.buffer_size:
                self._flush_buffer()
            return True
        except (BrokenPipeError, OSError, ValueError):
            self.closed = True
            return False

    def _flush_buffer(self) -> bool:
        if not self.buffer or self.closed:
            return True
        try:
            content = ''.join(self.buffer)
            self.output_file.write(content)
            self.output_file.flush()
            self.bytes_written += len(content)
            self.lines_written += content.count('\n')
            self.buffer.clear()
            return True
        except (BrokenPipeError, OSError, ValueError):
            self.closed = True
            return False

# Optimized yes_worker for infinite output
def yes_worker(worker_id: int, text: str, count: Union[int, float], delay: float, 
               quiet: bool, output_file: Optional[str] = None, mode: str = "normal",
               stats_queue: Optional[queue.Queue] = None) -> None:
    stats = WorkerStats()
    try:
        output = SafeOutput(open(output_file, 'w') if output_file else None)
        generator = TextGenerator(text, mode)

        i = 0
        infinite = count == float("inf")
        while infinite or i < count:
            if not quiet:
                generated_text = generator.generate() + "\n"
                if not output.write(generated_text):
                    break
                stats.lines_output += 1
                stats.bytes_output += len(generated_text)

            i += 1
            if delay > 0:
                time.sleep(delay)

        output._flush_buffer()
        output.close()
        stats.finish()
    except KeyboardInterrupt:
        stats.finish(interrupted=True)
    finally:
        if stats_queue:
            stats_queue.put(('stats', worker_id, stats))


# ─────────────────────────────────────────────────────────────────────────────
# System Detection and Environment
# ─────────────────────────────────────────────────────────────────────────────

class SystemInfo:
    """Detect system environment and capabilities."""
    
    @staticmethod
    def is_powershell() -> bool:
        """Detect if running inside PowerShell."""
        return (
            'pwsh' in os.environ.get('SHELL', '').lower()
            or 'powershell' in os.environ.get('PROMPT', '').lower()
            or 'PSModulePath' in os.environ
            or 'POWERSHELL_DISTRIBUTION_CHANNEL' in os.environ
        )
    
    @staticmethod
    def is_windows() -> bool:
        """Check if running on Windows."""
        return os.name == 'nt' or sys.platform.startswith('win')
    
    @staticmethod
    def supports_colors() -> bool:
        """Check if terminal supports colors."""
        return (
            hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
            and os.environ.get('TERM') != 'dumb'
            and not os.environ.get('NO_COLOR')
        )
    
    @staticmethod
    def get_terminal_size() -> tuple:
        """Get terminal size (width, height)."""
        try:
            return os.get_terminal_size()
        except (OSError, ValueError):
            return (80, 24)  # Default fallback
    
    @staticmethod
    def setup_signal_handlers() -> None:
        """Setup appropriate signal handlers for the platform."""
        # Handle SIGPIPE gracefully on Unix systems
        if hasattr(signal, "SIGPIPE"):
            signal.signal(signal.SIGPIPE, signal.SIG_DFL)
        
        # Handle SIGINT (Ctrl+C) gracefully
        def sigint_handler(sig, frame):
            sys.exit(0)
        signal.signal(signal.SIGINT, sigint_handler)

# ─────────────────────────────────────────────────────────────────────────────
# Text Processing and Generation
# ─────────────────────────────────────────────────────────────────────────────

class TextGenerator:
    """Generate various types of text output."""
    
    def __init__(self, text: str, mode: str = "normal"):
        self.base_text = text
        self.mode = mode
        self.counter = 0
    
    def generate(self) -> str:
        """Generate the next text based on the mode."""
        self.counter += 1
        
        if self.mode == "normal":
            return self.base_text
        elif self.mode == "numbered":
            return f"{self.counter:06d}: {self.base_text}"
        elif self.mode == "timestamped":
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            return f"[{timestamp}] {self.base_text}"
        elif self.mode == "random":
            variations = [
                self.base_text,
                self.base_text.upper(),
                self.base_text.lower(),
                self.base_text.capitalize(),
                self.base_text[::-1]  # reversed
            ]
            return random.choice(variations)
        elif self.mode == "progressive":
            # Add more characters each time
            length = min(len(self.base_text), self.counter)
            return self.base_text[:length]
        else:
            return self.base_text

def parse_escape_sequences(text: str) -> str:
    """Parse common escape sequences in text."""
    replacements = {
        '\\n': '\n',
        '\\t': '\t',
        '\\r': '\r',
        '\\\\': '\\',
        '\\0': '\0',
    }
    
    for escape, replacement in replacements.items():
        text = text.replace(escape, replacement)
    
    return text

# ─────────────────────────────────────────────────────────────────────────────
# Worker Functions and Process Management
# ─────────────────────────────────────────────────────────────────────────────

class WorkerStats:
    """Statistics for a worker process/thread."""
    def __init__(self):
        self.lines_output = 0
        self.bytes_output = 0
        self.start_time = time.perf_counter()
        self.end_time = None
        self.interrupted = False
    
    def finish(self, interrupted: bool = False):
        """Mark the worker as finished."""
        self.end_time = time.perf_counter()
        self.interrupted = interrupted
    
    def duration(self) -> float:
        """Get the duration of the worker."""
        end = self.end_time or time.perf_counter()
        return end - self.start_time
    
    def rate(self) -> float:
        """Get lines per second rate."""
        duration = self.duration()
        return self.lines_output / duration if duration > 0 else 0

def yes_worker(worker_id: int, text: str, count: Union[int, float], delay: float, 
               quiet: bool, output_file: Optional[str] = None, mode: str = "normal",
               stats_queue: Optional[queue.Queue] = None) -> None:
    """Worker function that generates repeated text output."""
    
    stats = WorkerStats()
    
    try:
        # Setup output
        if output_file:
            output = SafeOutput(open(output_file, 'w'))
        else:
            output = SafeOutput()
        
        # Setup text generator
        generator = TextGenerator(text, mode)
        
        # Main output loop
        i = 0
        while i < count:
            if not quiet:
                generated_text = generator.generate() + "\n"
                if not output.write(generated_text):
                    break  # Output closed/broken
                
                stats.lines_output += 1
                stats.bytes_output += len(generated_text)
            
            i += 1
            
            # Rate limiting
            if delay > 0:
                time.sleep(delay)
            
            # Yield control periodically for better responsiveness
            if i % 1000 == 0:
                time.sleep(0.001)
        
        output.close()
        stats.finish()
        
    except KeyboardInterrupt:
        stats.finish(interrupted=True)
    except Exception as e:
        if stats_queue:
            stats_queue.put(('error', worker_id, str(e)))
        stats.finish(interrupted=True)
    finally:
        if stats_queue:
            stats_queue.put(('stats', worker_id, stats))

def threaded_yes_worker(worker_id: int, text: str, count: Union[int, float], 
                       delay: float, quiet: bool, mode: str,
                       stats_queue: queue.Queue, stop_event: threading.Event) -> None:
    """Thread-based worker for better resource usage."""
    
    stats = WorkerStats()
    output = SafeOutput()
    generator = TextGenerator(text, mode)
    
    try:
        i = 0
        while i < count and not stop_event.is_set():
            if not quiet:
                generated_text = generator.generate() + "\n"
                if not output.write(generated_text):
                    break
                
                stats.lines_output += 1
                stats.bytes_output += len(generated_text)
            
            i += 1
            
            if delay > 0:
                time.sleep(delay)
            
            # Check for stop signal more frequently
            if i % 100 == 0 and stop_event.is_set():
                break
        
        stats.finish()
        
    except KeyboardInterrupt:
        stats.finish(interrupted=True)
    finally:
        stats_queue.put(('stats', worker_id, stats))

# ─────────────────────────────────────────────────────────────────────────────
# Statistics and Monitoring
# ─────────────────────────────────────────────────────────────────────────────

def print_statistics(worker_stats: List[WorkerStats], total_time: float, 
                    show_colors: bool = False) -> None:
    """Print comprehensive statistics about the yes command execution."""
    
    if not worker_stats:
        return
    
    # Calculate totals
    total_lines = sum(s.lines_output for s in worker_stats)
    total_bytes = sum(s.bytes_output for s in worker_stats)
    interrupted_workers = sum(1 for s in worker_stats if s.interrupted)
    
    # Color codes
    if show_colors:
        GREEN = '\033[32m'
        YELLOW = '\033[33m'
        RED = '\033[31m'
        BLUE = '\033[34m'
        RESET = '\033[0m'
    else:
        GREEN = YELLOW = RED = BLUE = RESET = ''
    
    # Print statistics
    print(f"\n{BLUE}=== Yes Command Statistics ==={RESET}", file=sys.stderr)
    print(f"{GREEN}Total Lines Output:{RESET} {total_lines:,}", file=sys.stderr)
    print(f"{GREEN}Total Bytes Output:{RESET} {format_bytes(total_bytes)}", file=sys.stderr)
    print(f"{GREEN}Total Time:{RESET} {total_time:.3f} seconds", file=sys.stderr)
    
    if total_time > 0:
        lines_per_sec = total_lines / total_time
        bytes_per_sec = total_bytes / total_time
        print(f"{GREEN}Average Rate:{RESET} {lines_per_sec:,.0f} lines/sec, {format_bytes(bytes_per_sec)}/sec", file=sys.stderr)
    
    print(f"{GREEN}Workers:{RESET} {len(worker_stats)} total", file=sys.stderr)
    
    if interrupted_workers > 0:
        print(f"{YELLOW}Interrupted Workers:{RESET} {interrupted_workers}", file=sys.stderr)
    
    # Per-worker statistics if multiple workers
    if len(worker_stats) > 1:
        print(f"\n{BLUE}Per-Worker Statistics:{RESET}", file=sys.stderr)
        for i, stats in enumerate(worker_stats):
            status = f"{RED}(interrupted){RESET}" if stats.interrupted else f"{GREEN}(completed){RESET}"
            print(f"  Worker {i+1}: {stats.lines_output:,} lines, {stats.rate():,.0f} lines/sec {status}", file=sys.stderr)

def format_bytes(bytes_count: Union[int, float]) -> str:
    """Format bytes in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f} PB"

# ─────────────────────────────────────────────────────────────────────────────
# Main Application
# ─────────────────────────────────────────────────────────────────────────────

def setup_argument_parser() -> argparse.ArgumentParser:
    """Set up command line argument parser with comprehensive options."""
    
    parser = argparse.ArgumentParser(
        prog="enhanced_yes",
        description="Enhanced Python implementation of the Unix 'yes' command.",
        epilog="""Examples:
  %(prog)s                          # Print 'y' repeatedly
  %(prog)s hello                    # Print 'hello' repeatedly
  %(prog)s -c 100 "test"            # Print 'test' 100 times
  %(prog)s --delay 0.1 --mode timestamped  # Print with timestamps and delay
  %(prog)s --workers 4 --count 1000  # Use 4 workers for faster output
  %(prog)s --output results.txt "data"  # Output to file
        """,
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # Basic options
    parser.add_argument(
        "text", 
        nargs="?", 
        default="y",
        help="The string to print repeatedly (default: 'y')"
    )
    
    # Output control
    parser.add_argument(
        "-c", "--count", 
        type=int,
        help="Print only this many times per worker (default: unlimited)"
    )
    
    parser.add_argument(
        "-d", "--delay", 
        type=float, 
        default=0,
        help="Delay between prints in seconds (default: 0)"
    )
    
    parser.add_argument(
        "-o", "--output", 
        type=str,
        help="Output to file instead of stdout"
    )
    
    # Text processing
    parser.add_argument(
        "--mode", 
        choices=["normal", "numbered", "timestamped", "random", "progressive"],
        default="normal",
        help="Text generation mode (default: normal)"
    )
    
    parser.add_argument(
        "--parse-escapes", 
        action="store_true",
        help="Parse escape sequences like \\n, \\t in text"
    )
    
    # Performance and parallelization
    parser.add_argument(
        "--workers", 
        type=int, 
        default=1,
        help="Number of parallel workers (default: 1)"
    )
    
    parser.add_argument(
        "--use-threads", 
        action="store_true",
        help="Use threads instead of processes for parallelization"
    )
    
    # Behavior options
    parser.add_argument(
        "-q", "--quiet", 
        action="store_true",
        help="Don't output text, just simulate (for testing)"
    )
    
    parser.add_argument(
        "--no-newline", 
        action="store_true",
        help="Don't add newlines after each text output"
    )
    
    # Debug and info options
    parser.add_argument(
        "--stats", 
        action="store_true",
        help="Show execution statistics at the end"
    )
    
    parser.add_argument(
        "--debug", 
        action="store_true",
        help="Enable debug output"
    )
    
    parser.add_argument(
        "--version", 
        action="version", 
        version="Enhanced Yes Command 2.0.0"
    )
    
    return parser

def validate_arguments(args) -> None:
    """Validate command line arguments."""
    if args.count is not None and args.count < 0:
        raise ValueError("Count must be non-negative")
    
    if args.delay < 0:
        raise ValueError("Delay must be non-negative")
    
    if args.workers < 1:
        raise ValueError("Number of workers must be at least 1")
    
    if args.workers > multiprocessing.cpu_count() * 2:
        print(f"[WARNING] Using {args.workers} workers on a {multiprocessing.cpu_count()}-CPU system", 
              file=sys.stderr)
    
    # Check for problematic combinations
    if SystemInfo.is_powershell() and not sys.stdout.isatty() and args.workers > 1:
        print("[WARNING] PowerShell with multiprocessing and pipe redirection may cause issues.", 
              file=sys.stderr)

def main(argv=None):
    """Main application entry point."""
    if argv is None:
        argv = sys.argv[1:]
    
    parser = setup_argument_parser()
    
    try:
        args = parser.parse_args(argv)
        validate_arguments(args)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Setup system
    SystemInfo.setup_signal_handlers()
    show_colors = SystemInfo.supports_colors() and not args.quiet
    
    # Process text
    text = args.text
    if args.parse_escapes:
        text = parse_escape_sequences(text)
    
    if args.no_newline:
        line_ending = ""
    else:
        line_ending = "\n"
    
    # Determine count
    count = args.count if args.count is not None else float("inf")
    
    # Debug info
    if args.debug:
        print(f"[DEBUG] Text: '{text}', Count: {count}, Workers: {args.workers}", file=sys.stderr)
        print(f"[DEBUG] Mode: {args.mode}, Delay: {args.delay}s", file=sys.stderr)
        print(f"[DEBUG] System: PowerShell={SystemInfo.is_powershell()}, Windows={SystemInfo.is_windows()}", file=sys.stderr)
    
    start_time = time.perf_counter()
    worker_stats = []
    
    try:
        if args.use_threads or args.workers == 1:
            # Use threading for single worker or when explicitly requested
            stats_queue = queue.Queue()
            stop_event = threading.Event()
            threads = []
            
            for i in range(args.workers):
                if args.workers == 1:
                    # Single threaded execution
                    yes_worker(0, text, count, args.delay, args.quiet, args.output, args.mode, None)
                else:
                    # Multi-threaded execution
                    thread = threading.Thread(
                        target=threaded_yes_worker,
                        args=(i, text, count, args.delay, args.quiet, args.mode, stats_queue, stop_event)
                    )
                    thread.start()
                    threads.append(thread)
                    
                    if args.debug:
                        print(f"[DEBUG] Thread {i} started", file=sys.stderr)
            
            # Wait for threads to complete
            if threads:
                try:
                    for thread in threads:
                        thread.join()
                except KeyboardInterrupt:
                    stop_event.set()
                    for thread in threads:
                        thread.join(timeout=1.0)
                
                # Collect statistics
                while not stats_queue.empty():
                    msg_type, worker_id, data = stats_queue.get()
                    if msg_type == 'stats':
                        worker_stats.append(data)
                    elif msg_type == 'error' and args.debug:
                        print(f"[DEBUG] Worker {worker_id} error: {data}", file=sys.stderr)
        
        else:
            # Use multiprocessing
            stats_queue = multiprocessing.Queue()
            processes = []
            
            for i in range(args.workers):
                process = multiprocessing.Process(
                    target=yes_worker,
                    args=(i, text, count, args.delay, args.quiet, args.output, args.mode, stats_queue)
                )
                process.start()
                processes.append(process)
                
                if args.debug:
                    print(f"[DEBUG] Process {process.pid} started", file=sys.stderr)
            
            try:
                for process in processes:
                    process.join()
            except KeyboardInterrupt:
                for process in processes:
                    if args.debug:
                        print(f"[DEBUG] Terminating process {process.pid}", file=sys.stderr)
                    process.terminate()
                    process.join(timeout=1.0)
                    if process.is_alive():
                        process.kill()
            
            # Collect statistics
            while not stats_queue.empty():
                try:
                    msg_type, worker_id, data = stats_queue.get_nowait()
                    if msg_type == 'stats':
                        worker_stats.append(data)
                    elif msg_type == 'error' and args.debug:
                        print(f"[DEBUG] Worker {worker_id} error: {data}", file=sys.stderr)
                except queue.Empty:
                    break
    
    except KeyboardInterrupt:
        if args.debug:
            print("\n[DEBUG] Interrupted by user", file=sys.stderr)
    
    end_time = time.perf_counter()
    total_time = end_time - start_time
    
    # Show statistics
    if args.stats and worker_stats:
        print_statistics(worker_stats, total_time, show_colors)
    elif args.debug:
        print(f"\n[DEBUG] Execution time: {total_time:.6f} seconds", file=sys.stderr)

if __name__ == "__main__":
    # Enable multiprocessing support on Windows
    multiprocessing.freeze_support()
    
    try:
        main()
    except (BrokenPipeError, OSError, KeyboardInterrupt):
        # Exit quietly if pipe is closed or interrupted
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)