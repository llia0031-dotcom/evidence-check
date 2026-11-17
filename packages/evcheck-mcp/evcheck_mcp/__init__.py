"""evcheck's MCP server as a package of its own, so `uvx evcheck-mcp` starts it with everything it needs."""
from evcheck.mcp_server import main

__all__ = ["main"]
