import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Config:
    """Configuration constants for the CLI framework."""
    COMMANDS_DIR: Path = Path(__file__).parent / "ppc_commands"
    COMMUNITY_COMMANDS_DIR: Path = Path(__file__).parent / "ppc_addon"
    CACHE_DIR: Path = Path(__file__).parent / ".ppc_cache"
    JSON_PROJECT_META_FILE: str = "ppc.project.json"
    TOML_PROJECT_META_FILE: str = "ppc.project.toml"
    GIT_META_FILE: str = ".ppc.git"
    LOCK_FILE: str = ".ppc.lock"
    CACHE_EXPIRY_HOURS: int = 24
    MAX_INSTALL_TIME_SECONDS: int = 300  # 5 minutes
    ALLOWED_URL_SCHEMES: List[str] = None
    
    def __post_init__(self):
        """Create necessary directories and set defaults."""
        if self.ALLOWED_URL_SCHEMES is None:
            self.ALLOWED_URL_SCHEMES = ["https", "git", "ssh"]
        
        try:
            self.COMMANDS_DIR.mkdir(exist_ok=True)
            self.COMMUNITY_COMMANDS_DIR.mkdir(exist_ok=True)
            self.CACHE_DIR.mkdir(exist_ok=True)
        except PermissionError:
            print(f"Warning: Cannot create directories due to permissions")

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
    dependencies: Optional[List[str]] = None
    python_version: str = "3.6+"
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []