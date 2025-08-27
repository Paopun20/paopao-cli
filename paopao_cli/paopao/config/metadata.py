from dataclasses import dataclass, field
from typing import Optional

@dataclass
class CommandMetadata:
    name: str = "unknown"
    version: str = "Unknown"
    author: str = "Unknown"
    description: str = "No description available"
    source: str = "community"

    def edit(
        self,
        name: Optional[str] = None,
        version: Optional[str] = None,
        author: Optional[str] = None,
        description: Optional[str] = None,
        source: Optional[str] = None
    ):
        if name is not None:
            self.name = name
        if version is not None:
            self.version = version
        if author is not None:
            self.author = author
        if description is not None:
            self.description = description
        if source is not None:
            self.source = source
