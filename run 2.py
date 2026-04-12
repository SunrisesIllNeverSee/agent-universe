from pathlib import Path
import logging
import threading

import uvicorn

from app.server import create_app

logger = logging.getLogger("civitae")


def _run_mcp(mcp):
    """Run MCP server in a thread with crash logging."""
    try:
        mcp.run(transport="streamable-http")
    except Exception:
        logger.exception("MCP thread crashed — uvicorn continues but MCP is dead")


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    app = create_app(root)
    mcp = app.state.mcp_bridge.build_fastmcp()
    threading.Thread(target=_run_mcp, args=(mcp,), daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=8300)
