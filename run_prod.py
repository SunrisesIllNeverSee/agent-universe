"""Production entry point — reads PORT from environment for Railway/Render/Fly."""
from __future__ import annotations
import os
from pathlib import Path

import uvicorn

from app.server import create_app

root = Path(__file__).resolve().parent
app = create_app(root)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
