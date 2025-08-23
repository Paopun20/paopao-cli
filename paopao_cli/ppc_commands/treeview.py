# My Helper Tool LOL, you want to use. yes, you can
import os, sys, argparse

import pathspec  # for .gitignore support

from pathlib import Path

from rich.console import Console
from rich.tree import Tree

console = Console()

def load_gitignore_patterns(gitignore_path: Path):
    if not gitignore_path.exists():
        return None
    with gitignore_path.open("r") as f:
        lines = f.read().splitlines()
    return pathspec.PathSpec.from_lines("gitwildmatch", lines)

def build_tree(directory: Path, tree: Tree, base_path: Path, ignore_spec=None):
    try:
        for path in sorted(directory.iterdir()):
            if path.name.startswith("."):
                continue  # skip hidden/system folders

            relative_path = path.relative_to(base_path)

            # Skip ignored files/folders if using gitignore
            if ignore_spec and ignore_spec.match_file(str(relative_path)):
                continue

            # Show only the final name component at this level:
            display_name = path.name

            if path.is_dir():
                branch = tree.add(f"📁 [bold blue]{display_name}")
                build_tree(path, branch, base_path, ignore_spec)

            elif path.is_file():
                suffix = path.suffix.lower()
                if suffix in [".py", ".pyc", ".pyo"]:
                    tree.add(f"🐍 [bold green]{display_name}")
                elif suffix == ".md":
                    tree.add(f"📝 [bold magenta]{display_name}")
                elif suffix == ".txt":
                    tree.add(f"📄 [white]{display_name}")
                elif suffix == ".b" or suffix == ".bf16":
                    tree.add(f"🧠 [bold yellow]{display_name}")
                elif suffix == ".bf16": 
                    tree.add(f"🚀 [bold cyan]{display_name}")
                elif suffix in [".wav", ".mp3", ".ogg", ".flac", ".midi", ".wma"]:
                    tree.add(f"🎵 [purple]{display_name}")
                elif suffix in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp", ".ico"]:
                    tree.add(f"🖼️ [orange1]{display_name}")
                else:
                    tree.add(f"🗄️ [white]{display_name}")
            else:
                tree.add(f"❓ [dim]{display_name}")

    except PermissionError:
        tree.add("[ [red]🚫 Permission Denied[/] ]")

def main():
    parser = argparse.ArgumentParser(description="Display directory tree with icons and optional .gitignore filtering.")
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Root directory to display (default: current directory)"
    )
    parser.add_argument(
        "--usegitignore",
        metavar="GITIGNORE_FILE",
        help="Path to a .gitignore file to exclude files/folders"
    )
    args = parser.parse_args()

    root_dir = Path(os.path.expandvars(args.directory)).resolve()

    if not root_dir.exists():
        console.print(f"[bold red]❌ Path not found:[/] {root_dir}")
        sys.exit(1)

    ignore_spec = None
    if args.usegitignore:
        gitignore_path = Path(os.path.expandvars(args.usegitignore)).resolve()
        ignore_spec = load_gitignore_patterns(gitignore_path)
        if ignore_spec is None:
            console.print(f"[yellow]⚠️ Warning: .gitignore file not found or empty: {gitignore_path}[/]")

    tree = Tree(f"📦 [link file://{root_dir}]{root_dir.name}[/]")
    build_tree(root_dir, tree, base_path=root_dir, ignore_spec=ignore_spec)
    console.print(tree)