"""
run_mcp_command.py — MCP 1: COMMAND Runtime Bridge (stdio)

Runs the internal governance chat MCP (app/mcp_bridge.py).
This is NOT the CIVITAE plugin — for that, use civitae_mcp_server.py.
"""
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app.server import create_app  # noqa: E402


if __name__ == "__main__":
    app = create_app(ROOT)
    mcp = app.state.mcp_bridge.build_fastmcp()
    mcp.run()
