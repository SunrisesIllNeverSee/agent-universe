from pathlib import Path
import threading

import uvicorn

from app.server import create_app


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    app = create_app(root)
    mcp = app.state.mcp_bridge.build_fastmcp()
    threading.Thread(target=lambda: mcp.run(transport="streamable-http"), daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=8300)
