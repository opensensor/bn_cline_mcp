#!/bin/bash
# Save this as /home/matteius/Documents/Cline/MCP/bn-mcp/run-bridge.sh
export BN_HTTP_SERVER=http://localhost:8088
cd /home/matteius/Documents/Cline/MCP/bn-mcp/
/usr/bin/node binaryninja-mcp-bridge.js
