"""i14y-mcp — MCP server for Switzerland's national metadata catalogue (I14Y)."""

__version__ = "0.1.0"

from .server import main, mcp

__all__ = ["main", "mcp", "__version__"]
