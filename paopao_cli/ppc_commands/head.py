#!/usr/bin/env python3
"""
Enhanced Python implementation of the 'head' command.
Supports multiple files, byte counting, and follows GNU head behavior.
"""
import sys
import argparse
import os
from pathlib import Path
from typing import List, Optional, TextIO, BinaryIO, Union

def format_file_size(size: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'K', 'M', 'G', 'T']:
        if size < 1024:
            return f"{size:.1f}{unit}" if size != int(size) else f"{int(size)}{unit}"
        size /= 1024
    return f"{size:.1f}P"

def print_header(filename: str, show_header: bool = True) -> None:
    """Print file header in the format ==> filename <=="""
    if show_header:
        print(f"==> {filename} <==")

def head_lines_from_file(file_obj: TextIO, num_lines: int, quiet: bool = False) -> int:
    """
    Read and print the first num_lines from a file object.
    Returns the number of lines actually read.
    """
    lines_read = 0
    try:
        for line in file_obj:
            if lines_read >= num_lines:
                break
            if not quiet:
                sys.stdout.write(line)
            lines_read += 1
    except (BrokenPipeError, OSError):
        # Handle broken pipe gracefully
        pass
    return lines_read

def head_bytes_from_file(file_obj: Union[TextIO, BinaryIO], num_bytes: int, quiet: bool = False) -> int:
    """
    Read and print the first num_bytes from a file object.
    Returns the number of bytes actually read.
    """
    bytes_read = 0
    try:
        if hasattr(file_obj, 'buffer'):
            # Text file, use binary buffer
            file_obj = file_obj.buffer
        
        while bytes_read < num_bytes:
            chunk_size = min(8192, num_bytes - bytes_read)  # Read in chunks
            chunk = file_obj.read(chunk_size)
            if not chunk:
                break
            
            if not quiet:
                if isinstance(chunk, bytes):
                    sys.stdout.buffer.write(chunk)
                else:
                    sys.stdout.write(chunk)
            
            bytes_read += len(chunk)
    except (BrokenPipeError, OSError):
        # Handle broken pipe gracefully
        pass
    return bytes_read

def parse_count_argument(value: str) -> int:
    """
    Parse count argument, supporting suffixes like 10K, 5M, etc.
    """
    value = value.strip().upper()
    
    # Handle multiplier suffixes
    multipliers = {
        'B': 1, 'K': 1024, 'M': 1024**2, 
        'G': 1024**3, 'T': 1024**4
    }
    
    if value[-1] in multipliers:
        try:
            number = float(value[:-1])
            return int(number * multipliers[value[-1]])
        except ValueError:
            raise argparse.ArgumentTypeError(f"invalid count: '{value}'")
    
    try:
        return int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid count: '{value}'")

def process_file(filename: str, args: argparse.Namespace, show_header: bool) -> tuple[bool, int]:
    """
    Process a single file and return (success, items_processed).
    """
    try:
        if filename == '-':
            file_obj = sys.stdin
            display_name = '<stdin>'
        else:
            path = Path(filename)
            if not path.exists():
                print(f"head: cannot open '{filename}' for reading: No such file or directory", 
                      file=sys.stderr)
                return False, 0
            
            if path.is_dir():
                print(f"head: error reading '{filename}': Is a directory", file=sys.stderr)
                return False, 0
            
            try:
                file_obj = open(filename, 'r', encoding='utf-8', errors='replace')
                display_name = filename
            except PermissionError:
                print(f"head: cannot open '{filename}' for reading: Permission denied", 
                      file=sys.stderr)
                return False, 0
            except Exception as e:
                print(f"head: cannot open '{filename}' for reading: {e}", file=sys.stderr)
                return False, 0
        
        if show_header:
            print_header(display_name)
        
        # Process the file
        if args.bytes is not None:
            items_processed = head_bytes_from_file(file_obj, args.bytes, args.quiet)
        else:
            items_processed = head_lines_from_file(file_obj, args.lines, args.quiet)
        
        # Close file if we opened it
        if filename != '-' and hasattr(file_obj, 'close'):
            file_obj.close()
        
        return True, items_processed
    
    except KeyboardInterrupt:
        if filename != '-' and hasattr(file_obj, 'close'):
            file_obj.close()
        raise
    except Exception as e:
        print(f"head: error reading '{filename}': {e}", file=sys.stderr)
        return False, 0

def main(argv: Optional[List[str]] = None) -> int:
    """Main function with proper exit codes."""
    parser = argparse.ArgumentParser(
        prog="head",
        description="Print the first N lines (or bytes) of files to stdout",
        epilog="""
Examples:
  head file.txt                    # First 10 lines of file.txt
  head -n 20 file.txt             # First 20 lines
  head -c 1K file.txt             # First 1024 bytes
  head -n 5 file1.txt file2.txt   # First 5 lines of each file
  cat file.txt | head -n 3        # First 3 lines from stdin
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Line/byte count options (mutually exclusive)
    count_group = parser.add_mutually_exclusive_group()
    count_group.add_argument(
        "-n", "--lines", 
        type=parse_count_argument,
        default=10,
        metavar="NUM",
        help="Print first NUM lines (default: 10). Supports suffixes: K, M, G"
    )
    count_group.add_argument(
        "-c", "--bytes",
        type=parse_count_argument,
        metavar="NUM", 
        help="Print first NUM bytes. Supports suffixes: K, M, G"
    )
    
    # Output options
    parser.add_argument(
        "-q", "--quiet", "--silent",
        action="store_true",
        help="Never print headers when multiple files are specified"
    )
    parser.add_argument(
        "-v", "--verbose", 
        action="store_true",
        help="Always print headers, even for single files"
    )
    
    # File arguments
    parser.add_argument(
        "files",
        nargs="*",
        default=['-'],
        help="Files to process (default: stdin if no files specified)"
    )
    
    # Version info
    parser.add_argument(
        "--version",
        action="version",
        version="head (Python implementation) 1.0"
    )
    
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code if e.code is not None else 0
    
    # Validate arguments
    if args.bytes is not None and args.bytes < 0:
        print("head: invalid number of bytes: cannot be negative", file=sys.stderr)
        return 1
    
    if args.lines < 0:
        print("head: invalid number of lines: cannot be negative", file=sys.stderr)
        return 1
    
    # Determine if we should show headers
    multiple_files = len(args.files) > 1
    show_headers = (multiple_files and not args.quiet) or args.verbose
    
    # Process files
    exit_code = 0
    total_processed = 0
    
    try:
        for i, filename in enumerate(args.files):
            # Add spacing between files (except first)
            if show_headers and i > 0:
                print()
            
            success, items_processed = process_file(filename, args, show_headers)
            
            if not success:
                exit_code = 1
            
            total_processed += items_processed
            
            # Early termination check for stdin
            if filename == '-' and not sys.stdin.isatty():
                break
    
    except KeyboardInterrupt:
        print("\nhead: interrupted", file=sys.stderr)
        return 130  # Standard exit code for SIGINT
    except (BrokenPipeError, OSError):
        # Handle broken pipe (e.g., piped to `head` command)
        try:
            sys.stdout.close()
            sys.stderr.close()
        except:
            pass
        return 0
    
    return exit_code

if __name__ == "__main__":
    try:
        sys.exit(main())
    except (BrokenPipeError, OSError):
        # Final safety net for broken pipes
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
