"""i14y-mcp — MCP server for Switzerland's national metadata catalogue (I14Y)."""

from ._version import __version__
from .server import main, mcp

__all__ = ["main", "mcp", "__version__"]
