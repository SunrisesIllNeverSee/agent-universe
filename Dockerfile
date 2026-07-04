FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install the civitae-mcp package from PyPI (MIT licensed, stdio MCP)
RUN pip install civitae-mcp

# Default API URL (the live CIVITAE marketplace)
ENV CIVITAE_API_URL=https://signomy.xyz

# Run the MCP server over stdio (Glama introspector calls tools/list)
CMD ["python", "-m", "civitae_mcp"]
