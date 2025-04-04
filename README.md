# binary_ninja_cline_mcp
An MCP server for Cline that works with Binary Ninja (Personal License)

This repository contains an MCP server that allows Cline to analyze binaries using Binary Ninja.
Note:  Not all files will be used, there is also prototype of using headless Binary Ninja but my 
license is Personal so I can't test it.

## Setup

1. Install the latest of Binary Ninja MCP Plugin https://github.com/fosdickio/binary_ninja_mcp
2. Open your binary and start the MCP server from within Binary Ninja.
3. Open a terminal and run python binary_ninja_mcp_http_server.py --port 8088
4. Open another terminal and run `npm start`
5. Open Cline and add the following tool:{
Example:
```
{
  "mcpServers": {
    "BN MCP": {
      "command": "node",
      "args": ["/home/matteius/binary_ninja_cline/bn_cline_mcp/binaryninja-mcp-bridge.js"],
      "env": {
        "BN_HTTP_SERVER": "http://localhost:8088"
      },
      "autoApprove": [],
      "disabled": false,
      "timeout": 30
    }
  }
}

```