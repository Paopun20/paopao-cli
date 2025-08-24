#!/usr/bin/env python3
"""
Enhanced Directory Tree Visualization Tool
A powerful tool for displaying directory structures with icons, filtering, and rich formatting.
"""

import os
import sys
import argparse
import stat
from pathlib import Path
from typing import Optional, Dict, Set, List
from dataclasses import dataclass
from datetime import datetime

try:
    import pathspec  # for .gitignore support
    PATHSPEC_AVAILABLE = True
except ImportError:
    PATHSPEC_AVAILABLE = False
    print("Warning: pathspec not available. Install with: pip install pathspec")

from rich.console import Console
from rich.tree import Tree
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# ─────────────────────────────────────────────────────────────────────────────
# Configuration and File Type Mappings
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TreeStats:
    """Statistics about the directory tree."""
    total_files: int = 0
    total_dirs: int = 0
    total_size: int = 0
    file_types: Dict[str, int] = None
    largest_file: Optional[tuple] = None
    
    def __post_init__(self):
        if self.file_types is None:
            self.file_types = {}

class FileTypeConfig:
    """File type mappings and icons."""
    
    # Programming languages
    PROGRAMMING = {
        '.py': ('🐍', 'bold green', 'Python'),
        '.pyc': ('🐍', 'dim green', 'Python Bytecode'),
        '.pyo': ('🐍', 'dim green', 'Python Optimized'),
        '.pyx': ('🐍', 'bright_green', 'Cython'),
        '.js': ('🟨', 'yellow', 'JavaScript'),
        '.ts': ('🔷', 'blue', 'TypeScript'),
        '.jsx': ('⚛️', 'cyan', 'React JSX'),
        '.tsx': ('⚛️', 'bright_cyan', 'React TSX'),
        '.html': ('🌐', 'orange1', 'HTML'),
        '.css': ('🎨', 'magenta', 'CSS'),
        '.scss': ('🎨', 'bright_magenta', 'SASS'),
        '.less': ('🎨', 'bright_magenta', 'LESS'),
        '.java': ('☕', 'red', 'Java'),
        '.c': ('⚙️', 'blue', 'C'),
        '.cpp': ('⚙️', 'bright_blue', 'C++'),
        '.h': ('📋', 'cyan', 'Header'),
        '.hpp': ('📋', 'bright_cyan', 'C++ Header'),
        '.rs': ('🦀', 'orange1', 'Rust'),
        '.go': ('🐹', 'bright_blue', 'Go'),
        '.php': ('🐘', 'purple', 'PHP'),
        '.rb': ('💎', 'red', 'Ruby'),
        '.swift': ('🐦', 'orange1', 'Swift'),
        '.kt': ('🟣', 'purple', 'Kotlin'),
        '.scala': ('🔴', 'red', 'Scala'),
        '.sh': ('🐚', 'green', 'Shell Script'),
        '.bash': ('🐚', 'bright_green', 'Bash Script'),
        '.zsh': ('🐚', 'bright_green', 'Zsh Script'),
        '.fish': ('🐟', 'cyan', 'Fish Script'),
        '.ps1': ('💙', 'blue', 'PowerShell'),
        '.bat': ('⚫', 'white', 'Batch File'),
        '.cmd': ('⚫', 'bright_white', 'Command File'),
        '.r': ('📊', 'blue', 'R Script'),
        '.m': ('📐', 'orange1', 'MATLAB/Objective-C'),
        '.pl': ('🐪', 'blue', 'Perl'),
        '.lua': ('🌙', 'bright_blue', 'Lua'),
        '.vim': ('💚', 'green', 'Vim Script'),
    }
    
    # Data and config files
    DATA_CONFIG = {
        '.json': ('📋', 'yellow', 'JSON'),
        '.yaml': ('📋', 'bright_yellow', 'YAML'),
        '.yml': ('📋', 'bright_yellow', 'YAML'),
        '.xml': ('📋', 'orange1', 'XML'),
        '.toml': ('📋', 'cyan', 'TOML'),
        '.ini': ('⚙️', 'white', 'INI Config'),
        '.cfg': ('⚙️', 'bright_white', 'Config'),
        '.conf': ('⚙️', 'bright_white', 'Config'),
        '.env': ('🔒', 'green', 'Environment'),
        '.csv': ('📊', 'green', 'CSV Data'),
        '.tsv': ('📊', 'bright_green', 'TSV Data'),
        '.sql': ('🗄️', 'blue', 'SQL'),
        '.db': ('🗄️', 'bright_blue', 'Database'),
        '.sqlite': ('🗄️', 'bright_blue', 'SQLite'),
        '.sqlite3': ('🗄️', 'bright_blue', 'SQLite3'),
    }
    
    # Documents
    DOCUMENTS = {
        '.md': ('📝', 'bright_magenta', 'Markdown'),
        '.txt': ('📄', 'white', 'Text'),
        '.rtf': ('📄', 'bright_white', 'Rich Text'),
        '.pdf': ('📕', 'red', 'PDF'),
        '.doc': ('📘', 'blue', 'Word Document'),
        '.docx': ('📘', 'bright_blue', 'Word Document'),
        '.xls': ('📗', 'green', 'Excel'),
        '.xlsx': ('📗', 'bright_green', 'Excel'),
        '.ppt': ('📙', 'orange1', 'PowerPoint'),
        '.pptx': ('📙', 'bright_orange', 'PowerPoint'),
        '.odt': ('📄', 'cyan', 'OpenDocument Text'),
        '.ods': ('📊', 'bright_cyan', 'OpenDocument Spreadsheet'),
        '.tex': ('📑', 'white', 'LaTeX'),
        '.rst': ('📝', 'yellow', 'reStructuredText'),
    }
    
    # Media files
    MEDIA = {
        '.mp3': ('🎵', 'purple', 'MP3 Audio'),
        '.wav': ('🎵', 'bright_purple', 'WAV Audio'),
        '.flac': ('🎵', 'magenta', 'FLAC Audio'),
        '.ogg': ('🎵', 'bright_magenta', 'OGG Audio'),
        '.wma': ('🎵', 'cyan', 'WMA Audio'),
        '.midi': ('🎼', 'yellow', 'MIDI'),
        '.mid': ('🎼', 'bright_yellow', 'MIDI'),
        '.mp4': ('🎬', 'red', 'MP4 Video'),
        '.avi': ('🎬', 'bright_red', 'AVI Video'),
        '.mkv': ('🎬', 'magenta', 'MKV Video'),
        '.mov': ('🎬', 'bright_magenta', 'MOV Video'),
        '.wmv': ('🎬', 'blue', 'WMV Video'),
        '.webm': ('🎬', 'green', 'WebM Video'),
        '.png': ('🖼️', 'cyan', 'PNG Image'),
        '.jpg': ('🖼️', 'orange1', 'JPEG Image'),
        '.jpeg': ('🖼️', 'bright_orange', 'JPEG Image'),
        '.gif': ('🖼️', 'yellow', 'GIF Image'),
        '.bmp': ('🖼️', 'white', 'Bitmap Image'),
        '.tiff': ('🖼️', 'bright_white', 'TIFF Image'),
        '.tif': ('🖼️', 'bright_white', 'TIFF Image'),
        '.webp': ('🖼️', 'green', 'WebP Image'),
        '.svg': ('🖼️', 'magenta', 'SVG Vector'),
        '.ico': ('🖼️', 'blue', 'Icon'),
        '.icns': ('🖼️', 'bright_blue', 'macOS Icon'),
    }
    
    # Archives and packages
    ARCHIVES = {
        '.zip': ('📦', 'yellow', 'ZIP Archive'),
        '.rar': ('📦', 'bright_yellow', 'RAR Archive'),
        '.7z': ('📦', 'orange1', '7-Zip Archive'),
        '.tar': ('📦', 'cyan', 'TAR Archive'),
        '.gz': ('📦', 'bright_cyan', 'Gzip'),
        '.bz2': ('📦', 'blue', 'Bzip2'),
        '.xz': ('📦', 'bright_blue', 'XZ Archive'),
        '.deb': ('📦', 'red', 'Debian Package'),
        '.rpm': ('📦', 'bright_red', 'RPM Package'),
        '.dmg': ('📦', 'magenta', 'macOS Disk Image'),
        '.iso': ('💿', 'purple', 'ISO Image'),
        '.img': ('💿', 'bright_purple', 'Disk Image'),
    }
    
    # Executables and binaries
    EXECUTABLES = {
        '.exe': ('⚡', 'red', 'Windows Executable'),
        '.msi': ('📦', 'blue', 'Windows Installer'),
        '.app': ('📱', 'cyan', 'macOS Application'),
        '.deb': ('📦', 'orange1', 'Debian Package'),
        '.rpm': ('📦', 'red', 'RPM Package'),
        '.appimage': ('📱', 'green', 'AppImage'),
        '.snap': ('📦', 'yellow', 'Snap Package'),
        '.flatpak': ('📦', 'blue', 'Flatpak'),
        '.bin': ('⚙️', 'white', 'Binary'),
        '.dll': ('⚙️', 'cyan', 'Dynamic Library'),
        '.so': ('⚙️', 'bright_cyan', 'Shared Object'),
        '.dylib': ('⚙️', 'magenta', 'Dynamic Library'),
    }
    
    # Special files
    SPECIAL = {
        '.b': ('🧠', 'yellow', 'Binary'),
        '.bf16': ('🚀', 'cyan', 'BFloat16'),
        '.gitignore': ('🚫', 'red', 'Git Ignore'),
        '.gitattributes': ('⚙️', 'blue', 'Git Attributes'),
        '.dockerfile': ('🐳', 'blue', 'Dockerfile'),
        'dockerfile': ('🐳', 'bright_blue', 'Dockerfile'),
        '.dockerignore': ('🐳', 'red', 'Docker Ignore'),
        '.license': ('⚖️', 'yellow', 'License'),
        'license': ('⚖️', 'bright_yellow', 'License'),
        'readme': ('📖', 'green', 'Readme'),
        '.readme': ('📖', 'bright_green', 'Readme'),
        'makefile': ('🔨', 'orange1', 'Makefile'),
        '.makefile': ('🔨', 'bright_orange', 'Makefile'),
        '.lock': ('🔒', 'red', 'Lock File'),
    }
    
    @classmethod
    def get_all_mappings(cls) -> Dict[str, tuple]:
        """Get combined mapping of all file types."""
        mappings = {}
        for category in [cls.PROGRAMMING, cls.DATA_CONFIG, cls.DOCUMENTS, 
                        cls.MEDIA, cls.ARCHIVES, cls.EXECUTABLES, cls.SPECIAL]:
            mappings.update(category)
        return mappings
    
    @classmethod
    def get_file_info(cls, file_path: Path) -> tuple:
        """Get icon, color, and description for a file."""
        mappings = cls.get_all_mappings()
        suffix = file_path.suffix.lower()
        name_lower = file_path.name.lower()
        
        # Check by suffix first
        if suffix in mappings:
            return mappings[suffix]
        
        # Check by full name (for files like 'Dockerfile', 'Makefile')
        if name_lower in mappings:
            return mappings[name_lower]
        
        # Default fallback
        return ('🗄️', 'white', 'File')

# ─────────────────────────────────────────────────────────────────────────────
# Utility Functions
# ─────────────────────────────────────────────────────────────────────────────

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    size_idx = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and size_idx < len(size_names) - 1:
        size /= 1024.0
        size_idx += 1
    
    if size_idx == 0:
        return f"{int(size)} {size_names[size_idx]}"
    else:
        return f"{size:.1f} {size_names[size_idx]}"

def get_file_permissions(file_path: Path) -> str:
    """Get file permissions as a string."""
    try:
        mode = file_path.stat().st_mode
        perms = []
        
        # Owner permissions
        perms.append('r' if mode & stat.S_IRUSR else '-')
        perms.append('w' if mode & stat.S_IWUSR else '-')
        perms.append('x' if mode & stat.S_IXUSR else '-')
        
        # Group permissions
        perms.append('r' if mode & stat.S_IRGRP else '-')
        perms.append('w' if mode & stat.S_IWGRP else '-')
        perms.append('x' if mode & stat.S_IXGRP else '-')
        
        # Other permissions
        perms.append('r' if mode & stat.S_IROTH else '-')
        perms.append('w' if mode & stat.S_IWOTH else '-')
        perms.append('x' if mode & stat.S_IXOTH else '-')
        
        return ''.join(perms)
    except (OSError, PermissionError):
        return "?????????"

def load_gitignore_patterns(gitignore_path: Path):
    """Load .gitignore patterns if pathspec is available."""
    if not PATHSPEC_AVAILABLE:
        return None
        
    if not gitignore_path.exists():
        return None
    
    try:
        with gitignore_path.open("r", encoding="utf-8", errors="ignore") as f:
            lines = f.read().splitlines()
        return pathspec.PathSpec.from_lines("gitwildmatch", lines)
    except (OSError, PermissionError) as e:
        console.print(f"[yellow]Warning: Could not read .gitignore file: {e}[/]")
        return None

def should_ignore_path(path: Path, ignore_patterns: Set[str], ignore_hidden: bool) -> bool:
    """Check if a path should be ignored based on various criteria."""
    name = path.name.lower()
    
    # Hidden files/directories
    if ignore_hidden and name.startswith('.'):
        return True
    
    # Common ignore patterns
    if ignore_patterns:
        if name in ignore_patterns:
            return True
        
        # Check for pattern matches
        for pattern in ignore_patterns:
            if pattern in name:
                return True
    
    return False

# ─────────────────────────────────────────────────────────────────────────────
# Tree Building Functions
# ─────────────────────────────────────────────────────────────────────────────

def build_tree(
    directory: Path, 
    tree: Tree, 
    base_path: Path, 
    stats: TreeStats,
    ignore_spec=None,
    show_hidden: bool = False,
    show_size: bool = False,
    show_permissions: bool = False,
    show_modified: bool = False,
    max_depth: Optional[int] = None,
    current_depth: int = 0,
    ignore_patterns: Optional[Set[str]] = None
) -> None:
    """Build the directory tree recursively."""
    
    if max_depth is not None and current_depth >= max_depth:
        return
    
    try:
        paths = list(directory.iterdir())
        # Sort directories first, then files, both alphabetically
        paths.sort(key=lambda p: (not p.is_dir(), p.name.lower()))
        
        for path in paths:
            # Skip hidden files unless explicitly requested
            if not show_hidden and path.name.startswith('.'):
                continue
            
            # Check ignore patterns
            if ignore_patterns and should_ignore_path(path, ignore_patterns, not show_hidden):
                continue
            
            # Handle gitignore patterns
            if ignore_spec:
                try:
                    relative_path = path.relative_to(base_path)
                    if ignore_spec.match_file(str(relative_path)):
                        continue
                except ValueError:
                    # Path is not relative to base_path
                    continue
            
            display_parts = [path.name]
            
            if path.is_dir():
                stats.total_dirs += 1
                
                # Add directory size if requested
                if show_size:
                    try:
                        dir_size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
                        display_parts.append(f"({format_file_size(dir_size)})")
                    except (OSError, PermissionError):
                        display_parts.append("(size unknown)")
                
                display_name = " ".join(display_parts)
                branch = tree.add(f"📁 [bold blue]{display_name}[/bold blue]")
                
                # Recursively build subdirectory
                build_tree(
                    path, branch, base_path, stats, ignore_spec, 
                    show_hidden, show_size, show_permissions, show_modified,
                    max_depth, current_depth + 1, ignore_patterns
                )
                
            elif path.is_file():
                stats.total_files += 1
                
                try:
                    file_stat = path.stat()
                    file_size = file_stat.st_size
                    stats.total_size += file_size
                    
                    # Track file types
                    suffix = path.suffix.lower() or 'no extension'
                    stats.file_types[suffix] = stats.file_types.get(suffix, 0) + 1
                    
                    # Track largest file
                    if stats.largest_file is None or file_size > stats.largest_file[1]:
                        stats.largest_file = (str(path), file_size)
                    
                    # Get file type info
                    icon, color, file_type = FileTypeConfig.get_file_info(path)
                    
                    # Add size information
                    if show_size:
                        display_parts.append(f"({format_file_size(file_size)})")
                    
                    # Add permissions
                    if show_permissions:
                        perms = get_file_permissions(path)
                        display_parts.append(f"[{perms}]")
                    
                    # Add modification time
                    if show_modified:
                        mtime = datetime.fromtimestamp(file_stat.st_mtime)
                        display_parts.append(f"({mtime.strftime('%Y-%m-%d %H:%M')})")
                    
                    display_name = " ".join(display_parts)
                    tree.add(f"{icon} [{color}]{display_name}[/{color}]")
                    
                except (OSError, PermissionError):
                    # Handle files we can't access
                    icon, color, _ = FileTypeConfig.get_file_info(path)
                    display_name = f"{path.name} [red](access denied)[/red]"
                    tree.add(f"{icon} [{color}]{display_name}[/{color}]")
                    
            else:
                # Handle special files (symlinks, etc.)
                try:
                    if path.is_symlink():
                        target = path.readlink()
                        tree.add(f"🔗 [cyan]{path.name}[/cyan] → [dim]{target}[/dim]")
                    else:
                        tree.add(f"❓ [dim]{path.name}[/dim]")
                except (OSError, PermissionError):
                    tree.add(f"❓ [dim red]{path.name} (access denied)[/dim red]")
                    
    except PermissionError:
        tree.add("[red]🚫 Permission Denied[/red]")
    except OSError as e:
        tree.add(f"[red]❌ Error: {e}[/red]")

def show_statistics(stats: TreeStats, root_path: Path) -> None:
    """Display tree statistics in a nice table."""
    table = Table(title="Directory Statistics", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")
    
    table.add_row("Total Files", str(stats.total_files))
    table.add_row("Total Directories", str(stats.total_dirs))
    table.add_row("Total Size", format_file_size(stats.total_size))
    
    if stats.largest_file:
        largest_name = Path(stats.largest_file[0]).name
        largest_size = format_file_size(stats.largest_file[1])
        table.add_row("Largest File", f"{largest_name} ({largest_size})")
    
    # Show top file types
    if stats.file_types:
        sorted_types = sorted(stats.file_types.items(), key=lambda x: x[1], reverse=True)
        top_types = sorted_types[:3]  # Show top 3
        type_str = ", ".join([f"{ext} ({count})" for ext, count in top_types])
        table.add_row("Top File Types", type_str)
    
    console.print(table)

# ─────────────────────────────────────────────────────────────────────────────
# Main Application
# ─────────────────────────────────────────────────────────────────────────────

def setup_argument_parser() -> argparse.ArgumentParser:
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Enhanced directory tree visualization with icons and filtering.",
        epilog="""Examples:
  ppc treeview                          # Show current directory
  ppc treeview /path/to/dir             # Show specific directory
  ppc treeview --show-hidden            # Include hidden files
  ppc treeview --use-gitignore .gitignore  # Use .gitignore filtering
  ppc treeview --max-depth 2            # Limit depth to 2 levels
  ppc treeview --show-size --show-permissions  # Show detailed info
        """,
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Root directory to display (default: current directory)"
    )
    
    parser.add_argument(
        "--use-gitignore",
        metavar="GITIGNORE_FILE",
        help="Path to a .gitignore file for filtering files/folders"
    )
    
    parser.add_argument(
        "--show-hidden",
        action="store_true",
        help="Show hidden files and directories"
    )
    
    parser.add_argument(
        "--show-size",
        action="store_true",
        help="Show file and directory sizes"
    )
    
    parser.add_argument(
        "--show-permissions",
        action="store_true",
        help="Show file permissions"
    )
    
    parser.add_argument(
        "--show-modified",
        action="store_true",
        help="Show last modification time"
    )
    
    parser.add_argument(
        "--max-depth",
        type=int,
        metavar="N",
        help="Maximum depth to traverse (default: unlimited)"
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show directory statistics after the tree"
    )
    
    parser.add_argument(
        "--ignore-patterns",
        nargs="*",
        metavar="PATTERN",
        help="Additional patterns to ignore (e.g., '*.pyc' '__pycache__')"
    )
    
    parser.add_argument(
        "--no-icons",
        action="store_true",
        help="Disable icons for compatibility"
    )
    
    return parser

def main(argv=None):
    """Main application entry point."""
    if argv is None:
        argv = sys.argv[1:]
    
    parser = setup_argument_parser()
    args = parser.parse_args(argv)
    
    # Resolve the root directory
    root_dir = Path(os.path.expandvars(os.path.expanduser(args.directory))).resolve()
    
    if not root_dir.exists():
        console.print(f"[bold red]❌ Path not found:[/] {root_dir}")
        sys.exit(1)
    
    if not root_dir.is_dir():
        console.print(f"[bold red]❌ Not a directory:[/] {root_dir}")
        sys.exit(1)
    
    # Handle gitignore patterns
    ignore_spec = None
    if args.use_gitignore:
        if not PATHSPEC_AVAILABLE:
            console.print("[yellow]⚠️ Warning: pathspec not installed. Install with: pip install pathspec[/]")
        else:
            gitignore_path = Path(os.path.expandvars(os.path.expanduser(args.use_gitignore))).resolve()
            ignore_spec = load_gitignore_patterns(gitignore_path)
            if ignore_spec is None:
                console.print(f"[yellow]⚠️ Warning: .gitignore file not found: {gitignore_path}[/]")
    
    # Set up ignore patterns
    ignore_patterns = set()
    if args.ignore_patterns:
        ignore_patterns.update(pattern.lower() for pattern in args.ignore_patterns)
    
    # Initialize statistics
    stats = TreeStats()
    
    # Create the root tree
    root_display = f"📦 [link file://{root_dir}]{root_dir.name}[/]"
    if args.show_size:
        try:
            with Progress(SpinnerColumn(), TextColumn("Calculating directory size..."), transient=True) as progress:
                progress.add_task("", total=None)
                total_size = sum(f.stat().st_size for f in root_dir.rglob('*') if f.is_file())
            root_display += f" ({format_file_size(total_size)})"
        except (OSError, PermissionError):
            root_display += " (size calculation failed)"
    
    tree = Tree(root_display)
    
    # Build the tree
    try:
        with Progress(SpinnerColumn(), TextColumn("Building directory tree..."), transient=True) as progress:
            progress.add_task("", total=None)
            build_tree(
                directory=root_dir,
                tree=tree,
                base_path=root_dir,
                stats=stats,
                ignore_spec=ignore_spec,
                show_hidden=args.show_hidden,
                show_size=args.show_size,
                show_permissions=args.show_permissions,
                show_modified=args.show_modified,
                max_depth=args.max_depth,
                ignore_patterns=ignore_patterns
            )
    except KeyboardInterrupt:
        console.print("\n[yellow]Tree building interrupted by user.[/]")
        sys.exit(1)
    
    # Display the tree
    console.print(tree)
    
    # Show statistics if requested
    if args.stats:
        console.print()
        show_statistics(stats, root_dir)

if __name__ == "__main__":
    main()
