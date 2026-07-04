# syntax=docker/dockerfile:1
# Glama introspection Dockerfile for agent-universe / Signomy MCP server.
# Installs the civitae-mcp package (MIT) from PyPI and runs it as a stdio
# MCP server so Glama can call tools/list for scoring and "Try in Browser".
# The core platform (FastAPI backend, governance, marketplace) is not
# included — this is the catalog/introspection surface only.

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CIVITAE_API_URL=https://signomy.xyz

# Install only the MCP client package — no repo code needed
RUN pip install --no-cache-dir civitae-mcp==0.2.0

# Verify the package installed and can import
RUN python -c "import civitae_mcp; print('civitae-mcp OK')"

# Run the MCP server over stdio (Glama introspector calls tools/list)
CMD ["python", "-m", "civitae_mcp"]
