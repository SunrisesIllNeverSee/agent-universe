"""
run_mcp_command.py — MCP 1: COMMAND Runtime Bridge (stdio)

Runs the internal governance chat MCP (app/mcp_bridge.py).
This is NOT the CIVITAE plugin — for that, use the civitae-mcp package (pip install civitae-mcp).

Run from repo root:
    python packages/civitae-mcp/run_mcp_command.py
"""
from pathlib import Path
import sys


# Repo root is two levels up from packages/civitae-mcp/
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from app.server import create_app  # noqa: E402


if __name__ == "__main__":
    app = create_app(ROOT)
    mcp = app.state.mcp_bridge.build_fastmcp()
    mcp.run()
